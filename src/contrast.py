
from pathlib import Path
import csv

import cv2
import numpy as np
import matplotlib.pyplot as plt


# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = Path(
    r"C:\Users\Ve\Downloads\Projektfach_Bildqualität 2026_27"
)

RESULT_DIR = ROOT / "results" / "contrast"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

FPS = 25.0


# ==================================================
# 2. VIDEO LIST
# ==================================================

VIDEOS = {
    "AT012": "Good",
    "ESC01": "Good",
    "ESC04": "Good",
    "ESC16": "Good",
    "ESC19": "Good",
    "ESC02": "Bad",
    "ESC05": "Bad",
    "ESC06": "Bad",
    "ESC09": "Bad",
    "ESC18": "Bad",
}

GOOD_VIDEOS = [
    "AT012", "ESC01", "ESC04", "ESC16", "ESC19"
]

BAD_VIDEOS = [
    "ESC02", "ESC05", "ESC06", "ESC09", "ESC18"
]


# ==================================================
# 3. ANALYZE ONE VIDEO
# ==================================================

def analyze_video(video_path):

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {video_path}"
        )

    times = []
    brightness_values = []
    contrast_values = []

    frame_index = 0

    while True:

        success, frame = cap.read()

        if not success:
            break

        # Convert to grayscale
        if frame.ndim == 3:
            gray = cv2.cvtColor(
                frame, cv2.COLOR_BGR2GRAY
            )
        else:
            gray = frame

        # Mean grayscale intensity
        brightness = float(np.mean(gray))

        # Global grayscale contrast
        contrast = float(np.std(gray))

        times.append(frame_index / FPS)
        brightness_values.append(brightness)
        contrast_values.append(contrast)

        frame_index += 1

        if frame_index % 1000 == 0:
            print(f"Processed {frame_index} frames")

    cap.release()

    return (
        np.array(times),
        np.array(brightness_values),
        np.array(contrast_values)
    )


# ==================================================
# 4. SUSPECTED FLICKER INTERVALS
# ==================================================

def create_flicker_mask(times):

    return (
        ~((times >= 50) & (times <= 70)) &
        ~((times >= 150) & (times <= 170)) &
        ~((times >= 250) & (times <= 270))
    )


# ==================================================
# 5. PLOT ONE VIDEO
# ==================================================

def plot_video(name, label, times, brightness, contrast):

    fig, ax1 = plt.subplots(figsize=(18, 6))

    # Blue: Contrast
    ax1.plot(
        times,
        contrast,
        color="blue",
        linewidth=0.5
    )

    ax1.set_ylabel(
        "Contrast (grayscale standard deviation)",
        color="blue"
    )
    ax1.tick_params(axis="y", labelcolor="blue")

    # Orange: Brightness
    ax2 = ax1.twinx()

    ax2.plot(
        times,
        brightness,
        color="orange",
        linewidth=0.5,
        alpha=0.7
    )

    ax2.set_ylabel("Brightness (0-255)", color="orange")
    ax2.tick_params(axis="y", labelcolor="orange")

    ax1.set_xlabel("Time (seconds)")
    ax1.set_title(
        f"{name} ({label}) - Contrast vs Brightness"
    )
    ax1.grid(True, alpha=0.3)

    fig.tight_layout()

    fig.savefig(
        RESULT_DIR / f"{name}_contrast_vs_brightness.png",
        dpi=150
    )

    plt.close(fig)


# ==================================================
# 6. PROCESS ALL 10 VIDEOS
# ==================================================

summary = []
all_results = {}

