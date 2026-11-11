# Alpine Grand Prix — multiplayer v6

The custom Three.js edition now has a separate **playable multiplayer client** at
[multiplayer.html](https://mhammedamazil-hub.github.io/Testrepo/multiplayer.html).
The existing solo game links to it; solo driving, walking, finite hops, the original
Roadster and the previous cinematic remain intact.

## Race with friends

1. Open the multiplayer link, enter a temporary guest name, choose one of six
   paint colours and select Low, Balanced or High graphics.
2. **Create a room**, then copy its invitation to your friends. Invitations open
   the guest screen with the room code filled in; no account or email is needed.
3. Friends choose their names/colours and **Join room**. All racers click **Ready**.
4. The host chooses 1–3 laps and starts a shared four-second countdown. Rooms
   support **2–6 racers**. New entrants cannot join an active race.
5. Follow eight ordered gates around the **5,687.88 m** circuit. The road is 14 m
   wide inside a new 2.4 × 2.4 km graded landscape with runoff and guardrails.
6. Results include recovery penalties and DNF; the host can return everyone to
   the lobby for a rematch. A race times out after 20 minutes.

**Desktop:** WASD/arrows drive, Space brakes, Shift uses nitro, R recovers,
Q briefly reverses the camera, F requests fullscreen. Reverse selection uses
D/R while stopped. **Touch:** independent wheel or arrow steering, gas/brake
pedals, D/R, nitro, recovery and camera drag. MAP shows the circuit and car.
Chat input releases driving controls; Enter sends. Quick comments are one tap.
Online races do not pause when a menu/tab loses focus.

**No multiplayer flight or walking.** Cars use local Rapier four-wheel dynamics
against the terrain, road and rails. Opponents are smoothed, coloured visual
cars, **not collision bodies**; this deliberately avoids peer collision jitter.
The ground boost is a game powerup, not a manufacturer specification.

- One nitro charge, 2.5 seconds / capped 9,500 N grounded force.
- Four cyan pickup positions replenish a charge, with 12-second per-racer refill.
- Recovery returns to the last passed gate (or grid), costs **+3 seconds**, and
  has a five-second cooldown. Severe off-road/slow overturned states request
  automatic recovery after three seconds.
- Chat: 160 characters, rate limited, plain-text DOM, 35 visible messages.
  Guest names have 18 characters. Host can remove lobby guests.

## What GitHub Pages does—and does not—host

Pages serves HTML, JavaScript, WASM and models. It **cannot run a race/signalling
server**. The production client uses the free public PeerJS discovery service at
`0.peerjs.com:443`; peers then exchange real WebRTC data channels. The host's
browser owns the room, countdown, checkpoint order, results, inventory and
recovery. Close the host and the room ends: no host migration or persistence.

This is a friends-racing architecture, not dedicated authoritative server physics
or secure esports anti-cheat. Each client runs its own dynamic car simulation.
Host checks sequences, rate, plausible displacement, flight height and ordered
crossings, but modified clients/hosts can still cheat. Traffic is 20 Hz client
states and 10 Hz host snapshots; remote transforms interpolate.

**Connectivity caveat:** public signalling has no uptime promise. Networks that
block WebRTC or need TURN may fail; no paid or guaranteed TURN relay is configured.
Neither a successful HTTP discovery request nor local two-client testing proves
cross-NAT connectivity. No external service was provisioned or purchased.
See [validation](VALIDATION.md) for the exact public smoke outcome.

Names are temporary (`sessionStorage` only); chat/room state live in browser
memory. The signalling operator learns connection metadata, and room members
receive names, messages and WebRTC connection metadata. Room codes/invitations
are not passwords. There is no public room directory or permanent account.

## Graphics choices

| Preset | Maximum pixel budget (16:9 example) | Car | Shadows | Trees / grass |
|---|---|---|---|---|
| Low | 360,000 (800×450) | lighter derivative | off | 350 / 0 |
| Balanced | 921,600 (1280×720) | lighter derivative | 1024 sun map | 700 / 1800 |
| High | 2,073,600 (1920×1080) | unchanged full car | 2048 sun map | 1100 authored pines / 4500 |

The renderer uses an aspect-correct pixel budget, independently of CSS display size.
Quality is selected before connection. Suggestions use exposed device memory /
CPU thread hints; the user can override them. Pixel budgets, instanced scenery,
spatial grass culling and batched vehicles control cost; no phone FPS guarantee.
Low/Balanced's **58,697-triangle / 3,932,628-byte** model is an attributed CC-BY-4.0
metarex.4d derivative with 256px textures. The uploaded/full car is unchanged.
These are rasterized/stylized graphics, not a photorealism claim.

## Run and deploy

```sh
npm ci --prefix engine
npm run signal --prefix engine     # terminal 1: local discovery on port 9000
npm run dev --prefix engine        # terminal 2: Vite on 3001, /peerjs proxy
npm test --prefix engine
node engine/tests/grand-prix-drive.js
npm run build --prefix engine      # .exports/alpine, both HTML entry points
```

Use the same Vite origin for both local clients. Browser-facing code never calls
another device's localhost; Vite proxies discovery/WebSockets. Production defaults
to public signalling, without needing a server on Pages. Optional custom discovery
is selected at **build time**:

```sh
VITE_PEER_HOST=your-signalling-host.example \
VITE_PEER_PORT=443 VITE_PEER_PATH=/peerjs VITE_PEER_SECURE=true \
npm run build --prefix engine
```

Self-hosting needs an independently hosted, trusted HTTPS/WSS reverse proxy to
PeerServer (the included `tools/game/peer_server.cjs` is local-development tooling,
not a hardened public service). TURN credentials/ICE configuration require a
separate deployment design; the above variables configure signalling only.
Never embed a privileged server secret in a static build.

The branch's existing `game-build.yml` validates both games and publishes both
entry points at root and `/alpine/`. It verifies live HTML, low GLB and multiplayer
crawler image. Room invitations use the hash, so the room code is not needed by
Pages or its crawler. Shared links expose the common game title/preview, not a
private room's live roster or custom room name.

### Code map

- `engine/src/online/main.js`: guest/lobby/race/results UI and local physics loop.
- `network.js`: PeerJS connection lifecycle and host snapshot/action routing.
- `race-session.js`: testable host room, gates, laps, nitro and recovery rules.
- `protocol.js`: bounded input, profiles, packet and snapshot validation.
- `map.js`, `world.js`, `quality.js`: expanded circuit, visuals/colliders, presets.
- `engine/tests/multiplayer.test.js`: deterministic rules and actual boost dynamics.
- `tools/game/multiplayer_*`: independent browser/layout/graphics/public tests.

Credits are exposed in-game at `world/credits.txt`; derivative hashes and
attribution are in `world/grand-prix/low-car-provenance.json`.
