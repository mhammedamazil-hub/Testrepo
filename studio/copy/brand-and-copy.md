# LUMENFORGE — brand book & launch copy

## 1. The name

**LUMENFORGE** — *lumen* (light, the thing a screen actually emits) + *forge* (heat, craft, something made by hand).

Why it works:
- Two hard consonants, no ambiguity when spoken on a call.
- **"Forge"** doubles as the studio's verb: a build is *a forge*, the process is *forging*, the team are *forgers*, a delivered slot is *a forge slot*.
- The mark is the letter **L** built from two lit beams — the initial reads at 16 px because it is a single silhouette, and it doubles as a 3D "room corner", i.e. the product.
- Domain: `lumenforge.studio` (`.studio` signals the category; `.com` was not needed for launch).

Rejected names and why: *Volumetric*, *Deepframe*, *Roomlab*, *Solidlight* — all either descriptive (unregistrable), or read as a VR company rather than a website studio.

## 2. Position

> **Websites you can walk through.**

The category is *interactive 3D websites*. The enemy is not other studios; it is the **flat hero image** and the **4 MB background video**.

**One-sentence pitch:** LUMENFORGE models your product in Blender, bakes it with bpy, and ships a Three.js + React site your customer can walk around — under 2 MB, 60 fps on a mid-range phone.

**Three-line pitch:**
1. Your customers can't feel a product through a flat photo.
2. We build the room instead: Blender-authored geometry, Three.js controls, React performance.
3. Fixed price, fixed date, measured load budget. You keep the source.

## 3. Voice

- **Engineer's confidence, artist's restraint.** Short sentences. Numbers instead of adjectives.
- Never say *immersive*, *cutting-edge*, *next-gen*, *revolutionize*, *unleash*, *seamless*.
- Always name the technology when it is the point: **bpy**, **Draco**, **KTX2**, **React Three Fiber**.
- Every claim carries a number: *"1.9 MB first load"*, *"58 fps on a Pixel 6a"*, *"3.1× longer sessions"*.

**Banned words:** immersive, synergy, bespoke (overused), pixel-perfect, world-class, game-changing.

## 4. Taglines (tested pairs)

| Line | Use |
| --- | --- |
| **Websites you can walk through.** | primary |
| **The web was flat. We forged it solid.** | manifesto poster |
| **Not a slide. A site.** | performance ads |
| **Stop showing your product. Open the door.** | commerce campaigns |
| **Beauty that survives a mid-range phone.** | engineering / hiring |
| **Send us your product. We send back a room.** | outbound email subject |

## 5. Naming the offer

Products are *tiers of heat* — Spark → Forge → Foundry. Consistent, memorable, and each one implies the next.

| Tier | Price | Scope | Delivery |
| --- | --- | --- | --- |
| Spark | $4,800 | 1 walkthrough scene, 3 art-directed stills, mobile + WebGL fallback | 2 weeks |
| Forge | $12,500 | Up to 5 rooms/products, bpy asset pipeline, scroll camera, CMS, analytics, launch kit | 3–5 weeks |
| Foundry | $3,900/mo | 2 scenes per sprint, perf monitoring, asset library upkeep | rolling |

**Add-ons:** launch video (from the same scene, +$2,400), 3D ad set (9:16 / 1:1 / 16:9, +$1,200), AR product mode (+$3,000).

## 6. Landing page copy (final, shipped in `site/index.html`)

**Hero**
> Interactive 3D studio · booking Q1
> **Websites you can walk through.**
> We model your product in Blender, bake the geometry with bpy, and ship it as a Three.js + React site that loads under two seconds on a mid-range phone. Not a video. Not a slideshow. A place.

**Stats strip:** first-load budget < 2.0 MB · 60 fps · build 3–5 weeks · Lighthouse 95+

**Work** — *Three rooms, three industries.*
- **Atelier Nova** — 3D commerce. A flagship store where every piece is a real object you can rotate, place and buy. *1.9 MB first load · +38% add-to-cart · bpy asset pipeline*
- **Meridian Towers** — 3D real estate. 48 unit interiors, sun studies computed in Blender, walkable on a phone. *3.1× longer sessions · KTX2 + Draco · sun study in bpy*
- **Kinetic Labs** — product launch. A scroll-driven reveal that turns a spec sheet into a launch moment. *2.4M campaign views · GSAP + R3F · GLTF + Draco*

