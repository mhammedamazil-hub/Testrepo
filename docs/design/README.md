# Circuit UI design references

Two **AI-generated design concepts**, selected by the user before implementation:

- `steering-wheel-reference.png`: wheel + actual pedal-shaped controls.
- `directional-buttons-reference.png`: angular left/right buttons + pedal controls.

These are references, **not actual game screenshots**, a graphics-quality promise, Steam integration, or proof of runtime performance. They informed the implemented CSS/SVG controls and compact HUD. The live game retains its existing licensed Roadster/landscape/sky rather than replacing it with concept imagery.

Actual implementation evidence and limitations: `../game/circuit-v3/`. The user can switch wheel/buttons from the in-game controls or the quick control switch. Walking retains an independent joystick. All driving inputs use the actual Rapier dynamics, not a UI-only animation.
