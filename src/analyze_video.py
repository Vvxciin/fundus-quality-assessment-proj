
from pathlib import Path
import cv2
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

RESULT_DIR = ROOT / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

VIDEOS = {
    "ESC01 (Good)": Path(
        r"C:\Users\Ve\Downloads\Projektfach_Bildqualität 2026_27\Gute Videos\ESC01.dv"
    ),
    "ESC02 (Bad)": Path(
        r"C:\Users\Ve\Downloads\Projektfach_Bildqualität 2026_27\Schlechte Videos\ESC02.dv"
    ),
}


# Analyze without extracting frames
def analyze_video(VIDEO):
    cap = cv2.VideoCapture(str(VIDEO))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO}")

    # FFprobe confirmed that both videos have 25 FPS
    # terminal:
    # ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -show_entries format=duration -of default=noprint_wrappers=1 "PATH_TO_VIDEO"
    fps = 25.0

    print(f"Analyzing {VIDEO.name}, using FPS: {fps}")

    times = []
    sobel_scores = []
    brightness_values = []

    frame_index = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # Video looks GRAY but OpenCV may still decode it as BGR
        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        brightness = float(np.mean(gray))

        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        magnitude = cv2.magnitude(gx, gy)
        sobel = float(np.mean(magnitude))

        times.append(frame_index / fps)
        sobel_scores.append(sobel)
        brightness_values.append(brightness)

        frame_index += 1

        if frame_index % 500 == 0:
            print(f"Processed {frame_index} frames")

    cap.release()

    return times, sobel_scores, brightness_values


# Run analysis 
results = {}

for name, VIDEO in VIDEOS.items():
    results[name] = analyze_video(VIDEO)


# Plot both videos in the same fig
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(18, 9), sharex=True
)

print("\n--- Comparison outside flicker intervals ---")

for name, (times, sobel_scores, brightness_values) in results.items():

    times = np.array(times)
    sobel_scores = np.array(sobel_scores)
    brightness_values = np.array(brightness_values)

    # Exclude flicker intervals
    mask = (
        ~((times >= 50) & (times <= 70)) &
        ~((times >= 150) & (times <= 170)) &
        ~((times >= 250) & (times <= 270))
    )

    clean_sobel = sobel_scores[mask]
    clean_brightness = brightness_values[mask]

    print(f"\n{name}")
    print(f"Mean Sobel: {np.mean(clean_sobel):.2f}")
    print(f"Median Sobel: {np.median(clean_sobel):.2f}")
    print(f"Mean brightness: {np.mean(clean_brightness):.2f}")

for name, (times, sobel_scores, brightness_values) in results.items():

    color = "green" if "Good" in name else "red"

    ax1.plot(
        times, sobel_scores,
        color=color, linewidth=0.4,
        alpha=0.7, label=name
    )

    ax2.plot(
        times, brightness_values,
        color=color, linewidth=0.4,
        alpha=0.7, label=name
    )

ax1.set_title("Sobel - Good vs Bad")
ax1.set_ylabel("Sobel gradient magnitude")
ax1.legend()
ax1.grid(True)

ax2.set_title("Brightness - Good vs Bad")
ax2.set_xlabel("Time (seconds)")
ax2.set_ylabel("Mean brightness (0-255)")
ax2.legend()
ax2.grid(True)

fig.tight_layout()

fig.savefig(
    RESULT_DIR / "ESC01_vs_ESC02_comparison.png",
    dpi=150
)

print("\n--- Full video statistics (including flicker) ---")

for name, (_, sobel_scores, brightness_values) in results.items():
    print(f"\n{name}")
    print(f"Mean Sobel: {np.mean(sobel_scores):.2f}")
    print(f"Median Sobel: {np.median(sobel_scores):.2f}")
    print(f"Mean brightness: {np.mean(brightness_values):.2f}")

plt.show()
