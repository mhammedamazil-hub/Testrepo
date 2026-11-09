# Short hops, circuit art and unchanged-preset performance (v0.5)

## Correcting the previous flight mode

The previous v0.4 implementation maintained a height target with continuous lift, and regenerated boost while airborne. That was an unlimited hover mode, not a finite cold-gas hop. It has been replaced, not merely renamed.

### Official source and what it does NOT establish

Consulted on 2026-11-05: [1](https://www.tesla.com/roadster), Tesla's official Roadster page. Its indexed primary-source copy describes “cold-gas thrusters”, all-electric actuators making rapid adjustments to stabilize flight, and perimeter thrusters supporting forward/upward acceleration and rotational movement for the Rocket augment. The official page's crawler-readable body was incomplete in this environment; the official-page search extraction supplied the thruster copy. The readable footnote states the Rocket feature is not available everywhere and headline specifications concern the optional Thrust augment.

**No official flight-duration figure, refill interval, nozzle flow map, pressure curve, final inertia tensor or tank thermodynamics was verified.** Estimates from third-party articles are not treated as manufacturer specifications. The supplied 2020-labelled model is not asserted to be the newer Rocket hardware. Driving mass/power/suspension estimates remain separately disclosed.

### Explicit GAME balance, not certified physics

`HOP` in `engine/src/flight.js` labels all of the following as game settings:

| Setting | Game value |
|---|---:|
| Absolute powered-time ceiling | 6 simulated seconds per hop |
| Automatic descent begins | 2.8 simulated seconds, or below 35% gas |
| Minimum launch supply | 85%, with actual wheel contact |
| Full refill | 20 simulated seconds on the ground only |
| Lift soft ceiling | 8 m above downward ground ray |

- Launch is a short force pulse, followed by limited manual lift/thrust and automatic descent. Neutral input is **not** altitude-holding cruise. Momentum and Earth gravity govern the arc.
- Upward and forward thrust, boost, air braking and attitude torque spend the **same** supply. No energy is created by releasing boost or pressing Land. Engagement does not refill the tank.
- No airborne re-arm or airborne refill. At the hard time ceiling or zero supply there is **no powered lift, braking or stabilization**, including no free landing reserve. Gravity takes over; a hard landing is possible if the player spends the reserve aggressively.
- Landing requests use only the remaining gas. Touchdown disarms without resetting charge; normal wheel driving returns. Ground refill is accelerated for playability and does not claim to represent real compressor performance.
- No airplane wings, unlimited hover, sustained travel mode or transform/velocity assignment. The full Rapier dynamic body remains in use.

Six optional low stunt gates replace the high hover-course targets. Drive mode is the normal race; using a hop makes that lap practice-only.

## Track and gameplay improvements

Original red/ivory kerbs follow the actual road spline outside its 10 m driving strip. The existing asphalt base texture is retained with a deterministic 128² aggregate-detail sample and subtle rubbered lanes. Checkerboard start paint, a branded gantry, course reflectors and bend chevrons add readable racing structure. Existing road/collision vertices are unchanged; kerbs/boards are cosmetic trackside art, not a new rumble-strip tire solver. Gantry posts are outside the existing guardrail collision boundary. No extra dynamic lights or shadow maps were added.

Static same-material art is baked/merged where compatible; repeated reflectors/checker tiles are instanced. New vegetation remains the existing v0.4 instanced meadow, not a replacement that lowers density.

Time Attack adds a three-second launch countdown, three ordered sector splits, signed split difference versus a same-assist stored benchmark, a persistent clean-lap personal best and gold/silver/bronze targets (130/160/above 160 seconds). Recovery, hops or changing assist invalidate the current PB attempt; the following lap becomes a fresh attempt. Stored data is validated and blocked storage fails safely. These are solo time trials, not AI opponents/multiplayer.

## Same-graphics low-end work

The Three.js matrix manual explains avoiding automatic transform recomputation on static objects [2](https://threejs.org/manual/en/matrix-transformations.html). We calculate and freeze local/world matrices only on truly static terrain, track, vegetation instances, rails and circuit art. Car/wheels, character animation, lights/targets, water reflection and gates remain live; shader wind and visibility still work. Camera chase vectors are reused instead of allocating three new vectors every render. HUD text/gear markup is written only when changed, instead of recreating unchanged DOM text/span nodes at 20 Hz; unit and real-browser identity checks cover this. Existing v0.4 exact-material multi-draw fallback, invisible-shaft bypass, object reuse, fixed solver and diagnostic throttling remain.

An exploratory 39-cell forest split was **rejected** after actual A/B measurements: it culled some offscreen tree triangles but added many draw submissions to what had been a single cheap instanced billboard mesh. The final release retains that original one-draw forest and every tree. Avoid presenting a triangle-count reduction as a win when submission overhead regresses.

The final `../game/time-attack-v5/static-forest-comparison.json` records actual same-scene matrix A/B readback and CPU matrix-update microbenchmark. This is not whole-game or physical-tablet FPS evidence. New track art has real rendering cost; no whole-version speedup is promised by adding it.

**Unchanged presets:** default Full 1920×1080 pixel budget, existing texture assets, car geometry, 1024² directional/512² headlight shadows, current-frame 512² planar lake reflection, photographed sky/grass, lighting and ACES. Balanced/Performance remain explicit choices, not automatic downgrades. Software browser QA explicitly selects Performance on both A/B sides for practical readback testing; that is not the shipped default.

No paid resources or GPU provisioning. Low-end hardware still has finite bandwidth/thermal budgets: there is no honest universal “same graphics, better graphics and guaranteed 60 FPS” promise. Release evidence separates CPU microbenchmarks, draw submissions, image checks, gameplay tests and unmeasured physical-device performance.
