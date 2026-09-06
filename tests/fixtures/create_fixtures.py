"""
Script to generate deterministic test fixtures for TRACE E2E Test Suite.
Generates:
- clean_portrait.png & .jpg (single face portrait from genuine face crop)
- multi_face_portrait.png & .jpg (two faces)
- non_face_pattern.png & .jpg (abstract noise/pattern without face)
- tampered_clone.png & .jpg (single-pixel/byte modified clone of clean portrait)
- corrupted_image.bin (corrupt byte sequence)
- metadata_sample.json (RFC 8785 sample metadata)
"""

import os
import json
import numpy as np
import cv2
from PIL import Image

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

def create_fixtures():
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    import insightface
    t1 = insightface.data.get_image("t1")  # shape (886, 1280, 3) BGR

    # 1. Clean single face portrait (400x400)
    # Face 0 in t1 centered around x: 745..847, y: 342..480
    crop_single = t1[260:560, 670:920]
    clean_bgr = cv2.resize(crop_single, (400, 400))
    clean_rgb = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2RGB)
    img_clean = Image.fromarray(clean_rgb)

    clean_png = os.path.join(FIXTURES_DIR, "clean_portrait.png")
    clean_jpg = os.path.join(FIXTURES_DIR, "clean_portrait.jpg")
    img_clean.save(clean_png, format="PNG")
    img_clean.save(clean_jpg, format="JPEG", quality=95)

    # 2. Multi face portrait (2 faces, 500x400)
    crop_face2 = t1[200:460, 20:210]
    f1_resized = cv2.resize(crop_single, (220, 320))
    f2_resized = cv2.resize(crop_face2, (220, 320))

    multi_bgr = np.full((400, 500, 3), 235, dtype=np.uint8)
    multi_bgr[40:360, 20:240] = f1_resized
    multi_bgr[40:360, 260:480] = f2_resized
    multi_rgb = cv2.cvtColor(multi_bgr, cv2.COLOR_BGR2RGB)
    img_multi = Image.fromarray(multi_rgb)

    multi_png = os.path.join(FIXTURES_DIR, "multi_face_portrait.png")
    multi_jpg = os.path.join(FIXTURES_DIR, "multi_face_portrait.jpg")
    img_multi.save(multi_png, format="PNG")
    img_multi.save(multi_jpg, format="JPEG", quality=95)

    # 3. Non-face pattern (abstract geometric noise / tiles, 400x400)
    non_face_bgr = np.zeros((400, 400, 3), dtype=np.uint8)
    for i in range(0, 400, 40):
        for j in range(0, 400, 40):
            color = (40, 180, 200) if (i // 40 + j // 40) % 2 == 0 else (60, 80, 20)
            non_face_bgr[i:i + 38, j:j + 38] = color
    non_face_rgb = cv2.cvtColor(non_face_bgr, cv2.COLOR_BGR2RGB)
    img_non_face = Image.fromarray(non_face_rgb)

    non_face_png = os.path.join(FIXTURES_DIR, "non_face_pattern.png")
    non_face_jpg = os.path.join(FIXTURES_DIR, "non_face_pattern.jpg")
    img_non_face.save(non_face_png, format="PNG")
    img_non_face.save(non_face_jpg, format="JPEG", quality=95)

    # 4. Tampered clone (clean portrait with 1 pixel modified at bottom corner)
    img_tampered = img_clean.copy()
    orig_pixel = img_tampered.getpixel((10, 10))
    new_pixel = ((orig_pixel[0] + 1) % 256, orig_pixel[1], orig_pixel[2])
    img_tampered.putpixel((10, 10), new_pixel)
    tampered_png = os.path.join(FIXTURES_DIR, "tampered_clone.png")
    tampered_jpg = os.path.join(FIXTURES_DIR, "tampered_clone.jpg")
    img_tampered.save(tampered_png, format="PNG")
    img_tampered.save(tampered_jpg, format="JPEG", quality=95)

    # 5. Corrupted image binary
    corrupt_path = os.path.join(FIXTURES_DIR, "corrupted_image.bin")
    with open(corrupt_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01CORRUPTED_TRUNCATED_BINARY_DATA_0xDEADBEEF")

    # 6. Sample canonical metadata JSON
    metadata = {
        "image_sha256": "4a5f6e8d9c1b2a3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e",
        "source_url": "https://goa-archives.example.org/records/1971/portrait_042.jpg",
        "timestamp": 1725562800,
        "title": "Historical Archival Portrait - Goa Freedom Movement"
    }
    meta_path = os.path.join(FIXTURES_DIR, "metadata_sample.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Successfully created synthetic fixtures in:", FIXTURES_DIR)

if __name__ == "__main__":
    create_fixtures()
