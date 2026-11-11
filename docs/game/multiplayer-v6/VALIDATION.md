# Grand Prix v6 — validation and limits

## Results

| Check | Outcome | Evidence |
|---|---|---|
| Repository Python release/provenance suite | **63 passed** | `python -m unittest discover -s tests` |
| Node rules and actual Rapier regressions | **48 passed** | `npm test --prefix engine` |
| Actual two-client browser integration | **22 passed**, no browser runtime exceptions | [browser-validation.json](browser-validation.json) |
| Expanded circuit, input-only full Rapier lap | **Passed**, eight gates, zero rejected snapshots | [physics-lap.json](physics-lap.json) |
| Responsive multiplayer UI / text-field key isolation | **8 passed** | [ui-validation.json](ui-validation.json) |
| Existing solo layout / multitouch | **12 passed** | `node tools/game/time_attack_ui_test.cjs` |
| Low / Balanced / High asset and render checks | **3 passed** | [graphics-validation.json](graphics-validation.json) |
| Both static HTML entry points production build | **Passed** | `npm run build --prefix engine` |
| Public-service production browser connection | **Failed in sandbox** | [public-signalling-smoke.json](public-signalling-smoke.json) |

The public smoke attempted to register the production host through the default
PeerJS service and received a network error. No public room/data channel was
established. The exact network cause is not diagnosed; the sandbox restricts
outbound access. This is **not** public cross-network acceptance or evidence that
users on arbitrary networks can connect. Test a shared invitation on two real
networks before relying on the public deployment. No guaranteed TURN service is
configured. An earlier HTTP discovery response alone is not WebRTC proof.

## What the successful tests actually do

The browser integration runs independent Chromium contexts and **real PeerJS /
WebRTC data channels** through the included local discovery server and same-origin
Vite proxy. It creates a room, joins a different name/colour, checks host-only
start, shared countdown/laps, actual force-driven movement and remote car colour
and orientation, plain-text chat and quick messages, no flight, host nitro,
penalized recovery, late-join rejection, podium/rematch and host departure.

**Important separation:** podium/rematch UI is driven by a synthetic host finish
snapshot. The browser test does not physically drive two full race laps. Full
course acceptance is separately checked with the real Rapier simulation and
host gate validator: **5,687.88 m, 21,442 ticks, 357.367 simulated seconds, eight
gates, zero rejected states, maximum road-centre deviation 1.209 m, all four
wheel contacts**. Only pursuit-driver throttle/steering/brake inputs are used
after spawn; no test teleport/velocity assignment drives that lap. It is not a
human fun/playability score or a multiplayer endurance test.

Software rendering is deliberately decoupled from the 60 Hz test simulation.
Browser screenshots use QA-only preserved drawing buffers and synchronous
canvas image copying so background-context/resize compositing does not erase the
WebGL layer. These are real renderer pixels beneath real DOM UI, not generated
concept art. The production renderer does not preserve its drawing buffer.

Layout tests cover 360×780, 430×932, 932×430 and 1100×700 with both wheel and
arrows, six standings entries and chat controls. Screenshots: [lobby](room-lobby.png),
[landscape race](race-landscape.png), [portrait race](race-portrait.png).
Graphics previews are explicitly labelled single-host previews, not fake races:
[Low](low-preset.png), [Balanced](balanced-preset.png), [High](high-preset.png).

There is **no physical-phone/tablet FPS measurement**, no sustained six-client
High-preset performance result, no photorealism approval and no cross-NAT/TURN
certification. A successful 60 Hz physics simulation is not a 60 FPS benchmark.
The host's client-run physics architecture is not secure anti-cheat.

## Regression and provenance

Original source Roadster SHA-256:
`e10253ef699ed774a4d9f749bd01d176931b8980a0e7af6a9b717bfd443a44d3`

Existing compiled Roadster:
`d9ecef7a8b761bfbaad2ad9a6a0c8812b1d510a72a67a92c402c28c35e34d4f7`

Original terrain:
`df54e53ec2fb2c840014d50366df7eb424286d25c6bec03ac26dbb25c896ccca`

Existing graded solo terrain:
`3cf0a54b6b65be8e6904b74a7b5e2177df223393fdc95c21e9432e9604bb70a7`

These assets are unchanged. The original cinematic and its previous MP4 are
unchanged relative to the prior `2fdb5f3` release. Multiplayer terrain is generated
separately. Shared input only adds text-field isolation; shared physics only adds
an optional grounded boost force (solo never supplies it). Solo lobby spacing was
compacted to accommodate the new link without covering its vehicle panel.

CI reruns Python/Node/real circuit drives, builds both clients, publishes Pages
and checks public static resources. It does not run the downloaded software
Chromium harness or certify public discovery/connectivity. Browser tools require
the separately downloaded `.cache/browser` Chromium/Playwright and runtime libs;
those reproducible toolchains are intentionally not committed.
