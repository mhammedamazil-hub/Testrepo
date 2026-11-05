// LVL1 - the collision level baked from the villa GLB by `tools/game_level.py`.
//
// The renderer draws VPK1 geometry; the *game* needs a different truth: where a 0.7 m wide
// body may stand and how high the floor is there. Both are derived from the same triangles,
// so the level can never drift away from the art.
//
// Layout (little endian), 56 B header:
//
//   char     magic[4]      'LVL1'
//   uint32   version, cols, rows, n_obj, res0, res1, res2
//   float    cell_m, origin_x, origin_z, spawn_x, spawn_y, spawn_z
//   float    ground[cols*rows]   surface height, row-major, row = z, col = x
//   uint8    walk[cols*rows]     1 = a body fits here and it is reachable from the spawn
//   float    obj[n_obj*4]        x, y, z, radius
//
// This header is deliberately dependency-free (no GL, no JNI) so `tools/game_sim.cpp` can
// compile it for the desktop and walk the exact same level the tablet walks.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static const char LEVEL_MAGIC[4] = {'L', 'V', 'L', '1'};

struct LevelObj {
    float x = 0, y = 0, z = 0, r = 0.75f;
};

struct Level {
    uint32_t cols = 0, rows = 0, n_obj = 0;
    float cell = 0.3f, x0 = 0, z0 = 0;
    float spawn[3] = {0, 0, 0};
    std::vector<float> ground;
    std::vector<uint8_t> walk;
    std::vector<LevelObj> objs;

    bool load(const std::vector<uint8_t>& b, std::string* err) {
        if (b.size() < 56) {
            if (err) *err = "level shorter than the LVL1 header";
            return false;
        }
        if (std::memcmp(b.data(), LEVEL_MAGIC, 4) != 0) {
            if (err) *err = "bad level magic (run tools/game_level.py)";
            return false;
        }
        uint32_t v = 0;
        std::memcpy(&v, b.data() + 4, 4);
        if (v != 1) {
            if (err) *err = "unsupported level version";
            return false;
        }
        std::memcpy(&cols, b.data() + 8, 4);
        std::memcpy(&rows, b.data() + 12, 4);
        std::memcpy(&n_obj, b.data() + 16, 4);
        if (cols == 0 || rows == 0 || cols > 4096 || rows > 4096) {
            if (err) *err = "absurd level dimensions";
            return false;
        }
        std::memcpy(&cell, b.data() + 32, 4);
        std::memcpy(&x0, b.data() + 36, 4);
        std::memcpy(&z0, b.data() + 40, 4);
        for (int i = 0; i < 3; ++i) std::memcpy(&spawn[i], b.data() + 44 + 4 * i, 4);
        if (cell <= 0.02f || cell > 5.0f) {
            if (err) *err = "absurd cell size";
            return false;
        }

        const size_t n = (size_t)cols * rows;
        const size_t off_g = 56;
        const size_t off_w = off_g + n * 4;
        const size_t off_o = off_w + n;
        if (b.size() < off_o + (size_t)n_obj * 16) {
            if (err) *err = "truncated level payload";
            return false;
        }
        ground.resize(n);
        walk.resize(n);
        std::memcpy(ground.data(), b.data() + off_g, n * 4);
        std::memcpy(walk.data(), b.data() + off_w, n);
        objs.clear();
        for (uint32_t i = 0; i < n_obj; ++i) {
            LevelObj o;
            std::memcpy(&o.x, b.data() + off_o + i * 16 + 0, 4);
            std::memcpy(&o.y, b.data() + off_o + i * 16 + 4, 4);
            std::memcpy(&o.z, b.data() + off_o + i * 16 + 8, 4);
            std::memcpy(&o.r, b.data() + off_o + i * 16 + 12, 4);
            objs.push_back(o);
        }
        return true;
    }

