// The game itself: player movement, collision response, and the walk-through world.
//
// v10 is exploration: there is no score, no timer and nothing to collect. The level still
// carries a handful of "objective" positions, but they are only used by the desktop harness
// as waypoints to prove the whole garden can be walked. `explore` is what decides whether the
// orbs exist as gameplay at all.
//
// Deliberately free of GL, JNI and Android: `tools/game_sim.cpp` compiles this header for
// the host, so the walking, the collisions and the win condition are actually executed and
// measured before an APK is built. The tablet runs this exact code.
#pragma once
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

#include "level.h"

struct Player {
    float feet[3] = {0, 0, 0};   // x, y (floor height), z
    float yaw = 0.0f;            // radians, 0 looks towards +z
    float pitch = 0.0f;
    float eye = 1.62f;           // eye height above the floor
};

struct Game {
    Level lv;
    Player p;
    std::vector<uint8_t> taken;
    int orbs = 0, total = 0;
    float time = 0.0f;
    int state = 0;               // 0 = playing, 1 = all orbs collected
    float bob = 0.0f;            // camera bob phase
    float bob_amp = 0.0f;
    int last_pickup = -1;
    float pickup_flash = 0.0f;
    // Exploration mode: no pickups, no timer running towards anything, no win screen. The
    // player is here to look at the garden.
    bool explore = true;
    bool sprint = false;          // held double-tap / two-finger? unused, kept for the stick
    const std::vector<LevelObj>& waypoints() const { return lv.objs; }

    static constexpr float kBodyRadius = 0.26f;   // 52 cm wide: a shoulder, not a barrel
    static constexpr float kStepUp = 0.45f;   // terrace steps and the plinth lip
    static constexpr float kLookSpeed = 2.6f; // radians per second at full stick
    static constexpr float kWalkSpeed = 3.15f;
    static constexpr float kPickupRadius = 1.55f;

    bool init(const char* level_path, std::string* err) {
        if (!lv.load_file(level_path, err)) return false;
        total = (int)lv.objs.size();
        reset();
        return true;
    }

    /// Same, but from a Level the caller has already loaded (the device reads it through
    /// AAssetManager, the desktop harness through fopen).
    bool bind(const Level& level, std::string* err) {
        if (level.cols == 0 || level.walk.empty()) {
            if (err) *err = "empty level";
            return false;
        }
        lv = level;
        total = (int)lv.objs.size();
        reset();
        return true;
    }

    void reset() {
        for (int i = 0; i < 3; ++i) p.feet[i] = lv.spawn[i];
        p.feet[1] = lv.ground_at(lv.spawn[0], lv.spawn[2]);
        // spawn looks at the house (the villa sits north of the lawn: +z)
        p.yaw = 0.0f;
        p.pitch = -0.02f;
        taken.assign(lv.objs.size(), 0);
        orbs = 0;
        time = 0.0f;
        state = 0;
        bob = 0.0f;
        bob_amp = 0.0f;
        last_pickup = -1;
        pickup_flash = 0.0f;
    }

    void look(float dyaw, float dpitch) {
        p.yaw += dyaw;
        p.pitch += dpitch;
        if (p.pitch > 1.45f) p.pitch = 1.45f;
        if (p.pitch < -1.45f) p.pitch = -1.45f;
        // keep the angle bounded so it cannot lose float precision in a long session
        const float two_pi = 6.28318531f;
        if (p.yaw > two_pi) p.yaw -= two_pi;
        if (p.yaw < -two_pi) p.yaw += two_pi;
    }

    /// Can the body stand at (x, z) given it is currently at floor height `from_y`?
    /// Blocked cells are blocked; a step taller than kStepUp is a wall, not a step.
    bool can_stand(float x, float z, float from_y) const {
        if (!lv.body_fits(x, z, kBodyRadius)) return false;
        float g = lv.ground_at(x, z);
        if (g - from_y > kStepUp) return false;      // too tall to step onto
        if (from_y - g > 2.2f) return false;         // would be a fall off a roof
        return true;
    }

