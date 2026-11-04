#include "vpk.h"

#include <cstdio>
#include <cstring>

bool VModel::load(std::vector<uint8_t>&& data, std::string* err) {
    bytes = std::move(data);
    draws.clear();
    textures.clear();
    vert_off = idx_off = 0;

    if (bytes.size() < sizeof(VHeader)) {
        if (err) *err = "file shorter than the VPK header";
        return false;
    }
    std::memcpy(&h, bytes.data(), sizeof(VHeader));
    if (std::memcmp(h.magic, "VPK1", 4) != 0) {
        if (err) *err = "bad magic (not a VPK1 file - run tools/villa_pack.py)";
        return false;
    }
    if (h.version != 1) {
        if (err) *err = "unsupported VPK version";
        return false;
    }

    const size_t need = sizeof(VHeader) + (size_t)h.n_draws * sizeof(VDraw) +
                        (size_t)h.n_textures * sizeof(VTexture);
    if (h.n_draws == 0 || bytes.size() < need) {
        if (err) *err = "truncated draw/texture table";
        return false;
    }
    draws.resize(h.n_draws);
    std::memcpy(draws.data(), bytes.data() + sizeof(VHeader), draws.size() * sizeof(VDraw));
    textures.resize(h.n_textures);
    std::memcpy(textures.data(), bytes.data() + sizeof(VHeader) + draws.size() * sizeof(VDraw),
                textures.size() * sizeof(VTexture));

    vert_off = need;
    idx_off = vert_off + (size_t)h.n_verts * VPK_VERTEX_STRIDE;
    const size_t blob = idx_off + (size_t)h.n_indices * 2;
    if (bytes.size() < blob) {
        if (err) *err = "truncated vertex/index data";
        return false;
    }

    // validate every draw before the renderer trusts it
    for (size_t i = 0; i < draws.size(); ++i) {
        const VDraw& d = draws[i];
        if ((size_t)d.vert_offset + d.vertex_count > h.n_verts ||
            (size_t)d.index_offset + d.index_count > h.n_indices) {
            if (err) *err = "draw range outside the vertex/index arrays";
            return false;
        }
        if (d.index_count % 3) {
            if (err) *err = "draw index count is not a multiple of 3";
            return false;
        }
    }
    for (size_t i = 0; i < textures.size(); ++i) {
        if ((size_t)textures[i].offset + textures[i].length > bytes.size()) {
            if (err) *err = "texture payload outside the file";
            return false;
        }
    }
    return true;
}

bool VModel::load_file(const char* path, std::string* err) {
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
        if (err) *err = "empty file";
        return false;
    }
    std::vector<uint8_t> data((size_t)n);
    size_t got = std::fread(data.data(), 1, data.size(), f);
    std::fclose(f);
    if (got != data.size()) {
        if (err) *err = "short read";
        return false;
    }
    return load(std::move(data), err);
}
