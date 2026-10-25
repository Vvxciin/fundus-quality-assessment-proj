# Fundus-Bildqualität: Sobel-Baseline

## Vollständige Videos vergleichen

`src/batch_sobel.py` ergänzt die ursprünglichen Versuche um eine reproduzierbare
Auswertung beliebig vieler Good/Bad-Videos. Der Sobel-Wert ist unverändert:
Graustufen, 3×3-Sobel in X/Y, Mittelwert des Gradientenbetrags. Es wird **noch
keine automatische Qualitätsklasse** aus dem Score abgeleitet.

Die [vollständige Auswertung der zehn Kursvideos](docs/Ergebnisse_Sobel.md)
enthält Ergebnisse für alle 87.522 Frames, vier Grafiken und die Grenzen
der Interpretation.

### Installation (Python 3.11 oder neuer)

Im Projektordner, beispielsweise unter Windows/PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-batch.txt
```

### Alle Videos aus dem Kurs-ZIP analysieren

```powershell
.venv\Scripts\python.exe src\batch_sobel.py --input "C:\Pfad\Projektfach_Bildqualität 2026_27.zip"
```

Das Archiv wird direkt gelesen; weder vollständiges Entpacken noch vorherige
PNG-Extraktion ist nötig. Alternativ kann `--input` auf einen entpackten Ordner
oder eine einzelne Videodatei zeigen. Good/Bad wird ausschließlich aus den
Ordnernamen `Gute Videos` / `Schlechte Videos` bzw. `good` / `bad` übernommen.
Für eine Datei ohne passenden Ordner: `--label Good` oder `--label Bad`.
Identische Dateinamen in verschiedenen Unterordnern werden als Fehler gemeldet.

```powershell
# Nur zwei Videos für eine kurze Demonstration
.venv\Scripts\python.exe src\batch_sobel.py --input "C:\Pfad\Projekt.zip" --only ESC01 ESC02

# Grafiken/Statistiken ohne erneute Video-Dekodierung erstellen
.venv\Scripts\python.exe src\batch_sobel.py --plots-only

# Eigene angenommene Flickerintervalle; Grenzwerte werden inklusive ausgeschlossen
.venv\Scripts\python.exe src\batch_sobel.py --plots-only --flicker 50:70 150:170 250:270

# Keine Intervalle ausschließen
.venv\Scripts\python.exe src\batch_sobel.py --plots-only --flicker
```

Ausgabe unter `results/batch/` (mit `--output` änderbar):

- `cache/<Video>.csv`: Frame-Index, tatsächlicher relativer Zeitstempel, Sobel, Helligkeit.
- `cache/<Video>.json`: Dateiprovenienz, Softwareversionen, Framezahl und CSV-Prüfsumme.
- `summary.csv` / `summary.json`: vollständige Videos, jeweils insgesamt und außerhalb angenommener Flickerintervalle.
- `plots/`: vier deutsch beschriftete Grafiken (Vergleich, Verteilungen, Zeitverläufe, Flickerdetail).

Ein unverändertes Video wird beim nächsten Aufruf aus dem Cache geladen.
`--force` erzwingt eine neue Berechnung. Änderungen an Flickerfenstern erfordern
keine erneute Frame-Berechnung. Mit `--plots-only` werden alle vorhandenen Caches
verwendet, optional gefiltert durch `--only`. Ein normaler Lauf berichtet nur die
in diesem Lauf ausgewählten Videos. Vorhandene CSV-/Grafikdateien werden aktualisiert.

### Interpretation

- Die Videoetiketten sind **keine Frame-Ground-Truth**. Auch Good-Videos können
  beeinträchtigte Frames enthalten.
- Die voreingestellten Flickerfenster sind Annahmen aus der ersten Untersuchung,
  keine automatisch erkannten oder fachlich bestätigten Stimulationszeiten.
- Der Score reagiert auch auf Beleuchtung, Bildinhalt und Rauschen. Deshalb
  werden keine Accuracy, Sensitivität oder festen Good/Bad-Schwellen behauptet.
- Die Baseline verwendet das ganze Bild einschließlich schwarzem Rand.
  Keine FOV-Maske, Normalisierung, Skalierung oder Deinterlacing wurde ergänzt.
  Solche Änderungen wären getrennt zu untersuchende Experimente.
- Zeitstempel kommen aus dekodierten PTS. Bei rohem DV kann `average_rate`
  irreführend sein; Bildrate und Zeitstempel werden deshalb getrennt erfasst.
- Die Prüfung auf ein vorzeitiges Ende nutzt verfügbare Stream-Metadaten;
  bei PAL-DV 720×576/25 wird zusätzlich die Framezahl mit der Dateigröße geprüft.

### Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Die Tests prüfen unter anderem den Einfluss von Intensität/Blur/Rauschen,
Intervallgrenzen, ZIP-/Datei-Gleichheit, Cache-Wiederverwendung und die numerische
Übereinstimmung mit der ursprünglichen Funktion an einem verlustfreien Testvideo.

Die ursprünglichen Skripte `src/sobel.py` und `src/analyze_video.py` bleiben als
dokumentierter erster Versuch erhalten. `requirements.txt` gehört zum
ursprünglichen Entwicklungsstand; für das Batch-Werkzeug genügt
`requirements-batch.txt`.

## Ursprünglicher Versuch: Frames extrahieren

Ich habe die Frames mit FFmpeg extrahiert. Dafür muss FFmpeg installiert sein:

```powershell
winget install --id Gyan.FFmpeg -e
```

Danach im VS-Code-Terminal im Hauptordner des Projekts folgenden Befehl ausführen:

```powershell
ffmpeg -i "PFAD_ZUM_VIDEO\ESC01.dv" -map 0:v:0 -fps_mode passthrough "data\frames\good\ESC01\frame_%06d.png"
```

`PFAD_ZUM_VIDEO` müsst ihr durch den Speicherort des Videos auf eurem PC ersetzen.

Falls der Ausgabeordner noch nicht existiert, vorher erstellen:

```powershell
New-Item -ItemType Directory -Force "data\frames\good\ESC01"
```

ESC01 hat 25 FPS und dauert ungefähr 5:50 Minuten. Bei mir wurden ca. 8.752 Frames extrahiert.

Die Bilder liegen danach unter:

```text
data/frames/good/ESC01/
```

Wichtig ist, dass wir alle die gleiche Ordnerstruktur für die Frames verwenden, damit die Python-Skripte ohne Änderungen funktionieren.

Die Videos und Frames bleiben lokal und werden durch `.gitignore` nicht auf GitHub hochgeladen.