**Process** — *From blockout to browser in five moves.*
1. **Blockout** — camera path, scale and light direction locked before a single texture exists.
2. **Forge** — bpy scripts build hero assets, bake lightmaps, export GLTF with LODs.
3. **Budget** — Draco + KTX2 compression against a hard load ceiling you approve up front.
4. **Wire** — React Three Fiber scenes, scroll timelines, CMS bindings so marketing can edit copy.
5. **Harden** — mobile GPU tiers, WebGL fallbacks, SEO-safe HTML, Lighthouse gate in CI.

**Pricing** — *Fixed scope. Fixed number.* (tiers above)

**Contact** — *Send us your product. We'll send back a room.* Tell us what you sell and who walks in; you get a fixed price, a camera path and a load budget within 48 hours.

## 7. Launch ads (copy that ships with the artwork)

**Square (1:1) — "Your site. Not a slide."**
> **YOUR SITE.**
> **NOT A SLIDE.**
> A 3D world your customers can explore — built in Blender, shipped in React.
> **BOOK A FORGE SLOT**

**Story (9:16) — "Walk through your site."**
> **WALK / THROUGH / YOUR SITE.**
> Interactive 3D websites. No plugins. Loads in under 2s.
> **SWIPE UP**

**Wide (16:9) — "Take the walkthrough."**
> **TAKE THE WALKTHROUGH**
> Blender-authored. Three.js-powered. React-native performance.
> **LUMENFORGE.STUDIO**

**Search ad (RSA)**
- H1: Interactive 3D Websites · H2: Blender + Three.js Studio · H3: Under 2 MB Load
- D1: We forge walkable 3D sites in Blender and ship them in React. 60 fps on a mid-range phone.
- D2: Fixed price, fixed date, measured load budget. Book a forge slot — reply within 48 hours.

**Cold email (subject: Send us your product. We send back a room.)**
> Hi {first},
> You're selling {product} with photographs. Your customer is trying to judge size, material and finish from a flat image — and guessing wrong at the exact moment they'd add to cart.
> We build the room instead: one Blender scene, one Three.js walkthrough, a hard 2 MB load budget. Three weeks.
> Here's the 30-second sample: lumenforge.studio/showroom
> If it's not for you, tell me and I'll stop.

**LinkedIn post**
> Most "3D websites" are 40 MB showreels that melt a phone.
> We ship 1.9 MB ones at 60 fps. The difference is a bpy asset pipeline, Draco, KTX2 and saying no to a second light.
> New case study: a 3D flagship store with +38% add-to-cart. Link in comments.

**X / Twitter**
> The web was flat. We forged it solid.
> Interactive 3D sites, under 2 MB, built in Blender + Three.js.
> New work ↓

**Hiring post**
> **WE NEED A BLENDER WIZARD.**
> bpy automation · glTF budgets · shader restraint.
> Remote. Paid per build. Portfolio over CV.
> jobs@lumenforge.studio

## 8. Email signatures, bios, meta

- **Signature:** `{name} · LUMENFORGE — interactive 3D studio · lumenforge.studio`
- **IG bio:** `Walk-through websites. Blender → Three.js → React. Under 2 MB. Book a forge slot ↓`
- **Meta description:** LUMENFORGE builds interactive 3D websites with Blender (bpy), Three.js and React — launch-ready 3D commerce, real-estate and product sites that load under 2s.
- **OG title:** LUMENFORGE — Websites you can walk through

## 9. Asset map (what exists in this repo)

| Asset | File |
| --- | --- |
| Logo mark / mono / icon | `brand/logo/*.svg`, `brand/exports/logo-mark-*.png`, `icon-*.png` |
| Wordmark + lockups (light/dark) | `brand/exports/wordmark-2400.png`, `lockup-2400.png`, `lockup-dark-2400.png` |
| Favicons | `brand/exports/favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` |
| Hero key art | `ads/keyart/hero-1600x2000.png` |
| Ad set 1:1 / 9:16 / 16:9 | `ads/set/lumenforge-{square,story,wide}-*.png` |
| Posters (manifesto, case, hiring) | `ads/posters/poster-*.png` |
| Motion ad | `ads/video/lumenforge-ad-720.webm` + `lumenforge-loop-720.gif` + poster |
| Case-study plates | `portfolio/*-1800x1200.png` |
| Pitch deck (11 slides) | `deck/LUMENFORGE-pitch-deck.pptx` |
| Website + showroom | `site/index.html`, `site/showroom.html` |
| Portfolio PDF | `portfolio/LUMENFORGE-portfolio.pdf` |
