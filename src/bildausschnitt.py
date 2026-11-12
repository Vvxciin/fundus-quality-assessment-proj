"""Paarweiser Vergleich von Vollbild und festem zentralem Bildausschnitt."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path

import av
import cv2
import numpy as np

from batch_sobel import DEFAULT_FLICKER, discover, outside_windows


MERKMALE = ("sobel", "kontrast", "helligkeit", "laplace")
BEREICHE = ("vollbild", "mitte")


def mittelausschnitt(bild):
    hoehe, breite = bild.shape
    return bild[hoehe // 4:3 * hoehe // 4, breite // 4:3 * breite // 4]


def merkmale(grau):
    gx = cv2.Sobel(grau, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(grau, cv2.CV_64F, 0, 1, ksize=3)
    kanten = cv2.magnitude(gx, gy)
    laplace = cv2.Laplacian(cv2.GaussianBlur(grau, (3, 3), 0), cv2.CV_16S, ksize=3)
    # Erst filtern, dann auswerten. So entsteht keine künstliche Kante am Ausschnittrand.
    vollbild = (grau, kanten, laplace)
    mitte = tuple(mittelausschnitt(bild) for bild in vollbild)
    ergebnisse = []
    for bild, gradient, zweite_ableitung in (vollbild, mitte):
        mittel, streuung = cv2.meanStdDev(bild)
        ergebnisse.append((cv2.mean(gradient)[0], streuung[0, 0], mittel[0, 0],
                           cv2.norm(zweite_ableitung, cv2.NORM_L1) / bild.size))
    return ergebnisse


def auswerten(quelle, erwartete_frames):
    zeiten = []
    messungen = []
    start = None
    with quelle.open() as datei, av.open(datei) as video:
        for frame in video.decode(video=0):
            if frame.pts is None or frame.time_base is None:
                raise ValueError(f"{quelle.name}: Zeitstempel fehlt")
            zeit = frame.pts * frame.time_base
            if start is None:
                start = zeit
            zeiten.append(float(zeit - start))
            grau = cv2.cvtColor(frame.to_ndarray(format="bgr24"), cv2.COLOR_BGR2GRAY)
            messungen.append(merkmale(grau))
    if not zeiten or np.any(np.diff(zeiten) <= 0):
        raise ValueError(f"{quelle.name}: ungültige Zeitachse")
    if erwartete_frames is not None and len(zeiten) != erwartete_frames:
        raise ValueError(f"{quelle.name}: {len(zeiten)} statt {erwartete_frames} Frames")
    werte = np.asarray(messungen)
    auswahl = outside_windows(np.asarray(zeiten), DEFAULT_FLICKER)
    if not auswahl.any():
        raise ValueError(f"{quelle.name}: keine Frames außerhalb der Zeitfenster")
    ergebnis = {"video": quelle.name, "gruppe": {"Good": "Gut", "Bad": "Schlecht"}[quelle.label],
                "frames": len(zeiten), "frames_ausserhalb": int(auswahl.sum())}
    for name, daten in (("alle", werte), ("ausserhalb", werte[auswahl])):
        ergebnis[name] = {
            bereich: dict(zip(MERKMALE, daten[:, index, :].mean(axis=0).tolist()))
            for index, bereich in enumerate(BEREICHE)
        }
    return ergebnis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eingabe", type=Path, help="Kursarchiv oder Videoordner")
    parser.add_argument("--ausgabe", type=Path, required=True, help="Zielordner für die Ergebnisse")
    parser.add_argument("--referenz", type=Path, help="JSON-Zusammenfassung der Sobel-Auswertung")
    parser.add_argument("--jobs", type=int, default=1, help="Anzahl parallel ausgewerteter Videos")
    args = parser.parse_args()
    referenz = {}
    if args.referenz:
        referenz = {v["video"]: v for v in json.loads(args.referenz.read_text(encoding="utf-8"))["videos"]}
    quellen = discover(args.eingabe)
    if args.referenz and {q.name for q in quellen} != set(referenz):
        raise ValueError("Videoauswahl und Referenz stimmen nicht überein")
    if args.jobs < 1:
        parser.error("--jobs muss mindestens 1 sein")
    cv2.setNumThreads(1)

    def berechnen(quelle):
        print(f"{quelle.name}: Auswertung läuft", flush=True)
        alt = referenz.get(quelle.name)
        neu = auswerten(quelle, alt["frames"] if alt else None)
        if alt:
            for neu_schluessel, alt_schluessel in (("alle", "all_frames"), ("ausserhalb", "outside_assumed_flicker")):
                differenz = abs(neu[neu_schluessel]["vollbild"]["sobel"] - alt[alt_schluessel]["sobel_mean"])
                if differenz > 1e-6:
                    raise ValueError(f"{quelle.name}: Sobel-Abweichung {differenz:.8g} ({neu_schluessel})")
        print(f"{quelle.name}: {neu['frames']} Frames", flush=True)
        return neu

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        videos = list(pool.map(berechnen, quellen))
    args.ausgabe.mkdir(parents=True, exist_ok=True)
    dokument = {"annahme_flicker_s": DEFAULT_FLICKER, "videos": videos,
                "versionen": {"opencv": cv2.__version__, "pyav": av.__version__, "numpy": np.__version__}}
    (args.ausgabe / "zusammenfassung.json").write_text(json.dumps(dokument, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.ausgabe / "videomittelwerte.csv").open("w", encoding="utf-8", newline="") as datei:
        writer = csv.writer(datei)
        writer.writerow(["Video", "Gruppe", "Teilmenge", "Frames", "Bildbereich", *MERKMALE])
        for video in videos:
            for teilmenge, framefeld in (("alle", "frames"), ("ausserhalb", "frames_ausserhalb")):
                for bereich in BEREICHE:
                    writer.writerow([video["video"], video["gruppe"], teilmenge, video[framefeld], bereich,
                                     *(f"{video[teilmenge][bereich][m]:.8f}" for m in MERKMALE)])


if __name__ == "__main__":
    main()
