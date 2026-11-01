# RUN THIS — real InstantMesh inference, free, 3 clicks

Goal: your BMW M5 photo → genuine InstantMesh mesh → GLB you can hand back for verification.

**Cost: $0.** Google Colab free tier (T4 GPU). No card, no credits, no paid API.

---

## Before you start

* You need a Google account. That's it.
* The sandbox you're reading this in **cannot** do this run: no GPU, and it is firewalled off from
  Google/Hugging Face/Replicate. That is why the run happens on Colab.
* The notebook fetches the BMW M5 photo **by itself** (Wikimedia, CC BY-SA 2.0, auto-attributed).
  You do not need to upload anything.

## The run

**1.** Open <https://colab.research.google.com> → `File` → `Upload notebook` → choose
`notebooks/instantmesh_real_validation.ipynb` from this repo.
*(Alternative: `File` → `Open notebook` → `GitHub` tab → paste this repo's URL → pick the file.)*

**2.** Menu `Runtime` → `Change runtime type` → **Hardware accelerator: T4 GPU** → `Save`.

**3.** Menu `Runtime` → **`Run all`**. Then leave it alone.

### What you will see, in order

| Cell | What happens | Time |
|---|---|---|
| 1 | Prints GPU name + VRAM. **Stops immediately if there's no GPU** (with instructions). | 5 s |
| 2 | Installs torch 2.1 + xformers + requirements. `nvdiffrast` compiles from source — looks frozen for 5–10 min. Normal. | 8–15 min |
| 3 | Downloads ~7.3 GB of weights. | 3–8 min |
| 4 | Fetches the BMW M5 photo, prints its SHA-256, shows it. | 5 s |
| 5 | **The inference.** Tries textured → base → vertex-colour, printing which succeeded. | 2–15 min |
| 6 | Converts to GLB, validates it, prints vertex/triangle/texture info. | ~1 min |
| 7 | Prints a metrics block and downloads `instantmesh_real_glb.zip`. | 10 s |

### If Colab says "GPU not available"
Free tier is oversubscribed at peak times. Wait 15–30 min and try again, or use **Kaggle** instead:
<https://kaggle.com/code> → New Notebook → `Settings` → `Accelerator: GPU T4 x2` (30 GPU-h/week free).
Two edits needed there: cell 4's photo fetch works unchanged, but replace the `from google.colab import files`
block in cell 7 with `shutil.copy(zip_path, "/kaggle/working/")`.

### If cell 5 fails entirely
It prints the tail of the error for each of its three attempts. Copy that text into the chat — do not
change settings blindly.

### If the mesh looks bad
Cars are hard-mode for a 2024 single-image model. Re-run **only cell 5** with a different seed by editing
`--seed 42` to `--seed 7`. The 6-view grid PNG in `outputs/<config>/images/` shows you *why*: if the views
are wrong, the mesh will be wrong.

## What to send back

The notebook downloads **`instantmesh_real_glb.zip`**. Attach that file to this chat. It contains:

```
input.jpg                 the exact photo used (provenance)
metrics.json              GPU, peak VRAM, timings, hashes, which attempt won
mesh/mesh.glb             ← the deliverable
mesh/mesh.obj             (+ .mtl + texture .png on the textured path)
mesh/<6-view>.png         the generated views
```

If the zip is too big to attach, `mesh/mesh.glb` alone is enough for verification — `metrics.json` is what
makes the report complete, so attach both if you can.

## What I do when it arrives

1. `tools/verify_mesh.py inspect` — parse the GLB byte-by-byte, check every bufferView pointer, count
   geometry, detect `TEXCOORD_0` + texture vs. `COLOR_0` vertex colours.
2. `tools/verify_mesh.py render` — software-render 6 turntable frames to PNG **inside this sandbox** and
   put them in front of you. That is the "opens in a 3D viewer" evidence: an independent renderer, not the
   notebook's own preview.
3. `POST /api/import` — load it into the app so you can orbit it at `http://localhost:8000` and download
   GLB/OBJ from it (stamped `origin=external_import`, never reported as inference by this server).
4. A written report: generation time, GPU, peak VRAM, output size, texture presence, and quality issues
   specific to your image.

## Honesty note

Nothing in this repo has claimed a real generated asset yet. The `mock` provider's cube is watermarked
`SIMULATED_NOT_AI` everywhere. Your Colab run is the first real inference in this project, and it happens
on your side because it physically cannot happen here.
