"""Local GPU wrapper around the official TencentARC/InstantMesh code.

Why this exists: the official ``run.py`` CLI writes **only OBJ** (vertex colours).
The official Gradio demo also writes GLB via ``src.utils.mesh_util.save_glb``.
This script reproduces the official demo's inference path so we get both formats,
without modifying upstream code.

Run it with the InstantMesh repo as the working directory:

    cd InstantMesh
    python /path/to/instantmesh_generate.py \
        --config configs/instant-mesh-large.yaml \
        --image /path/to/input.png \
        --out /tmp/jobdir \
        --seed 42 --steps 75

Progress is emitted on stdout as ``STAGE:<stage>:<percent>:<message>`` so the app
can show real progress instead of a spinner.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def emit(stage: str, pct: int, message: str) -> None:
    print(f"STAGE:{stage}:{pct}:{message}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/instant-mesh-large.yaml")
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=75)
    parser.add_argument("--no-rembg", action="store_true")
    parser.add_argument("--export-texmap", action="store_true")
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()

    import numpy as np
    import torch
    from einops import rearrange
    from omegaconf import OmegaConf
    from PIL import Image
    from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler
    from huggingface_hub import hf_hub_download
    from pytorch_lightning import seed_everything
    from torchvision.transforms import v2

    from src.utils.camera_util import (
        FOV_to_intrinsics,
        get_circular_camera_poses,
        get_zero123plus_input_cameras,
    )
    from src.utils.infer_util import remove_background, resize_foreground, save_video
    from src.utils.mesh_util import save_glb, save_obj
    from src.utils.train_util import instantiate_from_config

    # NOTE: get_render_cameras lives in the official app.py/run.py, not in
    # src.utils.camera_util. Copied verbatim from run.py (Apache-2.0).
    def get_render_cameras(batch_size=1, M=120, radius=4.0, elevation=20.0, is_flexicubes=False):
        c2ws = get_circular_camera_poses(M=M, radius=radius, elevation=elevation)
        if is_flexicubes:
            cameras = torch.linalg.inv(c2ws)
            return cameras.unsqueeze(0).repeat(batch_size, 1, 1, 1)
        extrinsics = c2ws.flatten(-2)
        intrinsics = FOV_to_intrinsics(30.0).unsqueeze(0).repeat(M, 1, 1).float().flatten(-2)
        cameras = torch.cat([extrinsics, intrinsics], dim=-1)
        return cameras.unsqueeze(0).repeat(batch_size, 1, 1)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    seed_everything(args.seed)
    config = OmegaConf.load(args.config)
    config_name = os.path.basename(args.config).replace(".yaml", "")
    is_flexicubes = config_name.startswith("instant-mesh")
    device = torch.device("cuda")
    if not torch.cuda.is_available():
        print("ERROR: no CUDA device. The official code hard-codes CUDA.", file=sys.stderr)
        return 2

    emit("load", 10, "Loading Zero123++ pipeline")
    pipeline = DiffusionPipeline.from_pretrained(
        "sudo-ai/zero123plus-v1.2", custom_pipeline="zero123plus", torch_dtype=torch.float16
    )
    pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(
        pipeline.scheduler.config, timestep_spacing="trailing"
    )
    unet_path = hf_hub_download(repo_id="TencentARC/InstantMesh", filename="diffusion_pytorch_model.bin", repo_type="model")
    pipeline.unet.load_state_dict(torch.load(unet_path, map_location="cpu"), strict=True)
    pipeline = pipeline.to(device)

    emit("load", 25, "Loading InstantMesh reconstruction model")
    model = instantiate_from_config(config.model_config)
    ckpt = hf_hub_download(repo_id="TencentARC/InstantMesh", filename=f"{config_name.replace('-', '_')}.ckpt", repo_type="model")
    state = {k[14:]: v for k, v in torch.load(ckpt, map_location="cpu")["state_dict"].items() if k.startswith("lrm_generator.")}
    model.load_state_dict(state, strict=True)
    model = model.to(device)
    if is_flexicubes:
        model.init_flexicubes_geometry(device, fovy=30.0)
    model = model.eval()

    emit("preprocess", 35, "Preparing input image")
    image = Image.open(args.image)
    if not args.no_rembg:
        import rembg

        image = remove_background(image, rembg.new_session())
        image = resize_foreground(image, 0.85)

    emit("multiview", 45, f"Sampling {args.steps} steps with Zero123++ (seed {args.seed})")
    mv = pipeline(image, num_inference_steps=args.steps).images[0]
    mv_path = out_dir / "multiview.png"
    mv.save(mv_path)

    images = np.asarray(mv, dtype=np.float32) / 255.0
    images = torch.from_numpy(images).permute(2, 0, 1).contiguous().float()
    images = rearrange(images, "c (n h) (m w) -> (n m) c h w", n=3, m=2)
    images = v2.functional.resize(images.unsqueeze(0).to(device), 320, interpolation=3, antialias=True).clamp(0, 1)

    # Free the diffusion pipeline before the reconstruction to be VRAM-friendly.
    del pipeline
    torch.cuda.empty_cache()

    input_cameras = get_zero123plus_input_cameras(batch_size=1, radius=4.0).to(device)
    with torch.no_grad():
        emit("reconstruct", 65, "Encoding triplanes")
        planes = model.forward_planes(images, input_cameras)

        emit("extract", 80, "Extracting mesh (FlexiCubes)")
        mesh_out = model.extract_mesh(planes, use_texture_map=args.export_texmap, **config.infer_config)

        glb_path = out_dir / "mesh.glb"
        obj_path = out_dir / "mesh.obj"
        if args.export_texmap:
            from src.utils.mesh_util import save_obj_with_mtl

            vertices, faces, uvs, mesh_tex_idx, tex_map = mesh_out
            save_obj_with_mtl(
                vertices.data.cpu().numpy(),
                uvs.data.cpu().numpy(),
                faces.data.cpu().numpy(),
                mesh_tex_idx.data.cpu().numpy(),
                tex_map.permute(1, 2, 0).data.cpu().numpy(),
                str(obj_path),
            )
            print("NOTE: texture-mapped export writes OBJ+MTL+PNG; no GLB in this mode", flush=True)
            glb_path = None
        else:
            vertices, faces, vertex_colors = mesh_out
            vertices = vertices[:, [1, 2, 0]]
            save_glb(vertices, faces, vertex_colors, str(glb_path))
            save_obj(vertices, faces, vertex_colors, str(obj_path))

        video_path = None
        if not args.no_video:
            emit("render", 90, "Rendering turntable video")
            cams = get_render_cameras(batch_size=1, M=120, radius=4.5, elevation=20.0, is_flexicubes=is_flexicubes).to(device)
            frames = []
            chunk = 20 if is_flexicubes else 1
            for i in range(0, cams.shape[1], chunk):
                if is_flexicubes:
                    frame = model.forward_geometry(planes, cams[:, i:i + chunk], render_size=384)["img"]
                else:
                    frame = model.synthesizer(planes, cameras=cams[:, i:i + chunk], render_size=384)["images_rgb"]
                frames.append(frame)
            frames = torch.cat(frames, dim=1)[0]
            video_path = out_dir / "turntable.mp4"
            save_video(frames, str(video_path), fps=30)

    manifest = {
        "glb_path": str(glb_path) if glb_path else None,
        "obj_path": str(obj_path),
        "multiview_path": str(mv_path),
        "video_path": str(video_path) if video_path else None,
        "metadata": {
            "config": config_name,
            "seed": args.seed,
            "steps": args.steps,
            "texture_map": bool(args.export_texmap),
            "gpu": torch.cuda.get_device_name(0),
            "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2),
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    emit("done", 100, "Mesh exported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
