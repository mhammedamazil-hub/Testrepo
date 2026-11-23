#include "asset_manager.h"
#include "core/logging.h"
#include <fstream>

namespace reality {

AssetManager::AssetManager() = default;
AssetManager::~AssetManager() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> AssetManager::init(const std::string& assets_dir) {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "AssetManager already initialized",
                               "asset_manager.cpp:AssetManager::init"});
    }

    assets_dir_ = assets_dir;
    initialized_ = true;
    REALITY_LOG(INFO, "AssetManager: initialized with dir " + assets_dir_);
    return Result<void>();
}

Result<void> AssetManager::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "AssetManager not initialized",
                               "asset_manager.cpp:AssetManager::shutdown"});
    }

    assets_.clear();
    initialized_ = false;
    return Result<void>();
}

Result<void> AssetManager::register_asset(const std::string& id,
                                           const std::string& path,
                                           const std::string& type) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "AssetManager not initialized",
                               "asset_manager.cpp:AssetManager::register_asset"});
    }

    AssetRecord record;
    record.id = id;
    record.path = path;
    record.type = type;
    record.size_bytes = 0;

    // Check if file exists
    std::ifstream test_file(path);
    if (test_file.good()) {
        test_file.seekg(0, std::ios::end);
        record.size_bytes = static_cast<size_t>(test_file.tellg());
        test_file.close();
    }

    assets_[id] = record;
    REALITY_LOG(DEBUG, "AssetManager: registered asset " + id + " (" + type + ")");
    return Result<void>();
}

Result<void> AssetManager::load_asset(const std::string& id) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "AssetManager not initialized",
                               "asset_manager.cpp:AssetManager::load_asset"});
    }

    auto it = assets_.find(id);
    if (it == assets_.end()) {
        return Result<void>(Error{ErrorCode::ASSET_NOT_FOUND,
                               "Asset not registered: " + id,
                               "asset_manager.cpp:AssetManager::load_asset"});
    }

    it->second.loaded = true;
    REALITY_LOG(INFO, "AssetManager: loaded asset " + id);
    return Result<void>();
}

bool AssetManager::is_loaded(const std::string& id) const {
    auto it = assets_.find(id);
    if (it == assets_.end()) return false;
    return it->second.loaded;
}

std::string AssetManager::get_path(const std::string& id) const {
    auto it = assets_.find(id);
    if (it == assets_.end()) return "";
    return it->second.path;
}

std::string AssetManager::get_type(const std::string& id) const {
    auto it = assets_.find(id);
    if (it == assets_.end()) return "";
    return it->second.type;
}

std::vector<AssetRecord> AssetManager::list_assets() const {
    std::vector<AssetRecord> result;
    for (const auto& [id, record] : assets_) {
        result.push_back(record);
    }
    return result;
}

bool AssetManager::asset_exists(const std::string& id) const {
    auto it = assets_.find(id);
    if (it == assets_.end()) return false;
    std::ifstream test_file(it->second.path);
    return test_file.good();
}

} // namespace reality
