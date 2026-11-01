"""Self-hosted ZeroGPU Space: official InstantMesh pipeline with a clean 2-endpoint API.

Deploy this as your own Gradio Space (ZeroGPU hardware) when you want an endpoint that
your app can call without depending on the upstream demo's internals.

Why build our own Space instead of calling TencentARC/InstantMesh directly?
  * The upstream Space exposes `/make3d()` with **no parameters**; it relies on a
    server-side `gr.State` holding the multi-view image. That works only for a client
    that keeps one Gradio session alive, and it can break without notice.
  * Here `/generate` takes the image and returns OBJ + GLB in a single call — a stable
    contract for programmatic use.

ZeroGPU rules this code respects:
  * No GPU work at import time (models are loaded to CPU, moved in/out per call).
  * The whole GPU section is inside `@spaces.GPU(duration=...)`; VRAM is released on return.
"""
from __future__ import annotations

import os
import tempfile

import gradio as gr
import numpy as np
import spaces
import torch
from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler
from einops import rearrange
from omegaconf import OmegaConf
from PIL import Image
from torchvision.transforms import v2

from src.utils.camera_util import get_zero123plus_input_cameras
from src.utils.infer_util import remove_background, resize_foreground
from src.utils.mesh_util import save_glb, save_obj
from src.utils.train_util import instantiate_from_config

CONFIG_PATH = os.environ.get("IM_CONFIG", "configs/instant-mesh-large.yaml")
GPU_SECONDS = int(os.environ.get("IM_GPU_SECONDS", "120"))

config = OmegaConf.load(CONFIG_PATH)
config_name = os.path.basename(CONFIG_PATH).replace(".yaml", "")
IS_FLEXICUBES = config_name.startswith("instant-mesh")

print("Loading Zero123++ (CPU)…")
pipe = DiffusionPipeline.from_pretrained(
    "sudo-ai/zero123plus-v1.2", custom_pipeline="zero123plus", torch_dtype=torch.float16
)
pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")

print("Loading reconstruction model (CPU)…")
model = instantiate_from_config(config.model_config)
state = {k[14:]: v for k, v in torch.load(
    f"ckpts/{config_name.replace('-', '_')}.ckpt", map_location="cpu", weights_only=False
)["state_dict"].items() if k.startswith("lrm_generator.")}
model.load_state_dict(state, strict=True)
model = model.eval()


@spaces.GPU(duration=GPU_SECONDS)
def generate(image: Image.Image, steps: int = 75, seed: int = 42, remove_bg: bool = True):
    """image -> (glb_path, obj_path, multiview_png_path). Real inference."""
    from pytorch_lightning import seed_everything

    seed_everything(int(seed))
    device = torch.device("cuda")

    if remove_bg:
        image = resize_foreground(remove_background(image.convert("RGBA")), 0.85)

    pipe.to(device)
    mv = pipe(image, num_inference_steps=int(steps)).images[0]
    pipe.to("cpu")
    torch.cuda.empty_cache()

    arr = np.asarray(mv, dtype=np.float32) / 255.0
    imgs = rearrange(torch.from_numpy(arr).permute(2, 0, 1).contiguous().float(), "c (n h) (m w) -> (n m) c h w", n=3, m=2)
    imgs = v2.functional.resize(imgs.unsqueeze(0).to(device), 320, interpolation=3, antialias=True).clamp(0, 1)

    model.to(device)
    if IS_FLEXICUBES:
        model.init_flexicubes_geometry(device, fovy=30.0)

    cams = get_zero123plus_input_cameras(batch_size=1, radius=4.0).to(device)
    with torch.no_grad():
        planes = model.forward_planes(imgs, cams)
        vertices, faces, vertex_colors = model.extract_mesh(planes, use_texture_map=False, **config.infer_config)

    vertices = vertices[:, [1, 2, 0]]
    outdir = tempfile.mkdtemp()
    glb_path = os.path.join(outdir, "mesh.glb")
    obj_path = os.path.join(outdir, "mesh.obj")
    mv_path = os.path.join(outdir, "multiview.png")
    save_glb(vertices, faces, vertex_colors, glb_path)
    save_obj(vertices, faces, vertex_colors, obj_path)
    mv.save(mv_path)

    model.to("cpu")
    torch.cuda.empty_cache()
    return glb_path, obj_path, mv_path


with gr.Blocks(title="InstantMesh API") as demo:
    gr.Markdown("## InstantMesh — self-hosted API\n`/generate` returns OBJ + GLB in one call.")
    with gr.Row():
        inp = gr.Image(type="pil", image_mode="RGBA", label="Input image")
        with gr.Column():
            steps = gr.Slider(30, 75, value=75, step=5, label="Sample steps")
            seed = gr.Number(value=42, precision=0, label="Seed")
            remove_bg = gr.Checkbox(value=True, label="Remove background")
    btn = gr.Button("Generate", variant="primary")
    with gr.Row():
        out_glb = gr.Model3D(label="GLB")
        out_obj = gr.Model3D(label="OBJ")
    out_mv = gr.Image(label="Multi-view")
    btn.click(generate, [inp, steps, seed, remove_bg], [out_glb, out_obj, out_mv], api_name="generate")

demo.queue(max_size=8)
demo.launch()
