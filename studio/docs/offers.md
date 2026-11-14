# LUMENFORGE — offer sheet

**What we sell:** an interactive 3D website — a scene your customer can walk around, orbit and configure — built from a real Blender asset pipeline and shipped as a fast React site.

**What it is not:** a background video, a scroll-jacking showreel, a WebGL experiment that melts a phone, or a template with a spinning logo.

---

## Spark — $4,800 · 2 weeks

For a single hero product or one room that has to do the heavy lifting on a landing page.

| | |
| --- | --- |
| Scenes | 1 walkthrough or orbit scene |
| Assets | up to 15 models, cleaned and optimised (LOD + Draco) |
| Art direction | 3 art-directed stills delivered as campaign assets |
| Interaction | orbit + zoom, presets (3 camera bookmarks), mobile drag |
| Performance | first-load ≤ 2.2 MB, 60 fps target on iPhone 12 / Pixel 6a |
| Fallback | static WebP + CSS parallax for no-WebGL devices |
| Handover | source scene, GLTF, React `<Stage>` component, README |

**Good fit if:** you have one product, one launch page, and a hard date.
**Not a fit if:** you need CMS-driven content across 20 products (that's Forge).

---

## Forge — $12,500 · 3–5 weeks *(most booked)*

The flagship build. A full 3D site section or a configurator with marketing control.

| | |
| --- | --- |
| Scenes | up to 5 rooms, products or configurations |
| Assets | full bpy pipeline — procedural variants, baked lightmaps, LOD chain |
| Art direction | full look development: palette, materials, lighting rig, type pairing |
| Interaction | scroll-driven camera, hotspot annotations, configurator states, transitions |
| CMS | copy, hotspots and product data editable without a deploy |
| Performance | first-load ≤ 2.0 MB, ≤ 8 draw calls per frame, Lighthouse 95+ |
| Instrumentation | analytics events for scene entry, interaction depth, configurator completion |
| Launch kit | 3 social stills, 1 vertical loop, OG image, page copy |
| Handover | repo access, source .blend, CI perf gate, 30-day support |

**Good fit if:** the 3D *is* the pitch — commerce flagships, property launches, hardware.
**Upgrade path:** Foundry retainer for the next scenes.

---

## Foundry — $3,900 / month · rolling

For teams shipping scenes continuously, or maintaining a growing 3D catalogue.

- 2 new scenes per sprint (2-week sprint cadence)
- Asset library upkeep: re-exports, LOD refreshes, material updates
- Performance monitoring: weekly load-budget report + regression alerts
- Ad creative refreshed monthly from live scenes (stills + loop)
- Priority queue, 2-business-day response, quarterly look-dev review

**Cancel:** 30 days' notice, all source handed over on exit.

---

## Add-ons

| Add-on | Price | Notes |
| --- | --- | --- |
| Launch video (16:9 + 9:16) | $2,400 | rendered from the shipped scene, no reshoot |
| 3D ad set (9 tiles) | $1,200 | 1:1 / 9:16 / 16:9 crops, caption variants |
| AR product mode | $3,000 | WebXR / model-viewer, iOS Quick Look + Android Scene Viewer |
| Extra scene | $1,850 | same pipeline, same budget ceiling |
| Blender asset pack (client-owned) | $2,600 | rigged .blend + bpy scripts, documented |
| Rush (≤ 5 business days) | +40% | subject to slot availability |

---

## What every engagement includes

1. **A written load budget** signed off before modelling starts (MB, draw calls, fps target device).
2. **Real device testing** — mid-range Android, iPhone 12, desktop, and a no-WebGL fallback path.
3. **A Lighthouse + budget gate in CI**, so the site cannot silently regress after launch.
4. **Source handover** — .blend, bpy scripts, GLTF, React components. No lock-in, no licence fee.
5. **Fixed price and fixed date.** Changes are quoted, not absorbed silently.

## Commercial terms

- 50% on booking, 50% on launch. Foundry billed monthly in advance.
- Two revision rounds included per scene; further rounds at $120/hr.
- Travel and third-party licences (HDRI, fonts, stock models) at cost, pre-approved.
- Payment: bank transfer or card. Net 14. Late payment pauses the sprint.

## Why the price holds

The expensive part of 3D web is not modelling — it is **getting it under 2 MB without looking cheap**. LUMENFORGE owns that pipeline: procedural bpy exports, baked lighting instead of real-time shadows, KTX2 textures, LOD switching, and a hard draw-call ceiling. That's why a Forge build ships in weeks instead of quarters, and why the number doesn't move after kickoff.
