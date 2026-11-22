#pragma once

#include <string>
#include "core/error.h"

namespace reality {

// glTF 2.0 loader interface
// Phase 1: stub/interface only. Full glTF parsing planned for Phase 2.
class GltfLoader {
public:
    GltfLoader() = default;
    ~GltfLoader() = default;

    // Load a glTF file (Phase 1: returns UNSUPPORTED)
    Result<void> load(const std::string& path) {
        return Result<void>(Error{ErrorCode::UNSUPPORTED,
                               "glTF loader not yet implemented (Phase 2)",
                               "gltf_loader.h:GltfLoader::load"});
    }

    // Check if a file is a valid glTF (Phase 1: checks extension only)
    bool is_gltf(const std::string& path) const {
        return path.size() >= 5 &&
               (path.substr(path.size() - 5) == ".gltf" ||
                path.substr(path.size() - 4) == ".glb");
    }
};

} // namespace reality
