"""Meaningful baseline, IO and cache checks using a tiny lossless test video."""
from fractions import Fraction
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import batch_sobel as batch
import av
import cv2
import numpy as np


class MetricTests(unittest.TestCase):
    def test_constant_image_has_no_edges(self):
        self.assertEqual(batch.sobel_metrics(np.full((32, 32), 90, np.uint8)), (0.0, 90.0))

    def test_intensity_scaling_changes_sobel_even_without_blur(self):
        image = np.tile(np.arange(32, dtype=np.uint8), (32, 1))
        original, _ = batch.sobel_metrics(image)
        doubled, _ = batch.sobel_metrics(image * 2)
        offset, _ = batch.sobel_metrics(image + 30)
        self.assertAlmostEqual(doubled, original * 2)
        self.assertAlmostEqual(offset, original)

    def test_blur_reduces_but_noise_adds_edge_energy(self):
        image = np.zeros((64, 64), np.uint8)
        image[:, 32:] = 180
        # Gaussian blur spreads a single step without reducing mean absolute
        # gradient much. Alternating stripes test attenuation of fine detail.
        image[:, ::4] = 180
        sharp, _ = batch.sobel_metrics(image)
        blurred, _ = batch.sobel_metrics(cv2.GaussianBlur(image, (9, 9), 2))
        noisy = np.random.default_rng(42).integers(80, 120, (64, 64), dtype=np.uint8)
        self.assertLess(blurred, sharp)
        self.assertGreater(batch.sobel_metrics(noisy)[0], 0)

    def test_flicker_endpoints_are_excluded_inclusively(self):
        t = np.array([49.96, 50, 60, 70, 70.04, 150, 170, 250, 270, 270.04])
        np.testing.assert_array_equal(batch.outside_windows(t, batch.DEFAULT_FLICKER),
                                      [True, False, False, False, True, False, False, False, False, True])
        self.assertTrue(batch.outside_windows(t, []).all())

    def test_empty_filtered_statistics_do_not_make_nan(self):
        result = batch.statistics(np.empty((0, 4)))
        self.assertEqual(result["frames"], 0)
        self.assertIsNone(result["sobel_mean"])

    def test_bad_interval_rejected(self):
        for interval in ("70:50", "nan:70", "-1:4", "a:b", "5:5"):
            with self.assertRaises(batch.argparse.ArgumentTypeError):
                batch.parse_window(interval)


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "Gute Videos" / "Test ä.mkv"
        self.video.parent.mkdir()
        self.images = []
        with av.open(str(self.video), "w") as container:
            stream = container.add_stream("ffv1", rate=25)
            stream.width, stream.height, stream.pix_fmt = 32, 32, "gray"
            for i in range(8):
                image = np.tile(np.arange(32, dtype=np.uint8) * 4, (32, 1)) + i
                self.images.append(image)
                frame = av.VideoFrame.from_ndarray(image, format="gray")
                frame.pts, frame.time_base = i, Fraction(1, 25)
                for packet in stream.encode(frame): container.mux(packet)
            for packet in stream.encode(): container.mux(packet)
        self.cache = self.root / "cache"

    def test_folder_and_zip_decode_identically(self):
        source = batch.discover(self.root)[0]
        meta, data = batch.analyze(source, self.cache)
        self.assertEqual(meta["frames"], 8)
        self.assertEqual(meta["label"], "Good")
        self.assertAlmostEqual(meta["duration_seconds"], .32)
        np.testing.assert_allclose(data[:, 1], np.arange(8) / 25)
        archive = self.root / "videos.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.write(self.video, "Projekt ä/Gute Videos/Test ä.mkv")
        zipmeta, zipdata = batch.analyze(batch.discover(archive)[0], self.root / "zipcache")
        np.testing.assert_array_equal(data, zipdata)
        self.assertEqual(zipmeta["frames"], 8)
        for i, image in enumerate(self.images):
            expected = batch.sobel_metrics(image)
            np.testing.assert_allclose(data[i, 2:], expected, atol=0)

    def test_valid_cache_skips_decoder_and_changed_csv_is_detected(self):
        source = batch.discover(self.video)[0]
        meta, first = batch.analyze(source, self.cache)
        with patch.object(batch.av, "open", side_effect=AssertionError("decoder must not run")):
            _, cached = batch.analyze(source, self.cache)
        np.testing.assert_array_equal(first, cached)
        # Labelkorrekturen brauchen keine neue Dekodierung, müssen aber für
        # einen späteren --plots-only-Lauf im Manifest erhalten bleiben.
        relabeled = batch.VideoSource(source.path, source.member, "Bad")
        with patch.object(batch.av, "open", side_effect=AssertionError("decoder must not run")):
            batch.analyze(relabeled, self.cache)
        stored = json.loads((self.cache / (source.name + ".json")).read_text(encoding="utf-8"))
        self.assertEqual(stored["label"], "Bad")
        path = self.cache / (source.name + ".csv")
        path.write_text(path.read_text().replace("0.0", "9.0", 1), encoding="utf-8")
        with self.assertRaises(ValueError): batch.read_scores(path, meta)
        _, repaired = batch.analyze(source, self.cache)
        np.testing.assert_array_equal(first, repaired)

    def test_duplicate_names_and_ambiguous_labels_are_rejected(self):
        bad = self.root / "Schlechte Videos" / self.video.name
        bad.parent.mkdir()
        bad.write_bytes(self.video.read_bytes())
        with self.assertRaises(ValueError): batch.discover(self.root)
        with self.assertRaises(ValueError): batch.infer_label(["Good", "Bad"])
        with self.assertRaises(ValueError): batch.infer_label(["unknown"])

    def test_original_function_and_batch_agree_on_decoded_video(self):
        # Extract only the original function, avoiding its top-level hard-coded run.
        import ast
        source_path = Path(__file__).resolve().parents[1] / "src/analyze_video.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "analyze_video")
        scope = {"cv2": cv2, "np": np}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), "exec"), scope)
        times, scores, brightness = scope["analyze_video"](self.video)
        _, data = batch.analyze(batch.discover(self.video)[0], self.cache)
        np.testing.assert_allclose(times, data[:, 1], atol=1e-12)
        np.testing.assert_allclose(scores, data[:, 2], atol=1e-12)
        np.testing.assert_allclose(brightness, data[:, 3], atol=1e-12)

    def test_incomplete_cache_is_not_accepted(self):
        source = batch.discover(self.video)[0]
        meta, _ = batch.analyze(source, self.cache)
        meta["frames"] += 1
        with self.assertRaises(ValueError): batch.read_scores(self.cache / (source.name + ".csv"), meta)

    def test_cli_creates_reports_and_plots_without_redecoding(self):
        output = self.root / "output"
        self.assertEqual(batch.main(["--input", str(self.video), "--output", str(output), "--flicker"]), 0)
        document = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(document["videos"][0]["frames"], 8)
        self.assertEqual(document["videos"][0]["outside_assumed_flicker"]["frames"], 8)
        self.assertEqual(len(list((output / "plots").glob("*.png"))), 4)
        with patch.object(batch.av, "open", side_effect=AssertionError("decoder must not run")):
            self.assertEqual(batch.main(["--plots-only", "--output", str(output), "--flicker"]), 0)


if __name__ == "__main__":
    unittest.main()
