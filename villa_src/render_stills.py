"""Render the hero stills to villa/renders/."""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from villa_src import cameras as C, scene as S  # noqa: E402

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "villa", "renders"))


def main(res=(1280, 720), samples=32):
    os.makedirs(OUT, exist_ok=True)
    sc, colls = S.build()
    sc.cycles.max_bounces = 5
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 5
    sc.cycles.adaptive_threshold = 0.02
    total = 0.0
    for name, (loc, tgt, lens) in C.SHOTS.items():
        cam = S.camera("cam_" + name, loc, tgt, lens=lens)
        path = os.path.join(OUT, f"{name}.png")
        dt = S.render(sc, cam, path, res=res, samples=samples)
        total += dt
        print(f"RENDER {name} {dt:.0f}s -> {path}", flush=True)
    print(f"DONE stills {total/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
