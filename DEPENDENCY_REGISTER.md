# DEPENDENCY_REGISTER — Reality Engine Phase 1

## Dependency Evaluation & Compliance

| # | Dependency | Version | License | Purpose | Status | Platform | Build Method |
|---|------------|---------|---------|---------|--------|----------|--------------|
| 1 | Jolt Physics | latest | MIT | Physics simulation (rigid bodies, colliders, collision detection) | CLONED | Linux x86_64 | CMake, static lib |
| 2 | glTF 2.0 | 2.0 | Public (Khronos) | Asset interchange format | SPEC ONLY | N/A | Parser written in-house |
| 3 | JSON (nlohmann) | latest | MIT | Scene/project serialization | NOT USED | N/A | Custom minimal JSON (C++ std) |
| 4 | C++ Standard Library | g++ 12.2 | N/A | Containers, algorithms, filesystem | USED | System | System |
| 5 | CMake | 4.4.5 | BSD-like | Build system | INSTALLED | pip | pip install |

## Dependencies Evaluated but NOT Used

| # | Dependency | License | Evaluation | Reason Not Used |
|---|------------|---------|------------|-----------------|
| A | EnTT | MIT | Evaluated for ECS | External dependency requiring install; custom lightweight ECS sufficient for Phase 1 |
| B | Flecs | MIT/Zlib | Evaluated for ECS | External dependency requiring install; custom ECS sufficient |
| C | SDL3 | zlib | Evaluated for windowing/input | Not installed locally, no GPU/display; headless only in Phase 1 |
| D | Vulkan SDK | Apache | Evaluated for rendering | Not available (no GPU, no dev headers, no root); headless renderer only |
| E | spdlog | MIT | Evaluated for logging | Custom logging sufficient; avoids external dep |
| F | RapidJSON | MIT | Evaluated for JSON | Custom minimal JSON parser/writer sufficient |
| G | Assimp | BSD | Evaluated for asset import | Not needed; glTF loader written in-house (Phase 1: stub) |
| H | Bullet Physics | zlib | Evaluated for physics | Jolt selected (MIT, modern, CCD, multithreaded) |
| I | PhysX | BSD | Evaluated for physics | Proprietary-ish, complex; Jolt simpler |
| J | Blender | GPL | Evaluated for authoring | Not installed locally; addon written to bpy API spec |

## Licenses

| Component | License | Notes |
|-----------|---------|-------|
| Reality Engine C++ code | Proprietary (see LICENSE) | Engine core, ECS, physics wrapper, runtime |
| Reality Engine Blender addon | GPL v3+ | Required for Blender addons; separate from engine |
| Jolt Physics | MIT | Static linked, attribution in THIRD_PARTY_NOTICES.md |
| Python platform | Proprietary | Existing universal_engine code |
| glTF 2.0 spec | Public (Khronos) | Format specification only |

## Build Outputs

| Output | Path | Type |
|--------|------|------|
| Engine static libs | `engine/build/lib/*.a` | Static libraries |
| Jolt static lib | `engine/build/lib/libJolt.a` | Static library |
| Runtime executable | `engine/build/runtime/reality_runtime` | Executable |
| Blender addon | `blender_addon/reality_engine_studio/` | Python package |

## Memory Constraints

| Constraint | Value | Mitigation |
|------------|-------|------------|
| RAM | 3.8GB | Release build (-O2), strip symbols (-s), -j2 parallel |
| Jolt debug build | Too much RAM | Release only |
| Blender build | Impossible (3.8GB RAM) | Addon only, no Blender rebuild |

## Local Installation Prefix

All dependencies installed to: `/home/user/Testrepo/engine/install/`

No system packages installed. No root required.
