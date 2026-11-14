# KILN — brand book & launch copy

## 1. The name

**KILN** — the chamber where material is fired until it holds. Four letters, one syllable,
no suffix, no "studio" needed.

Why it works:
- It is a **building**, not a metaphor. A kiln is an arch over a fire: the mark is a section
  through one, and every plate in the set is a room with a warm source behind it.
- It gives the studio its verbs without forcing them: a build is **fired**, the client's
  project is **in the kiln**, a rushed job is **unfired**.
- It survives the spoken test — one syllable through a bad phone line — and it is short
  enough to set as a wordmark with real tracking rather than a logotype that has to be drawn.
- Domain: `kiln.studio`. Rejected: *Volumetric*, *Deepframe*, *Roomlab*, *Solidlight*
  (descriptive), *Lumenforge* (two metaphors bolted together, and "forge" is the most
  over-used verb in software branding).

The name replaced **LUMENFORGE** because that name was doing two jobs and neither well:
"lumen" promised lighting design, "forge" promised metalwork, and the product is neither.
KILN promises one thing — a place where something is made and comes out able to hold.

## 2. Position

> **Rooms, not pages.**

The category is *interactive architecture*. The enemy is not other studios; it is the flat
hero image and the four-megabyte background video.

**One-sentence pitch:** KILN models the space in Blender, lights it with bpy, and ships it as
a React site that loads under two megabytes and holds sixty frames on a phone.

**Three-line pitch:**
1. A page is a photograph of a place. Photographs cannot be walked around.
2. We build the room instead: Cycles-lit geometry, Three.js controls, a measured budget.
3. Fixed price, fixed date, source handover.

## 3. Voice

- **Specify. Do not enthuse.** Short sentences. Numbers instead of adjectives.
- Never say *immersive*, *cutting-edge*, *next-gen*, *revolutionize*, *unleash*, *seamless*.
- Always name the technology when it is the point: **bpy**, **Cycles**, **Draco**, **KTX2**,
  **React Three Fiber**.
- Every claim carries a number: *"1.9 MB first load"*, *"60 fps on a Pixel 6a"*,
  *"3.1× longer sessions"*.

**Banned words:** immersive, synergy, bespoke, pixel-perfect, world-class, game-changing.

## 4. Tiers

| Tier | Price | What it is |
| --- | --- | --- |
| **Spar** | $4,800 | One scene, three stills, two weeks. The test. |
| **Kiln** | $12,500 | Up to five rooms, bpy pipeline, launch kit, three to five weeks. |
| **Firing** | $3,900 / mo | Two scenes per sprint, monitoring, monthly creative. |

The names are the process, in order: a spar is the small fire you start with, the kiln is
where the work is fired, firing is the ongoing cycle.

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
> **KILN.STUDIO**

**Search ad (RSA)**
- H1: Interactive 3D Websites · H2: Blender + Three.js Studio · H3: Under 2 MB Load
- D1: We forge walkable 3D sites in Blender and ship them in React. 60 fps on a mid-range phone.
- D2: Fixed price, fixed date, measured load budget. Book a forge slot — reply within 48 hours.

**Cold email (subject: Send us your product. We send back a room.)**
> Hi {first},
> You're selling {product} with photographs. Your customer is trying to judge size, material and finish from a flat image — and guessing wrong at the exact moment they'd add to cart.
> We build the room instead: one Blender scene, one Three.js walkthrough, a hard 2 MB load budget. Three weeks.
> Here's the 30-second sample: kiln.studio/showroom
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
> jobs@kiln.studio

## 8. Email signatures, bios, meta

- **Signature:** `{name} · KILN — interactive 3D studio · kiln.studio`
- **IG bio:** `Walk-through websites. Blender → Three.js → React. Under 2 MB. Book a forge slot ↓`
- **Meta description:** KILN builds interactive 3D websites with Blender (bpy), Three.js and React — launch-ready 3D commerce, real-estate and product sites that load under 2s.
- **OG title:** KILN — Websites you can walk through

## 9. Asset map (what exists in this repo)

| Asset | File |
| --- | --- |
| Mark (ink / paper / ember) | `brand/logo/kiln-mark.svg`, `kiln-mark-paper.svg`, `kiln-mark-ember.svg` |
| Mark, raster | `brand/exports/mark-1024.png`, `mark-512.png`, `mark-mono-512.png` |
| Wordmark | `brand/logo/kiln-wordmark.svg`, `brand/exports/wordmark-2400.png` |
| Lockups (ink / paper) | `brand/logo/kiln-lockup.svg`, `kiln-lockup-ink.svg` |
| Construction sheet | `brand/logo/kiln-construction.svg` / `.png` |
| Favicons | `brand/exports/favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` |
| Cycles plates | `brand/renders/hero-2400x1600.png`, `keyart-1600x2000.png`, `square-1600x1600.png`, `detail-2400x1350.png` |
| Case plates | `brand/renders/work-{atelier,meridian,kinetic}.png` |
| Posters | `ads/posters/kiln-manifesto-1200x1600.png`, `kiln-hiring-1200x1600.png` |
| Ad set 1:1 / 4:5 / 16:9 | `ads/set/kiln-{square,story,wide}-*.png` |
| Identity film | `ads/video/kiln-sting-1080.mp4` / `.webm`, `kiln-sting-poster.png`, `kiln-loop-720.gif` |
| Portfolio (9 pp) | `portfolio/KILN-portfolio.pdf` |
| Pitch deck (12 slides) | `deck/KILN-pitch-deck.pptx` |
| One-pager | `docs/KILN-one-pager.pdf` |
| Website + showroom | `site/index.html`, `site/showroom.html` |
