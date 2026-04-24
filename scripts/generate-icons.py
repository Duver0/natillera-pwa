"""
Generate PWA placeholder icons for Natillera PWA.
Run once: python scripts/generate-icons.py
Requires: pip install Pillow
Output: frontend/public/icons/icon-192.png, icon-512.png
"""
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "icons"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFont

    def make_icon(size: int, path: Path) -> None:
        img = Image.new("RGB", (size, size), color=(37, 99, 235))  # #2563eb
        draw = ImageDraw.Draw(img)
        font_size = size // 2
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        text = "N"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) // 2 - bbox[0]
        y = (size - text_h) // 2 - bbox[1]
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        img.save(path, "PNG")
        print(f"Generated: {path}")

    make_icon(192, OUTPUT_DIR / "icon-192.png")
    make_icon(512, OUTPUT_DIR / "icon-512.png")
    print("Icons generated successfully.")

except ImportError:
    # Fallback: generate minimal valid PNG using struct + zlib
    import struct
    import zlib

    def make_minimal_png(size: int, path: Path) -> None:
        """Generate a solid blue PNG without Pillow."""
        width = height = size
        # Blue pixel RGB
        r, g, b = 37, 99, 235

        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            c = chunk_type + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

        # IHDR
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        ihdr = png_chunk(b"IHDR", ihdr_data)

        # IDAT: raw pixels
        raw_rows = []
        for _ in range(height):
            row = b"\x00" + bytes([r, g, b] * width)
            raw_rows.append(row)
        idat = png_chunk(b"IDAT", zlib.compress(b"".join(raw_rows)))

        iend = png_chunk(b"IEND", b"")

        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend)
        print(f"Generated (no-Pillow): {path}")

    make_minimal_png(192, OUTPUT_DIR / "icon-192.png")
    make_minimal_png(512, OUTPUT_DIR / "icon-512.png")
    print("Icons generated successfully (minimal PNG, no Pillow).")
