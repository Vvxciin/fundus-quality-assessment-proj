"""Sobel-Baseline für vollständige Videos, mit CSV-Cache und deutschen Grafiken.

Wie im ersten Versuch: Graustufen -> Sobel X/Y (3x3, float64) -> mittlerer
Gradientenbetrag. Ein hoher Wert ist noch keine Good/Bad-Entscheidung.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from dataclasses import dataclass
import hashlib
import json
from itertools import zip_longest
from pathlib import Path, PurePosixPath
import sys
import zipfile

import av
import cv2
import numpy as np

ALGORITHM = "gray-bgr-opencv-sobel3-float64-mean-v1"
DEFAULT_FLICKER = [(50.0, 70.0), (150.0, 170.0), (250.0, 270.0)]
COLUMNS = ["frame_index", "time_seconds", "sobel_mean", "brightness_mean"]
VIDEO_SUFFIXES = {".dv", ".avi", ".mp4", ".mov", ".mkv"}


@dataclass(frozen=True)
class VideoSource:
    path: Path
    member: str | None
    label: str

    @property
    def name(self) -> str:
        return PurePosixPath(self.member).stem if self.member else self.path.stem

    def identity(self) -> dict:
        stat = self.path.stat()
        identity = {"path": str(self.path.resolve()), "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns, "member": self.member}
        if self.member:
            with zipfile.ZipFile(self.path) as archive:
                entry = archive.getinfo(self.member)
            identity.update(member_size=entry.file_size, crc32=entry.CRC)
        return identity

    @contextmanager
    def open(self):
        if self.member:
            with zipfile.ZipFile(self.path) as archive, archive.open(self.member) as stream:
                yield stream
        else:
            with self.path.open("rb") as stream:
                yield stream


def infer_label(parts) -> str:
    good = {"gute videos", "good", "good videos"}
    bad = {"schlechte videos", "bad", "bad videos"}
    labels = {"Good" for p in parts if p.casefold() in good}
    labels |= {"Bad" for p in parts if p.casefold() in bad}
    if len(labels) != 1:
        raise ValueError("Good/Bad-Ordner nicht eindeutig. Bei Einzelvideos --label verwenden.")
    return labels.pop()


def discover(path: Path, label: str | None = None) -> list[VideoSource]:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_file() and path.suffix.casefold() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist()
                     if PurePosixPath(n).suffix.casefold() in VIDEO_SUFFIXES]
        sources = [VideoSource(path, n, label or infer_label(PurePosixPath(n).parts[:-1]))
                   for n in names]
    elif path.is_dir():
        sources = [VideoSource(p, None, label or infer_label(p.parts[:-1]))
                   for p in sorted(path.rglob("*"))
                   if p.is_file() and p.suffix.casefold() in VIDEO_SUFFIXES]
    elif path.suffix.casefold() in VIDEO_SUFFIXES:
        sources = [VideoSource(path, None, label or infer_label(path.parts[:-1]))]
    else:
        raise ValueError("Eingabe muss ein Video, Videoordner oder ZIP-Archiv sein.")
    if not sources:
        raise ValueError("Keine Videos gefunden.")
    names = [s.name.casefold() for s in sources]
    if len(names) != len(set(names)):
        raise ValueError("Doppelte Videonamen würden Cache-Dateien überschreiben.")
    if any(not s.name or any(c in s.name for c in '<>:"/\\|?*') for s in sources):
        raise ValueError("Videoname ist nicht als Ausgabedatei geeignet.")
    return sorted(sources, key=lambda s: (s.label != "Good", s.name))


def sobel_metrics(gray: np.ndarray) -> tuple[float, float]:
    """Unveränderte Baseline: mittlere Kantenstärke und mittlerer Grauwert."""
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gx, gy)
    return float(magnitude.mean()), float(gray.mean())


def measurement_key(source: VideoSource) -> dict:
    # Flickerfenster gehören zur Auswertung, nicht zur Frame-Berechnung.
    return {"algorithm": ALGORITHM, "source": source.identity(),
            "opencv": cv2.__version__, "pyav": av.__version__, "numpy": np.__version__}


def read_scores(path: Path, metadata: dict) -> np.ndarray:
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["csv_sha256"]:
        raise ValueError("CSV-Prüfsumme stimmt nicht.")
    with path.open(encoding="utf-8", newline="") as stream:
        if next(csv.reader(stream)) != COLUMNS:
            raise ValueError("Unerwartete CSV-Spalten.")
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    if data.shape != (metadata["frames"], 4) or not len(data):
        raise ValueError("Unvollständiger CSV-Cache.")
    if not np.isfinite(data).all() or not np.array_equal(data[:, 0], np.arange(len(data))):
        raise ValueError("Ungültige Messwerte/Frame-Indizes.")
    if np.any(np.diff(data[:, 1]) <= 0):
        raise ValueError("Zeitstempel sind nicht streng aufsteigend.")
    return data


def analyze(source: VideoSource, cache_dir: Path, force: bool = False):
    cache_dir.mkdir(parents=True, exist_ok=True)
    csv_path = cache_dir / f"{source.name}.csv"
    meta_path = cache_dir / f"{source.name}.json"
    key = measurement_key(source)
    if not force and meta_path.exists() and csv_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            if metadata["key"] == key:
                data = read_scores(csv_path, metadata)
                if metadata["label"] != source.label:
                    metadata["label"] = source.label
                    temporary = meta_path.with_suffix(".json.tmp")
                    temporary.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
                    temporary.replace(meta_path)
                print(f"{source.name}: Cache, {len(data)} Frames", flush=True)
                return metadata, data
        except (ValueError, KeyError, OSError, StopIteration):
            print(f"{source.name}: Cache ungültig, neu berechnen", flush=True)

    print(f"{source.name} ({source.label}): vollständige Analyse", flush=True)
    rows = []
    with source.open() as handle, av.open(handle) as container:
        if not container.streams.video:
            raise ValueError(f"{source.name}: kein Videostream")
        video = container.streams.video[0]
        rate = video.guessed_rate or video.codec_context.framerate
        if rate is None or float(rate) <= 0:
            raise ValueError(f"{source.name}: Bildrate nicht bestimmbar")
        fps = float(rate)
        expected_duration = (float(video.duration * video.time_base)
                             if video.duration is not None else None)
        metadata = {"video": source.name, "label": source.label,
                    "fps": fps, "width": video.width, "height": video.height,
                    "stream_duration_seconds": expected_duration,
                    "timestamp_source": "decoded_pts", "interlaced_frames": 0}
        first_timestamp = None
        for index, frame in enumerate(container.decode(video=0)):
            if frame.pts is None or frame.time_base is None:
                raise ValueError(f"{source.name}: Frame {index} ohne Zeitstempel")
            timestamp = float(frame.pts * frame.time_base)
            if first_timestamp is None:
                first_timestamp = timestamp
            seconds = timestamp - first_timestamp
            if rows and seconds <= rows[-1][1]:
                raise ValueError(f"{source.name}: nicht aufsteigende Zeitstempel")
            gray = cv2.cvtColor(frame.to_ndarray(format="bgr24"), cv2.COLOR_BGR2GRAY)
            sobel, brightness = sobel_metrics(gray)
            rows.append((index, seconds, sobel, brightness))
            metadata["interlaced_frames"] += int(frame.interlaced_frame)
            if (index + 1) % 1000 == 0:
                print(f"  {source.name}: {index + 1} Frames", flush=True)
    if not rows:
        raise ValueError(f"{source.name}: keine dekodierbaren Frames")
    duration = rows[-1][1] + 1 / fps
    if expected_duration and duration + 1 / fps < expected_duration:
        raise ValueError(f"{source.name}: Dekodierung vor dem erwarteten Ende abgebrochen")
    # PAL-DV enthält genau 144000 Bytes pro 720x576/25-Frame. Erfasst auch
    # abgeschnittene letzte Frames, die der Decoder sonst still verwerfen kann.
    suffix = PurePosixPath(source.member).suffix if source.member else source.path.suffix
    if suffix.casefold() == ".dv" and (video.width, video.height, fps) == (720, 576, 25.0):
        size = key["source"].get("member_size", key["source"]["size"])
        if size != len(rows) * 144000:
            raise ValueError(f"{source.name}: PAL-DV-Größe passt nicht zur Framezahl")
    data = np.asarray(rows, dtype=float)
    csv_temp = csv_path.with_suffix(".csv.tmp")
    with csv_temp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    csv_temp.replace(csv_path)
    metadata.update(key=key, frames=len(data), duration_seconds=duration,
                    csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest())
    meta_temp = meta_path.with_suffix(".json.tmp")
    meta_temp.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    meta_temp.replace(meta_path)
    print(f"{source.name}: fertig, {len(data)} Frames, {duration:.2f} s", flush=True)
    return metadata, data


def outside_windows(times: np.ndarray, windows) -> np.ndarray:
    keep = np.ones(len(times), dtype=bool)
    for start, end in windows:
        keep &= ~((times >= start) & (times <= end))
    return keep


def statistics(data: np.ndarray) -> dict:
    if not len(data):
        return {"frames": 0, "sobel_mean": None, "sobel_median": None,
                "sobel_q10": None, "sobel_q90": None, "brightness_mean": None}
    return {"frames": len(data), "sobel_mean": float(data[:, 2].mean()),
            "sobel_median": float(np.median(data[:, 2])),
            "sobel_q10": float(np.quantile(data[:, 2], .1)),
            "sobel_q90": float(np.quantile(data[:, 2], .9)),
            "brightness_mean": float(data[:, 3].mean())}


def summarize(results, windows, output: Path):
    summaries = []
    for metadata, data in results:
        summaries.append({"video": metadata["video"], "label": metadata["label"],
                          "frames": metadata["frames"], "fps": metadata["fps"],
                          "width": metadata["width"], "height": metadata["height"],
                          "duration_seconds": metadata["duration_seconds"],
                          "interlaced_frames": metadata["interlaced_frames"],
                          "all_frames": statistics(data),
                          "outside_assumed_flicker": statistics(data[outside_windows(data[:, 1], windows)])})
    document = {"algorithm": ALGORITHM, "full_videos": True,
                "assumed_flicker_windows_seconds_inclusive": windows,
                "note": "Explorative Merkmalsanalyse; keine Frame-Labels oder Klassifikationsgenauigkeit.",
                "videos": summaries}
    (output / "summary.json").write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["video", "label", "subset", "frames", "sobel_mean", "sobel_median",
                         "sobel_q10", "sobel_q90", "brightness_mean"])
        for item in summaries:
            for subset in ("all_frames", "outside_assumed_flicker"):
                values = item[subset]
                writer.writerow([item["video"], item["label"], subset] + list(values.values()))
    return summaries


def make_plots(results, windows, output: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plots = output / "plots"
    plots.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    names = [m["video"] for m, _ in results]
    colors = ["#238464" if m["label"] == "Good" else "#bd514b" for m, _ in results]
    kept = [d[outside_windows(d[:, 1], windows)] for _, d in results]
    footer = "Alle Frames verarbeitet · Videolabels, keine Frame-Labels · Keine Klassifikationsgenauigkeit"
    outside_label = "Ohne angenommene Flickerintervalle" if windows else "Keine Intervalle ausgeschlossen"

    fig, ax = plt.subplots(figsize=(12, 6))
    positions = np.arange(len(names))
    means_all = [d[:, 2].mean() for _, d in results]
    means_kept = [d[:, 2].mean() if len(d) else np.nan for d in kept]
    ax.bar(positions - .2, means_all, .38, color=colors, alpha=.45)
    bars = ax.bar(positions + .2, means_kept, .38, color=colors)
    for bar, value in zip(bars, means_kept):
        if np.isfinite(value):
            ax.annotate(f"{value:.2f}".replace(".", ","), (bar.get_x()+bar.get_width()/2, value),
                        xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
    ax.set_xticks(positions, names)
    ax.set_ylabel("Mittlerer Sobel-Gradientenbetrag")
    ax.set_title("Sobel-Baseline: gute und schlechte Videoaufnahmen", loc="left", weight="bold")
    ax.set_ylim(0, max(means_all + [v for v in means_kept if np.isfinite(v)]) * 1.25 + 1)
    ax.legend(handles=[Patch(facecolor="#238464", label="Good"), Patch(facecolor="#bd514b", label="Bad"),
                       Patch(facecolor="gray", alpha=.45, label="Gesamtes Video"),
                       Patch(facecolor="gray", label=outside_label)], loc="upper left", ncol=2, fontsize=9)
    fig.text(.5, .02, footer, ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(plots / "01_sobel_vergleich.png", dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6))
    nonempty = [(i, d) for i, d in enumerate(kept) if len(d)]
    if nonempty:
        box = ax.boxplot([d[:, 2] for _, d in nonempty], positions=[i+1 for i, _ in nonempty],
                         patch_artist=True, showfliers=False, widths=.6)
        for patch, (i, _) in zip(box["boxes"], nonempty): patch.set_facecolor(colors[i]); patch.set_alpha(.65)
    ax.set_xticks(np.arange(len(names))+1, names)
    ax.set_ylabel("Sobel-Gradientenbetrag pro Frame")
    ax.set_title("Verteilungen statt nur Mittelwerte", loc="left", weight="bold")
    fig.text(.5, .045, outside_label + " · Box: mittlere 50 % · Linie: Median · Ausreißer ausgeblendet", ha="center", fontsize=9)
    fig.text(.5, .015, "Benachbarte Frames sind keine unabhängigen Stichproben.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, 1)); fig.savefig(plots / "02_sobel_verteilungen.png", dpi=170); plt.close(fig)

    columns = 2 if len(results) > 1 else 1
    groups = [[r for r in results if r[0]["label"] == label] for label in ("Good", "Bad")]
    ordered = [r for pair in zip_longest(*groups) for r in pair if r]
    # A plain grid remains valid for unequal group sizes or a single selected video.
    rows = (len(ordered) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(13, 2.2 * rows), squeeze=False, sharex=True)
    for ax, (meta, data) in zip(axes.flat, ordered):
        color = "#238464" if meta["label"] == "Good" else "#bd514b"
        ax.plot(data[:, 1], data[:, 2], lw=.35, color=color)
        for start, end in windows: ax.axvspan(start, end, color="#d79732", alpha=.17)
        ax.set_title(f"{meta['video']} ({meta['label']})", loc="left", fontsize=10)
        ax.set_ylabel("Sobel", fontsize=9)
    for ax in list(axes.flat)[len(ordered):]: ax.set_visible(False)
    for ax in axes[-1]: ax.set_xlabel("Zeit (s)")
    fig.suptitle("Zeitverläufe aller vollständig analysierten Videos", weight="bold")
    fig.text(.5, .005, "Orange Flächen: angenommene Flickerintervalle. Achsenskalierung je Video beachten.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .025, 1, .98)); fig.savefig(plots / "03_zeitverlaeufe.png", dpi=150); plt.close(fig)

    focus = next((r for r in results if r[0]["video"] == "ESC01"), results[0])
    meta, data = focus
    if windows:
        start, end = windows[0]
        left, right = start + (end-start)/4, start + (end-start)/4 + 1
    else:
        left, right = data[0, 1], min(data[-1, 1], data[0, 1]+1)
    selected = data[(data[:, 1] >= left) & (data[:, 1] <= right)]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    if len(selected):
        axes[0].plot(selected[:, 1], selected[:, 2], ".-", color="#326b9c")
        axes[1].plot(selected[:, 1], selected[:, 3], ".-", color="#bb752b")
    axes[0].set_ylabel("Sobel-Gradientenbetrag"); axes[1].set_ylabel("Mittlerer Grauwert (0–255)")
    axes[1].set_xlabel("Zeit (s)")
    axes[0].set_title(f"{meta['video']}: Sobel und Helligkeit im Detail", loc="left", weight="bold")
    fig.text(.5, .015, "Gemeinsame Schwankungen sind ein Hinweis auf Beleuchtungseinfluss, keine Qualitätsklassifikation.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(plots / "04_flicker_detail.png", dpi=170); plt.close(fig)


def parse_window(text: str):
    try:
        start, end = map(float, text.split(":"))
        if not np.isfinite([start, end]).all() or start < 0 or end <= start:
            raise ValueError
        return start, end
    except ValueError:
        raise argparse.ArgumentTypeError("Intervall als START:ENDE, z.B. 50:70") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Video, Ordner oder ZIP")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1]/"results/batch")
    parser.add_argument("--label", choices=["Good", "Bad"], help="Explizites Videolabel (sonst aus Ordnernamen)")
    parser.add_argument("--only", nargs="+", help="Nur diese Videonamen, z.B. ESC01 ESC02")
    parser.add_argument("--flicker", type=parse_window, nargs="*", default=DEFAULT_FLICKER,
                        help="Angenommene Intervalle START:ENDE; ohne Werte: keine ausschließen")
    parser.add_argument("--force", action="store_true", help="Cache neu berechnen")
    parser.add_argument("--plots-only", action="store_true", help="Nur gespeicherte Messwerte auswerten")
    args = parser.parse_args(argv)
    if not args.input and not args.plots_only:
        parser.error("--input ist erforderlich, außer bei --plots-only")
    if args.force and args.plots_only:
        parser.error("--force und --plots-only sind nicht kombinierbar")
    # Große Threadpools sind für diese kleinen Frames häufig langsamer.
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True, exist_ok=True)
    cache = args.output / "cache"
    results = []
    try:
        if args.plots_only:
            for path in sorted(cache.glob("*.json")):
                metadata = json.loads(path.read_text(encoding="utf-8"))
                if args.only and metadata["video"] not in args.only: continue
                if metadata["key"]["algorithm"] != ALGORITHM:
                    raise ValueError("Cache stammt aus einem anderen Algorithmus.")
                results.append((metadata, read_scores(path.with_suffix(".csv"), metadata)))
        else:
            sources = discover(args.input, args.label)
            if args.only:
                unknown = set(args.only) - {s.name for s in sources}
                if unknown: raise ValueError(f"Videos nicht gefunden: {sorted(unknown)}")
                sources = [s for s in sources if s.name in args.only]
            for source in sources:
                results.append(analyze(source, cache, args.force))
        if not results:
            raise ValueError("Keine Messwerte gefunden.")
        if args.only and set(args.only) != {m["video"] for m, _ in results}:
            raise ValueError("Nicht alle angefragten Videos im Cache vorhanden.")
        results.sort(key=lambda r: (r[0]["label"] != "Good", r[0]["video"]))
        summaries = summarize(results, args.flicker, args.output)
        make_plots(results, args.flicker, args.output)
        print(f"Fertig: {len(summaries)} Videos, {sum(x['frames'] for x in summaries)} Frames")
        print(f"Ausgabe: {args.output.resolve()}")
    except (OSError, ValueError, KeyError, StopIteration, av.error.FFmpegError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
