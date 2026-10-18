## Frames extrahieren

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