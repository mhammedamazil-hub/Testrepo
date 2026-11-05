// VPK1 - the flat format produced by `tools/villa_pack.py`.
//
// The Android viewer deliberately does NOT parse glTF: 723 nodes, 1019 primitives and a
// JSON tree would need a real parser and would still draw badly on a cheap tablet. The
// packer flattens all of that at build time; this header is the whole runtime model.
//
// Layout (little endian), header 84 B, draw 100 B, vertex 20 B, index 2 B:
//
//   VHeader
//   VDraw     [n_draws]
//   VTexture  [n_textures]     (offset,length) of JPEG/PNG bytes, absolute in file
//   vertices  [n_verts]        stride 20: uint16 pos[3], uint16 pad, int8 nrm[4],
//                              float uv[2]
//   indices   [n_indices]      uint16, relative to the draw's first vertex
//   blob                       texture payloads
//
// Positions are quantised into the draw's own bbox: world = pos_min + (p/65535)*pos_scale.
// Chunks never exceed 65535 vertices, so uint16 indices are enough everywhere and no
// GLES2 extension is required.
#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

static const uint16_t VPK_NO_TEXTURE = 0xFFFF;
static const uint32_t VPK_VERTEX_STRIDE = 20;
static const uint32_t VPK_ALPHA_CUTOUT = 1u;
// VDraw.flags bits, shared by the viewer and the game
static const uint16_t VPK_FLAG_CUTOUT = 1u;   // alpha test the texture
static const uint16_t VPK_FLAG_2SIDED = 2u;   // do not cull (and in the game: foliage + sway)
static const uint16_t VPK_FLAG_GLASS = 4u;    // blended glazing
static const uint16_t VPK_FLAG_WATER = 8u;    // animated pool surface

#pragma pack(push, 1)
struct VHeader {
    char magic[4];
    uint32_t version;
    uint32_t n_draws;
    uint32_t n_textures;
    uint32_t n_verts;
    uint32_t n_indices;
    uint32_t reserved;
    float scene_min[3];
    float scene_max[3];
    float fit_min[3];
    float fit_max[3];
    uint8_t pad[8];
};

struct VDraw {
    uint32_t index_offset;   // first index (not byte offset)
    uint32_t index_count;
    uint32_t vert_offset;    // first vertex
    uint32_t vertex_count;
    float pos_min[3];
    float pos_scale[3];
    float uv_scale[2];       // reserved, always 0/0 for now
    float uv_offset[2];
    uint16_t tex;            // texture index or VPK_NO_TEXTURE
    uint16_t flags;          // bit0 = alpha cutout
    float base_color[4];
    float alpha_cutoff;      // <= 0 means "no cutout"
    float emissive[3];
    float pad[2];
};

// AOB1 - the baked lighting sidecar written by tools/villa_pack.py --ao-out.
// GLES2 has no shadow maps and no SSAO, and the villa and the sun are static, so the sun's
// visibility and the ambient occlusion are computed once, per vertex, by raymarching a voxel
// grid of the scene. This header is the whole runtime format.
static const char AO_MAGIC[4] = {'A', 'O', 'B', '1'};

struct AoMap {
    uint32_t n_verts = 0;
    std::vector<uint8_t> ao;    // ambient visibility, per vertex
    std::vector<uint8_t> sun;   // sun visibility, per vertex
    bool load(const std::vector<uint8_t>& b, uint32_t expect_verts) {
        if (b.size() < 12 || std::memcmp(b.data(), AO_MAGIC, 4) != 0) return false;
        std::memcpy(&n_verts, b.data() + 4, 4);
        if (n_verts != expect_verts || b.size() < (size_t)12 + 2 * (size_t)n_verts) return false;
        ao.assign(b.begin() + 12, b.begin() + 12 + n_verts);
        sun.assign(b.begin() + 12 + n_verts, b.begin() + 12 + 2 * n_verts);
        return true;
    }
};

struct VTexture {
    uint32_t offset;
    uint32_t length;
};
#pragma pack(pop)

static_assert(sizeof(VHeader) == 84, "VPK header must stay 84 bytes");
static_assert(sizeof(VDraw) == 100, "VPK draw must stay 100 bytes");

struct VModel {
    VHeader h{};
    std::vector<VDraw> draws;
    std::vector<VTexture> textures;
    std::vector<uint8_t> bytes;   // whole file, owned
    size_t vert_off = 0, idx_off = 0;

    const uint8_t* vertex_base() const { return bytes.data() + vert_off; }
    const uint8_t* index_base() const { return bytes.data() + idx_off; }
    const uint8_t* draw_vertices(const VDraw& d) const {
        return vertex_base() + (size_t)d.vert_offset * VPK_VERTEX_STRIDE;
    }
    const uint16_t* draw_indices(const VDraw& d) const {
        return (const uint16_t*)(index_base() + (size_t)d.index_offset * 2);
    }
    const uint8_t* texture_bytes(uint16_t t) const {
        if (t >= textures.size() || t == VPK_NO_TEXTURE) return nullptr;
        return bytes.data() + textures[t].offset;
    }
    uint32_t texture_length(uint16_t t) const {
        return (t >= textures.size() || t == VPK_NO_TEXTURE) ? 0 : textures[t].length;
    }
    void centre(float out[3]) const {
        for (int i = 0; i < 3; ++i) out[i] = 0.5f * (h.fit_min[i] + h.fit_max[i]);
    }
    float radius() const {
        float m = 1.0f;
        for (int i = 0; i < 3; ++i) m = (h.fit_max[i] - h.fit_min[i]) > m
                                             ? (h.fit_max[i] - h.fit_min[i]) : m;
        return m;
    }
    /// Parse `n` bytes copied into `data`. Returns false and sets `err` on any mismatch -
    /// the viewer prints the reason to logcat instead of drawing garbage.
    bool load(std::vector<uint8_t>&& data, std::string* err);
    bool load_file(const char* path, std::string* err);
};
