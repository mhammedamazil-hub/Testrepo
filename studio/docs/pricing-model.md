# KILN — pricing model & unit economics

The public price list is in `offers.md`. This file is the internal one: what a build actually costs, where the margin is, and which decisions protect it.

## 1. Rate card (internal)

| Resource | Cost | Basis |
| --- | --- | --- |
| Creative director / founder | $0 booked, $110/hr opportunity | 20% of a Forge build |
| 3D generalist (contract) | $65/hr | 40–55 hrs per Forge build |
| Web engineer (contract) | $70/hr | 40–50 hrs per Forge build |
| Motion / edit | $55/hr | 8–14 hrs (launch kit) |
| Blender render time | ~$0.35/render-hour (spot) | 6–20 hrs per build |
| Asset licences | $150–400/build | HDRI, type, stock |
| Tools | ~$120/mo | Blender (free), R2, Vercel, monitoring |

## 2. Cost of a Forge build ($12,500)

| Line | Hours | Cost |
| --- | --- | --- |
| Look dev + blockout (CD) | 22 | $2,420 |
| Asset production / bpy (3D) | 48 | $3,120 |
| Web build (eng) | 46 | $3,220 |
| Motion launch kit | 10 | $550 |
| QA, device pass, CI gate | 12 | $770 |
| Licences + render | — | $420 |
| **Total direct** | 138 | **$10,500** |

→ **Gross margin ≈ 16%** on a first Forge build, rising to **~48%** on builds 3+ once the component library, bpy exporter and QA checklist are reused (direct cost drops to ~$6,500).

**This is the whole strategy:** the first build pays for the pipeline; every subsequent build is a component assembly. Which is why Foundry exists — retainers are where the margin lives.

## 3. Spark ($4,800)

| Line | Hours | Cost |
| --- | --- | --- |
| Look dev + blockout | 10 | $1,100 |
| Asset production | 20 | $1,300 |
| Web build | 18 | $1,260 |
| QA + deploy | 6 | $385 |
| Licences + render | — | $180 |
| **Total** | 54 | **$4,225** |

→ **~12% margin.** Spark is a *lead product*: its job is to get a scene into the client's hands and convert to Forge within 60 days. Target conversion: 40%.

## 4. Foundry ($3,900/mo)

| Line | Cost |
| --- | --- |
| 2 scenes/sprint (reused pipeline) | $2,100 |
| Monitoring + reporting | $260 |
| Ad refresh | $320 |
| Support reserve | $180 |
| **Direct** | **$2,860** |

→ **~27% margin, near-zero sales cost, 12-month average retention = $46,800 LTV.** This is the business; the projects are the funnel.

## 5. Required volume

Break-even (solo + one contractor, $9,500/mo fixed):

- 1 Forge build + 1 Spark per month → $17,300 revenue, ~$2,700–3,000 gross
- or **4 Foundry clients** → $15,600/mo, ~$4,100 gross, no bidding

Target mix at month 12: **5 Foundry + 1 Forge + 1 Spark per quarter** ≈ $33k/mo revenue, ~$13k gross.

## 6. Sales mechanics

| Stage | Target | Asset used |
| --- | --- | --- |
| Inbound / outbound | 40 conversations/mo | `copy/brand-and-copy.md` cold email |
| Qualified | 12/mo | 48-hour fixed quote (price + camera path + load budget) |
| Proposal | 6/mo | `deck/KILN-pitch-deck.pptx`, `portfolio/KILN-portfolio.pdf` |
| Won | 1–2/mo | Forge or Spark, with an upgrade clause |

- **No discovery invoice.** The quote is the discovery: we specify a camera path and a load budget from their existing product photos.
- **Always quote two tiers.** Spark as the entry, Forge as the recommendation. Foundry only after a project.
- **Show the showroom, not the deck.** `site/showroom.html` closes more calls than any slide.

## 7. Where the risk sits

| Risk | Mitigation |
| --- | --- |
| Scope creep in scene count | Scenes are counted in the SOW; extra scene = $1,850, quoted before work |
| Client supplies unoptimised CAD | Asset prep is a line item after 15 models |
| Performance regression after handover | CI budget gate + Foundry monitoring |
| Key-person dependency | bpy scripts + component library documented; contractor can build scene #4+ |
| 3D freelancer pricing drift | Fixed hourly contracts, 3-scene minimum batches |