    bool load_file(const char* path, std::string* err) {
        FILE* f = std::fopen(path, "rb");
        if (!f) {
            if (err) *err = std::string("cannot open ") + path;
            return false;
        }
        std::fseek(f, 0, SEEK_END);
        long n = std::ftell(f);
        std::fseek(f, 0, SEEK_SET);
        if (n <= 0) {
            std::fclose(f);
            if (err) *err = std::string("empty level ") + path;
            return false;
        }
        std::vector<uint8_t> b((size_t)n);
        size_t got = std::fread(b.data(), 1, b.size(), f);
        std::fclose(f);
        if (got != b.size()) {
            if (err) *err = "short read on level";
            return false;
        }
        return load(b, err);
    }

    // ---- queries -------------------------------------------------------------
    void to_cell(float x, float z, int* r, int* c) const {
        int cc = (int)std::floor((x - x0) / cell);
        int rr = (int)std::floor((z - z0) / cell);
        if (cc < 0) cc = 0;
        if (rr < 0) rr = 0;
        if (cc >= (int)cols) cc = (int)cols - 1;
        if (rr >= (int)rows) rr = (int)rows - 1;
        *r = rr;
        *c = cc;
    }

    bool inside(float x, float z) const {
        return x >= x0 && z >= z0 && x < x0 + cols * cell && z < z0 + rows * cell;
    }

    bool walk_at(float x, float z) const {
        if (!inside(x, z)) return false;
        int r, c;
        to_cell(x, z, &r, &c);
        return walk[(size_t)r * cols + c] != 0;
    }

    /// Height of the floor under (x, z). Bilinear, because a 0.3 m staircase of float cells
    /// would make the camera judder on every cell boundary; the collision test above stays
    /// nearest-cell so walls stay exactly as baked.
    float ground_at(float x, float z) const {
        if (!inside(x, z)) return 0.0f;
        float fx = (x - x0) / cell - 0.5f;
        float fz = (z - z0) / cell - 0.5f;
        int c0 = (int)std::floor(fx), r0 = (int)std::floor(fz);
        float tx = fx - c0, tz = fz - r0;
        float acc = 0.0f, wsum = 0.0f;
        for (int dr = 0; dr <= 1; ++dr) {
            for (int dc = 0; dc <= 1; ++dc) {
                int r = r0 + dr, c = c0 + dc;
                if (r < 0 || c < 0 || r >= (int)rows || c >= (int)cols) continue;
                float w = (dc ? tx : 1.0f - tx) * (dr ? tz : 1.0f - tz);
                acc += ground[(size_t)r * cols + c] * w;
                wsum += w;
            }
        }
        return wsum > 1e-4f ? acc / wsum : ground_at_nearest(x, z);
    }

    float ground_at_nearest(float x, float z) const {
        if (!inside(x, z)) return 0.0f;
        int r, c;
        to_cell(x, z, &r, &c);
        return ground[(size_t)r * cols + c];
    }

    /// Does a body of `rad` around (x, z) fit? Eight rim points plus the centre: a cell grid
    /// alone would let a shoulder poke through a 0.3 m wall.
    bool body_fits(float x, float z, float rad) const {
        if (!walk_at(x, z)) return false;
        for (int i = 0; i < 8; ++i) {
            float a = (float)i * 0.7853982f;
            if (!walk_at(x + std::cos(a) * rad, z + std::sin(a) * rad)) return false;
        }
        return true;
    }

    /// Any cell walkable at all? Used by the HUD's "you are outside the garden" guard.
    float ground_min(float x, float z, float rad) const {
        float lo = ground_at_nearest(x, z);
        for (int i = 0; i < 8; ++i) {
            float a = (float)i * 0.7853982f;
            float g = ground_at_nearest(x + std::cos(a) * rad, z + std::sin(a) * rad);
            if (g < lo) lo = g;
        }
        return lo;
    }

    float extent_x() const { return cols * cell; }
    float extent_z() const { return rows * cell; }
};
