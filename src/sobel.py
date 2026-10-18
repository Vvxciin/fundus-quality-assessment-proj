
from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt

# Project directories
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

for i, frame_path in enumerate(frames):
    gray = cv2.imread(
        str(frame_path),
        cv2.IMREAD_GRAYSCALE
    )

    if gray is None:
        print(f"Skipping unreadable frame: {frame_path}")
        continue

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


# GRAPH 1: Full video overview
plt.figure(figsize=(20, 6))
plt.plot(times, scores, linewidth=0.3, alpha=0.7)
plt.xlabel("Time (seconds)")
plt.ylabel("Mean Sobel gradient magnitude")
plt.title("ESC01 - Sobel sharpness (Full Video)")
plt.grid(True)
plt.tight_layout()

# Save BEFORE showing
plt.savefig(RESULT_DIR / "ESC01_sobel_full.png", dpi=150)


# GRAPH 2: Zoomed view (50–70 seconds)
plt.figure(figsize=(18, 6))
plt.plot(times, scores, linewidth=0.5, alpha=0.8)
plt.xlim(50, 70)
plt.xlabel("Time (seconds)")
plt.ylabel("Mean Sobel gradient magnitude")
plt.title("ESC01 - Sobel sharpness (50–70 seconds)")
plt.grid(True)
plt.tight_layout()

# Save BEFORE showing
plt.savefig(RESULT_DIR / "ESC01_sobel_zoom.png", dpi=150)

# Show both graphs
plt.show()

print(f"Processed {len(scores)} frames")
print(f"Mean Sobel score: {np.mean(scores):.2f}")
print("Graphs saved in the results folder.")
