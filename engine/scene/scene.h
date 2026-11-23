#pragma once

#include <string>
#include <vector>
#include <map>
#include <cstdint>
#include "ecs/ecs.h"
#include "core/error.h"
#include "core/config.h"

namespace reality {

struct SceneEntityData {
    EntityId id;
    std::string name;
    Transform transform;
    std::map<std::string, std::string> components;  // component type -> JSON string
};

struct SceneData {
    std::string name;
    std::string version = "1.0";
    std::vector<SceneEntityData> entities;
    std::map<std::string, std::string> metadata;
};

class Scene {
public:
    Scene();
    ~Scene();

    Result<void> init(const std::string& name);
    Result<void> shutdown();

    bool is_initialized() const { return initialized_; }
    const std::string& name() const { return name_; }

    // Add entity data to scene
    void add_entity(const SceneEntityData& entity);

    // Get entity data by ID
    const SceneEntityData* find_entity(const EntityId& id) const;

    // Serialize to JSON string
    std::string serialize() const;

    // Deserialize from JSON string
    Result<void> deserialize(const std::string& json);

    // Save to file
    Result<void> save(const std::string& path);

    // Load from file
    Result<void> load(const std::string& path);

    // Validate scene data
    Result<void> validate() const;

    uint32_t entity_count() const { return static_cast<uint32_t>(entities_.size()); }

private:
    std::string name_;
    bool initialized_ = false;
    std::vector<SceneEntityData> entities_;
    std::map<std::string, std::string> metadata_;
};

} // namespace reality