    /// Move with wall sliding: try the full step, then each axis alone. Returns true if
    /// *anything* moved, so the caller can decide about the bob phase.
    bool move(float dx, float dz) {
        if (dx == 0.0f && dz == 0.0f) return false;
        const float fy = p.feet[1];
        if (can_stand(p.feet[0] + dx, p.feet[2] + dz, fy)) {
            p.feet[0] += dx;
            p.feet[2] += dz;
        } else if (can_stand(p.feet[0] + dx, p.feet[2], fy)) {
            p.feet[0] += dx;
        } else if (can_stand(p.feet[0], p.feet[2] + dz, fy)) {
            p.feet[2] += dz;
        } else if (can_stand(p.feet[0], p.feet[2], fy)) {
            return false;   // wedged: still standing on legal ground, just cannot move
        } else {
            return false;   // should not happen; refuse rather than teleport into a wall
        }
        // follow the floor smoothly instead of snapping per cell
        float g = lv.ground_at(p.feet[0], p.feet[2]);
        p.feet[1] += (g - p.feet[1]) * 0.55f;
        if (std::fabs(g - p.feet[1]) < 0.01f) p.feet[1] = g;
        return true;
    }

    /// One frame. `fwd`/`side` are -1..1 from the touch stick; `dyaw`/`dpitch` come from the
    /// look drag. Movement is frame-rate independent because speed is multiplied by dt.
    void update(float dt, float fwd, float side, float dyaw, float dpitch) {
        if (dt > 0.1f) dt = 0.1f;          // a stalled frame must not teleport the player
        if (dt <= 0.0f) return;
        look(dyaw, dpitch);
        if (state == 1) {
            pickup_flash *= 0.94f;
            return;
        }
        if (!explore) time += dt;

        float mag = std::sqrt(fwd * fwd + side * side);
        if (mag > 1.0f) {
            fwd /= mag;
            side /= mag;
            mag = 1.0f;
        }
        // forward on the ground plane, right-hand perpendicular
        const float sy = std::sin(p.yaw), cy = std::cos(p.yaw);
        const float fx = sy, fz = cy;
        const float rx = cy, rz = -sy;
        const float sp = kWalkSpeed * mag * dt;
        move((fx * fwd + rx * side) * sp, (fz * fwd + rz * side) * sp);

        // camera bob: small, and squared with speed so standing still is perfectly still
        bob_amp += ((mag > 0.05f ? 1.0f : 0.0f) - bob_amp) * std::fmin(1.0f, dt * 6.0f);
        bob += dt * 8.6f * (0.4f + 0.6f * mag);

        // pickups: horizontal distance, so walking under one still counts
        if (explore) return;      // nothing to collect: the garden is the point
        for (size_t i = 0; i < lv.objs.size(); ++i) {
            if (taken[i]) continue;
            const LevelObj& o = lv.objs[i];
            const float dx = o.x - p.feet[0];
            const float dz = o.z - p.feet[2];
            const float dy = o.y - (p.feet[1] + p.eye);
            if (dx * dx + dz * dz < kPickupRadius * kPickupRadius &&
                std::fabs(dy) < 2.4f) {
                taken[i] = 1;
                ++orbs;
                last_pickup = (int)i;
                pickup_flash = 1.0f;
                if (orbs >= total) state = 1;
            }
        }
        if (pickup_flash > 0.0f) pickup_flash *= 0.90f;
    }

    float eye_pos(float out[3]) const {
        out[0] = p.feet[0];
        out[1] = p.feet[1] + p.eye + std::sin(bob) * 0.022f * bob_amp;
        out[2] = p.feet[2];
        return out[1];
    }

    void look_dir(float out[3]) const {
        const float cp = std::cos(p.pitch);
        out[0] = std::sin(p.yaw) * cp;
        out[1] = std::sin(p.pitch);
        out[2] = std::cos(p.yaw) * cp;
    }

    /// Distant objective hint for the HUD compass: index of the nearest uncollected orb
    /// and its bearing relative to the view, in radians (-pi..pi).
    bool nearest_orb(int* idx, float* bearing) const {
        float best = 1e30f;
        int bi = -1;
        for (size_t i = 0; i < lv.objs.size(); ++i) {
            if (taken[i]) continue;
            const float dx = lv.objs[i].x - p.feet[0];
            const float dz = lv.objs[i].z - p.feet[2];
            const float d = dx * dx + dz * dz;
            if (d < best) {
                best = d;
                bi = (int)i;
            }
        }
        if (bi < 0) return false;
        const float dx = lv.objs[bi].x - p.feet[0];
        const float dz = lv.objs[bi].z - p.feet[2];
        float b = std::atan2(dx, dz) - p.yaw;
        while (b > 3.14159265f) b -= 6.28318531f;
        while (b < -3.14159265f) b += 6.28318531f;
        *idx = bi;
        *bearing = b;
        return true;
    }
};
