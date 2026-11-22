#pragma once

#include <string>
#include <map>
#include <memory>
#include <vector>
#include "core/error.h"
#include "core/config.h"

namespace reality {

struct AssetRecord {
    std::string id;
    std::string path;
    std::string type;  // mesh, material, texture, audio, etc.
    bool loaded = false;
    size_t size_bytes = 0;
};

class AssetManager {
public:
    AssetManager();
    ~AssetManager();

    Result<void> init(const std::string& assets_dir);
    Result<void> shutdown();

    // Register an asset
    Result<void> register_asset(const std::string& id,
                                 const std::string& path,
                                 const std::string& type);

    // Load an asset
    Result<void> load_asset(const std::string& id);

    // Check if asset is loaded
    bool is_loaded(const std::string& id) const;

    // Get asset path
    std::string get_path(const std::string& id) const;

    // Get asset type
    std::string get_type(const std::string& id) const;

    // List all assets
    std::vector<AssetRecord> list_assets() const;

    // Check if asset exists (file on disk)
    bool asset_exists(const std::string& id) const;

private:
    std::string assets_dir_;
    bool initialized_ = false;
    std::map<std::string, AssetRecord> assets_;
};

} // namespace reality
