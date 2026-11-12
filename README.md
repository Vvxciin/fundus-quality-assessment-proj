# Bildqualität im Augenhintergrundvideo

Projektfach an der Hochschule Niederrhein. Stand vom 12. November 2026.

Der Wochenversuch untersucht, wie sich ein fester zentraler Bildausschnitt auf Sobel, Grauwertkontrast, Helligkeit und Laplace auswirkt. Für jedes der zehn Kursvideos werden dieselben Frames einmal im Vollbild und einmal im mittleren Viertel der Bildfläche ausgewertet.

- [PowerPoint mit Vortragsnotizen](praesentation/Bildqualitaet_Bildausschnitt_DE.pptx)
- [Videomittelwerte als CSV](ergebnisse/videomittelwerte.csv)
- [Ergebnisse mit Framezahlen und Softwareversionen](ergebnisse/zusammenfassung.json)

## Methode

Der Ausschnitt umfasst die mittlere Hälfte der Breite und der Höhe. Bei 720 × 576 Pixeln sind das 360 × 288 Pixel ab Position (180, 144). Die Position bleibt über alle Frames konstant.

Sobel verwendet die mittlere Stärke des Gradienten. Kontrast ist die Standardabweichung der Grauwerte und Helligkeit deren arithmetischer Mittelwert. Für Laplace wird das Vollbild mit einem 3 × 3 Gaußfilter geglättet. Anschließend folgt die Laplace-Ableitung mit einem 3 × 3 Kernel und der mittlere Betrag der Antwort. Beide Kantenfilter laufen vor der räumlichen Auswahl auf dem Vollbild. Die jeweiligen Filterantworten werden anschließend über das Vollbild und über den Ausschnitt gemittelt.

Die Ergebnisdateien enthalten zwei Zusammenfassungen. `alle` umfasst sämtliche Frames. `ausserhalb` schließt die vorläufig angenommenen Flickerfenster 50–70, 150–170 und 250–270 Sekunden samt Grenzen aus. Die Zeitachse beruht auf den dekodierten Frame-Zeitstempeln. Die vorgegebenen Gruppenlabels beziehen sich auf ganze Videos. Für eine Validierung der Messqualität wären Bewertungen pro Frame und für konkrete Gefäßregionen erforderlich.

## Ergebnis

Die vollständige Auswertung umfasst 87.522 Frames. Außerhalb der angenommenen Flickerfenster bleiben 72.492 Frames. Im zentralen Ausschnitt steigen Sobel und der Betrag der Laplace-Antwort bei allen zehn Videomittelwerten. Der Grauwertkontrast sinkt bei allen zehn. Die Spannweiten der guten und schlechten Aufnahmen überlappen sich auch im Ausschnitt bei allen vier Merkmalen. ESC09 hat im Ausschnitt mit 41,64 weiterhin den höchsten Sobel-Mittelwert der Stichprobe.

## Auswertung ausführen

Python 3.12 und das separat bereitgestellte Kursarchiv verwenden. Ein entpackter Ordner mit den beiden Qualitätsgruppen funktioniert ebenfalls.

```powershell
python -m pip install -r requirements.txt
python src/bildausschnitt.py 'C:/Pfad/Kursarchiv.zip' --ausgabe ergebnisse --jobs 4
```

Mit `--referenz` kann die [JSON-Zusammenfassung der vorherigen Sobel-Auswertung](https://github.com/Vvxciin/fundus-quality-assessment-proj/blob/eren/sobel-auswertung/results/batch_summary/summary.json) übergeben werden. Der Lauf prüft dann pro Video die Framezahl und die Vollbild-Sobel-Mittelwerte beider Zeitmengen mit einer Toleranz von `1e-6`. `src/batch_sobel.py` stammt aus dieser früheren Auswertung und stellt das Einlesen sowie die Zeitfensterlogik bereit.

## Beiträge aus dem Team

- [Sobel-Auswertung](https://github.com/Vvxciin/fundus-quality-assessment-proj/tree/eren/sobel-auswertung)
- [Globaler Grauwertkontrast](https://github.com/Vvxciin/fundus-quality-assessment-proj/tree/feature/contrast-analysis)
- [Laplace und Maskierung von Thomas](https://github.com/Vvxciin/fundus-quality-assessment-proj/pull/3)

Die eigenen Laplace-Mittelwerte im Wochenversuch verwenden die vollständige Betragsantwort. Die Maskenschwellen aus Thomas’ Prototyp gehören zu dessen separatem Versuch.