for video_name, label in VIDEOS.items():

    folder = (
        "Gute Videos"
        if label == "Good"
        else "Schlechte Videos"
    )

    video_path = DATA_DIR / folder / f"{video_name}.dv"

    print(f"\nAnalyzing {video_name} ({label})")

    if not video_path.is_file():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    times, brightness, contrast = analyze_video(video_path)

    if len(times) == 0:
        raise RuntimeError(
            f"No frames decoded: {video_name}"
        )

    # Store results for the combined 5x2 plot
    all_results[video_name] = {
        "times": times,
        "brightness": brightness,
        "contrast": contrast
    }

    # Full-video statistics
    mean_brightness = float(np.mean(brightness))
    mean_contrast = float(np.mean(contrast))

    correlation = float(
        np.corrcoef(brightness, contrast)[0, 1]
    )

    # Exclude suspected flicker only for statistics
    mask = create_flicker_mask(times)

    clean_contrast = contrast[mask]
    clean_brightness = brightness[mask]

    mean_clean = float(np.mean(clean_contrast))
    median_clean = float(np.median(clean_contrast))
    mean_brightness_clean = float(
        np.mean(clean_brightness)
    )

    print(f"Frames: {len(times)}")
    print(f"Mean brightness: {mean_brightness:.2f}")
    print(f"Mean contrast: {mean_contrast:.2f}")
    print(f"Correlation: {correlation:.3f}")
    print(f"Mean contrast without flicker: {mean_clean:.2f}")
    print(f"Median contrast without flicker: {median_clean:.2f}")

    # Store summary statistics
    summary.append({
        "video": video_name,
        "label": label,
        "frames": len(times),
        "mean_brightness": mean_brightness,
        "mean_contrast": mean_contrast,
        "correlation": correlation,
        "mean_contrast_no_flicker": mean_clean,
        "median_contrast_no_flicker": median_clean,
        "mean_brightness_no_flicker": mean_brightness_clean
    })

    # Save individual timeline
    plot_video(
        video_name,
        label,
        times,
        brightness,
        contrast
    )


# ==================================================
# 7. COMBINED FIGURE: 5 ROWS x 2 COLUMNS
# ==================================================

fig, axes = plt.subplots(
    5, 2,
    figsize=(20, 22),
    sharex=True
)

for row in range(5):

    for col in range(2):

        # Left = Good, Right = Bad
        if col == 0:
            video_name = GOOD_VIDEOS[row]
            label = "Good"
        else:
            video_name = BAD_VIDEOS[row]
            label = "Bad"

        data = all_results[video_name]

        times = data["times"]
        brightness = data["brightness"]
        contrast = data["contrast"]

        ax1 = axes[row, col]

        # Left Y-axis: Contrast
        ax1.plot(
            times,
            contrast,
            color="blue",
            linewidth=0.5
        )

        ax1.set_ylabel("Contrast", color="blue")
        ax1.tick_params(axis="y", labelcolor="blue")

        # Right Y-axis: Brightness
        ax2 = ax1.twinx()

        ax2.plot(
            times,
            brightness,
            color="orange",
            linewidth=0.5,
            alpha=0.7
        )

        ax2.set_ylabel("Brightness", color="orange")
        ax2.tick_params(axis="y", labelcolor="orange")

        ax1.set_title(
            f"{video_name} ({label}) - Contrast vs Brightness"
        )

        ax1.set_xlim(0, 350)
        ax1.grid(True, alpha=0.3)

        if row == 4:
            ax1.set_xlabel("Time (seconds)")

fig.text(
    0.27, 0.985,
    "GOOD VIDEOS",
    ha="center",
    fontsize=18,
    fontweight="bold",
    color="green"
)

fig.text(
    0.73, 0.985,
    "BAD VIDEOS",
    ha="center",
    fontsize=18,
    fontweight="bold",
    color="red"
)

fig.tight_layout(rect=[0, 0, 1, 0.965])

fig.savefig(
    RESULT_DIR / "all_videos_contrast_comparison.png",
    dpi=150
)

plt.close(fig)


# ==================================================
# 8. GOOD VS BAD BAR CHART
# ==================================================

names = [item["video"] for item in summary]

means = [
    item["mean_contrast_no_flicker"]
    for item in summary
]

colors = [
    "green" if item["label"] == "Good" else "red"
    for item in summary
]

fig, ax = plt.subplots(figsize=(13, 6))

bars = ax.bar(
    names,
    means,
    color=colors,
    alpha=0.75
)

ax.set_xlabel("Video")
ax.set_ylabel("Mean contrast (grayscale standard deviation)")
ax.set_title(
    "Good vs Bad - Mean Contrast Without Suspected Flicker"
)
ax.grid(axis="y", alpha=0.3)
ax.set_axisbelow(True)

for bar, value in zip(bars, means):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        f"{value:.2f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

fig.tight_layout()

fig.savefig(
    RESULT_DIR / "good_vs_bad_mean_contrast.png",
    dpi=150
)


# ==================================================
# 9. SAVE SUMMARY CSV
# ==================================================

csv_path = RESULT_DIR / "contrast_summary.csv"

with open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=summary[0].keys()
    )

    writer.writeheader()
    writer.writerows(summary)


# ==================================================
# 10. FINISH
# ==================================================

print("\nAll videos processed!")
print(f"Results saved in: {RESULT_DIR}")

plt.show()
