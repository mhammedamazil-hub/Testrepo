# LUMENFORGE — 90-day launch plan

The studio is a three-part machine: **one flagship demo** (the showroom) → **one repeatable offer** (Forge, $12,500) → **one recurring product** (Foundry, $3,900/mo). Everything in this repo exists to make those three things feel inevitable.

---

## Week 0 — assets are done, ship them

| Action | Artefact |
| --- | --- |
| Deploy `studio/site` to Vercel/Netlify/Cloudflare Pages (static, no build step) | `site/` |
| Point `lumenforge.studio` at it, verify OG card renders | `site/assets/og-1200x630.jpg` |
| Create the profiles with the avatar + banner | `ads/avatars/*` |
| Publish the 7-post launch sequence | `copy/social-kit.md` |
| Send the one-pager to 25 warm contacts | `docs/one-pager.md`, `portfolio/LUMENFORGE-portfolio.pdf` |
| Post the 6-second ad organically (Reels + LinkedIn + X) | `ads/video/lumenforge-ad-1080.mp4` |

**Gate:** site live, all four socials consistent, one demo link you can send without explaining anything.

---

## Weeks 1–4 — prove the demo converts

**Goal: 40 outbound, 12 replies, 6 calls, 2 paid projects.**

- **Outbound list:** 120 companies that sell objects people need to *size up* — ceramics, furniture, lighting, hardware, jewellery, property developers, boutique hotels. Find them on Instagram; the ones with beautiful photography and no interactivity are the leads.
- **The hook** is always the same: their product, in their colours, in a 20-second walkthrough. Do it as a *spec build*, not a proposal — one scene, one camera path, from their existing photos.
- **Never send a deck first.** Send the link to `showroom.html` plus one line about their product.
- **Qualify on budget in the first call.** "Forge starts at twelve-five. Is that in range, or should we look at Spark?" Saves weeks.
- **Publish weekly**: one case study carousel, one engineering post (load budgets), one studio post.

**Gate:** 2 signed projects. If not, the offer is wrong, not the market — test a "Spark for $3,900, first three clients" version before touching the price of Forge.

---

## Weeks 5–8 — deliver, film everything

Every build is also a marketing asset. On each project, capture:

1. **The blockout** (grey boxes, camera path) — best "how it's made" content you will ever get.
2. **The first real-time frame** on a mid-range phone, screen-recorded with the fps counter visible.
3. **A 15-second vertical cut** from the scene for the client's own channels (included in Forge — it makes you indispensable).
4. **A before/after** of their old hero image vs the room.
5. **A number**: add-to-cart, time-on-page, configurator completions. Ask for it at the 30-day check-in; it becomes the next proposal's first line.

**Gate:** 2 case studies with a real number each, 2 referrals asked for explicitly.

---

## Weeks 9–12 — convert projects into retainers

The Foundry pitch is not "more work", it is **"your 3D catalogue is now an asset that decays"**: new SKUs, seasonal materials, performance drift, ad creative going stale.

- At handover, present a 1-page **asset health report**: current load, draw calls, fps on three devices, and what a monthly refresh would include.
- Offer the first month at $2,900 as a pilot, then $3,900.
- Target: **2 of the first 4 clients on retainer by day 90.**

---

## Content engine (runs forever, 3 posts/week)

| Slot | Format | Source |
| --- | --- | --- |
| Monday | Engineering post (numbers, budgets, technique) | `docs/offers.md` + project learnings |
| Wednesday | Case study or client clip | `portfolio/plates/*`, client cut |
| Friday | Studio / hiring / manifesto | `ads/posters/*` |

Reuse rules: every post gets the lockup and the URL. Every carousel starts with the number, not the adjective. Every video is captioned — 85% of feed views are muted.

---

## Numbers to watch weekly

| Metric | Target by day 90 |
| --- | --- |
| Site → showroom click-through | > 25% |
| Showroom → contact (email/form) | > 8% |
| Outbound reply rate | > 20% |
| Call → proposal | > 60% |
| Proposal → close | > 30% |
| Avg. project value | > $9,000 |
| Retainer MRR | > $7,800 |

If showroom engagement is high but contact rate is low, the offer section is the problem. If reply rate is low, the outbound list is the problem. If close rate is low, qualification is the problem.

---

## The first hire

Not a generalist — a **Blender/bpy operator** who can take plate #4 of a scene from a blockout and return a budget-compliant GLTF. Paid per build, not per hour, so the margin on build 2+ stays intact. Hire at 3 concurrent projects, funded by the third deposit, not by savings.

## What not to do

- Do not add a fourth tier. Three prices, one recommendation.
- Do not sell "3D" — sell the walkthrough, the conversion number, the launch moment.
- Do not take a project under $4,800, even "for the portfolio". Discounting the entry tier destroys the ladder.
- Do not promise WebVR/AR before you have shipped the plain web version — `model-viewer` and WebXR are a $3,000 add-on with its own QA burden.
