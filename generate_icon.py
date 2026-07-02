"""Generate icon.ico (for build_exe.py) and favicon.png (for streamlit_app.py)
from the app's own color palette. Run once; re-run after changing the design.

    python generate_icon.py
"""
import os

from PIL import Image, ImageDraw

from regex_core import ACCENT_TEAL, BG_APP

PROJECT_DIR = os.path.dirname(__file__)
SIZE = 1024


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def build_icon() -> Image.Image:
    teal = _hex_to_rgba(ACCENT_TEAL)
    navy = _hex_to_rgba(BG_APP)

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    left, right = 140, SIZE - 140
    top, waist = 90, 480
    draw.rounded_rectangle([left, top, right, waist], radius=160, fill=teal)
    draw.polygon([(left, waist - 140), (right, waist - 140), (SIZE // 2, SIZE - 90)], fill=teal)

    # Bold checkmark — stays legible even downsized to a 16px favicon, unlike fine text glyphs.
    stroke_width = 70
    points = [(300, 470), (460, 630), (740, 300)]
    draw.line(points, fill=navy, width=stroke_width, joint="curve")
    for point in points:
        draw.ellipse(
            [point[0] - stroke_width / 2, point[1] - stroke_width / 2, point[0] + stroke_width / 2, point[1] + stroke_width / 2],
            fill=navy,
        )
    return img


def main() -> None:
    icon = build_icon()

    ico_path = os.path.join(PROJECT_DIR, "icon.ico")
    icon.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {ico_path}")

    favicon_path = os.path.join(PROJECT_DIR, "favicon.png")
    icon.resize((256, 256), Image.LANCZOS).save(favicon_path)
    print(f"Wrote {favicon_path}")


if __name__ == "__main__":
    main()
