---
title: InstantMesh API
emoji: 🧊
colorFrom: indigo
colorTo: green
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: false
license: apache-2.0
---

# InstantMesh — self-hosted ZeroGPU Space

One stable endpoint (`/generate`) that turns an image into OBJ + GLB, built on the official
[TencentARC/InstantMesh](https://github.com/TencentARC/InstantMesh) code.

## Why this exists

The upstream Space `TencentARC/InstantMesh` exposes `/make3d` **without parameters** — it relies on a
server-side `gr.State` passed from `/generate_mvs`. Great for the upstream UI, fragile for programmatic
clients. This Space takes the image and returns both meshes in a single call.

## Deploy (free tier)

Free personal accounts in good standing (verified email, account > 30 days old) can host **2 Gradio
Spaces on ZeroGPU**. GPU quota is **5 GPU-minutes/day** on a free account (2 min unauthenticated
visitors), resetting 24 h after first use. A run here is ~10–30 s of GPU time.

```bash
# 1. create a Gradio Space with ZeroGPU hardware on huggingface.co/new-space
git clone https://huggingface.co/spaces/<you>/<space>
cd <space>
git clone --depth 1 https://github.com/TencentARC/InstantMesh /tmp/im
cp -r /tmp/im/src /tmp/im/zero123plus /tmp/im/configs .
cp /path/to/this/repo/space/app.py .
# 2. weights: fetch into ./ckpts (see README in the audit repo)
python -c "
from huggingface_hub import hf_hub_download as d
import shutil, os; os.makedirs('ckpts', exist_ok=True)
for f in ['instant_mesh_large.ckpt','instant_mesh_base.ckpt','diffusion_pytorch_model.bin']:
    shutil.copy(d('TencentARC/InstantMesh', f, repo_type='model'), 'ckpts/'+f)
"
# 3. requirements: same as upstream requirements.txt, minus docker-only bits
git add -A && git commit -m "InstantMesh API space" && git push
```

## Calling it from the app

Set on the app server:

```bash
IM_PROVIDER=hf_space
HF_SPACE_ID=<you>/<space>
HF_TOKEN=hf_...   # optional, uses your daily ZeroGPU quota instead of the anonymous pool
```

## Honest limits

* ZeroGPU is time-sliced: expect queueing, and 5 GPU-min/day is roughly 10–20 generations **per account**.
* No persistent disk: weights are re-downloaded after a restart unless you use Hub storage.
* This wrapper skips the turntable render and texture-map export to keep GPU seconds low.
