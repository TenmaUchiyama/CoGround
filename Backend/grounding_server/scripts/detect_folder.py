"""Run from an environment with coground-server[detect] installed."""
import argparse
import io
import json
import time
from pathlib import Path

from PIL import Image
from coground_server.detection import Detector, save_debug


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    files = sorted(p for p in args.input.iterdir()
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not files:
        parser.error("no JPEG/PNG images in input directory")
    detector = Detector()
    detector.debug_dir = None
    for path in files:
        with Image.open(path) as source:
            image = source.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        data = path.read_bytes() if path.suffix.lower() in {".jpg", ".jpeg"} else buffer.getvalue()
        start = time.perf_counter()
        result = detector.detect(data)
        elapsed = time.perf_counter() - start
        save_debug(args.output / path.name, data, image, result["predictions"])
        print(json.dumps({"file": str(path), "seconds": elapsed, **result}))


if __name__ == "__main__":
    main()
