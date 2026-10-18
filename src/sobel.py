
from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt

# Project dir
ROOT = Path(__file__).resolve().parents[1]
FRAME_DIR = ROOT / "data" / "frames" / "good" / "ESC01"
RESULT_DIR = ROOT / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

FPS = 25

# Get all extracted frames in order
frames = sorted(FRAME_DIR.glob("frame_*.png"))

if not frames:
    raise RuntimeError(f"No frames found in {FRAME_DIR}")

times = []
scores = []
brightness_values = []

for i, frame_path in enumerate(frames):
    gray = cv2.imread(
        str(frame_path),
        cv2.IMREAD_GRAYSCALE
    )

    if gray is None:
        print(f"Skipping unreadable frame: {frame_path}")
        continue

    # Average brightness (0 = black, 255 = white)
    brightness = float(np.mean(gray))
    brightness_values.append(brightness)

    # Calculate horizontal and vertical gradients
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    # Gradient magnitude
    magnitude = cv2.magnitude(gx, gy)

    # Average edge strength
    sharpness = float(np.mean(magnitude))

    # Frame numbering starts at 1
    frame_number = int(frame_path.stem.split("_")[-1])
    time_seconds = (frame_number - 1) / FPS

    times.append(time_seconds)
    scores.append(sharpness)

    if i % 500 == 0:
        print(f"Processed {i}/{len(frames)} frames")


# G1: Full video overview
plt.figure(figsize=(20, 6))
plt.plot(times, scores, linewidth=0.3, alpha=0.7)
plt.xlabel("Time (seconds)")
plt.ylabel("Mean Sobel gradient magnitude")
plt.title("ESC01 - Sobel sharpness (Full Video)")
plt.grid(True)
plt.tight_layout()

# Save1
plt.savefig(RESULT_DIR / "ESC01_sobel_full.png", dpi=150)


# G2: Zoomed view (50–70 seconds)
plt.figure(figsize=(18, 6))
plt.plot(times, scores, linewidth=0.5, alpha=0.8)
plt.xlim(50, 70)
plt.xlabel("Time (seconds)")
plt.ylabel("Mean Sobel gradient magnitude")
plt.title("ESC01 - Sobel sharpness (50–70 seconds)")
plt.grid(True)
plt.tight_layout()

# Save2
plt.savefig(RESULT_DIR / "ESC01_sobel_zoom.png", dpi=150)


# ------------------------------
# 2 Compare Sobel and brightness


fig, ax1 = plt.subplots(figsize=(18, 6))

# Blue line: Sobel score
ax1.plot(
    times, scores,
    color="blue",
    linewidth=0.7,
    alpha=0.8,
    label="Sobel"
)

ax1.set_xlabel("Time (seconds)")
ax1.set_ylabel("Sobel gradient magnitude", color="blue")
ax1.tick_params(axis="y", labelcolor="blue")

# Create a second Y-axis for brightness
ax2 = ax1.twinx()

# Orange line: Brightness
ax2.plot(
    times, brightness_values,
    color="orange",
    linewidth=0.7,
    alpha=0.8,
    label="Brightness"
)

ax2.set_ylabel("Mean brightness (0-255)", color="orange")
ax2.tick_params(axis="y", labelcolor="orange")

# Zoom into 55-57 seconds
ax1.set_xlim(10, 30)

ax1.set_title("ESC01 - Sobel vs Brightness (10-30 seconds)")
ax1.grid(True, alpha=0.3)

fig.tight_layout()

# Save graph
fig.savefig(
    RESULT_DIR / "ESC01_sobel_vs_brightness_10_30.png",
    dpi=150
)

# Display all graphs
plt.show()

print(f"Processed {len(scores)} frames")
print(f"Mean Sobel score: {np.mean(scores):.2f}")
print("Graphs saved in the results folder.")
