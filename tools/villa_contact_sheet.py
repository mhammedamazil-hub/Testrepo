"""Build a contact sheet of the villa stills."""
import os

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
R = os.path.join(ROOT, "villa", "renders")


def main(cols=3, tile_w=640):
    files = sorted(f for f in os.listdir(R)
                   if f.endswith(".png") and not f.startswith("contact_sheet"))
    if not files:
        raise SystemExit("no renders")
    ims = [Image.open(os.path.join(R, f)) for f in files]
    ar = ims[0].height / ims[0].width
    tw, th = tile_w, int(tile_w * ar)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (24, 24, 24))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((i % cols) * tw, (i // cols) * th))
    out = os.path.join(R, "contact_sheet.png")
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
