# Erste Untersuchung mit dem Sobel-Operator (ESC01)  GJ.18.10.26

**Status:** Vorläufige Untersuchung  
**Methode:** Sobel-Kantendetektion  
**Video:** ESC01 (als „Good“ klassifiziert)  
**Bildrate:** 25 FPS  
**Videolänge:** ca. 350 Sekunden (5:50 Minuten)  
**Anzahl der Frames:** ca. 8.752

## 1. Zielsetzung

Ziel dieser Untersuchung ist es, zu überprüfen, ob sich der Sobel-Operator zur Bewertung der Bildschärfe von Augenhintergrundaufnahmen eignet.

Dabei soll untersucht werden, wie sich die berechneten Schärfewerte im zeitlichen Verlauf verändern und welche Faktoren diese beeinflussen.

## 2. Vorgehensweise

1. Das Video ESC01 wurde mit seiner ursprünglichen Bildrate von 25 FPS in Einzelbilder zerlegt.
2. Die Einzelbilder wurden in Graustufen umgewandelt.
3. Auf jedes Bild wurde der Sobel-Operator in horizontaler und vertikaler Richtung angewendet.
4. Aus den beiden Gradienten wurde der Gradientenbetrag berechnet.
5. Der Mittelwert der Gradientenbeträge wurde als Sobel-Wert für jedes Bild verwendet.
6. Die berechneten Werte wurden über die gesamte Videodauer sowie für einen vergrößerten Zeitabschnitt visualisiert.

## 3. Erste Beobachtungen

- Die meisten Sobel-Werte liegen ungefähr zwischen 20 und 25.
- In bestimmten Zeitabschnitten treten starke und schnelle Schwankungen auf.
- Besonders auffällig sind die Bereiche von ca. 50–70, 150–170 und 250–270 Sekunden.
- Bei der Betrachtung des Videos wurde festgestellt, dass in diesen Bereichen ein schneller Wechsel zwischen dunklen und normal beleuchteten Bildern auftritt.
- Es wird vermutet, dass diese Schwankungen mit der Flickerstimulation während der Untersuchung zusammenhängen.

## 4. Vorläufige Interpretation

Die Ergebnisse deuten darauf hin, dass der Sobel-Wert nicht ausschließlich von der Bildschärfe abhängt, sondern auch durch Veränderungen der Beleuchtung beeinflusst werden kann.

Ein niedriger Sobel-Wert bedeutet daher nicht automatisch, dass ein Bild unscharf oder qualitativ schlecht ist.

Insbesondere während der vermuteten Flickerstimulation muss zwischen Beleuchtungsschwankungen und tatsächlicher Bildunschärfe unterschieden werden.

Diese Interpretation muss durch weitere Untersuchungen überprüft werden.

## 5. Nächste Schritte

1. Berechnung der mittleren Helligkeit für jedes Einzelbild.
2. Vergleich der Helligkeitswerte mit den Sobel-Werten.
3. Genauere Untersuchung der auffälligen Zeitabschnitte.
4. Visueller Vergleich ausgewählter Einzelbilder mit hohen und niedrigen Sobel-Werten.
5. Anwendung derselben Methode auf ein als „Bad“ klassifiziertes Video.
6. Untersuchung, ob der Sobel-Operator auch unabhängig von Beleuchtungsschwankungen aussagekräftige Schärfewerte liefert.

## 6. Vorläufiges Fazit

Die erste Implementierung des Sobel-Operators wurde erfolgreich auf das Video ESC01 angewendet.

Die Ergebnisse zeigen deutliche Schwankungen der Gradientenwerte, insbesondere während der beobachteten schnellen Helligkeitswechsel.

Es sind weitere Untersuchungen erforderlich, um zu beurteilen, ob und unter welchen Bedingungen der Sobel-Operator für die automatische Qualitätsbewertung von Augenhintergrundaufnahmen geeignet ist.