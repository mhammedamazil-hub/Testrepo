#pragma once

#include <string>
#include <memory>
#include "ecs/ecs.h"
#include "core/error.h"

namespace reality {

class World {
public:
    World();
    ~World();

    Result<void> init(const std::string& name);
    Result<void> shutdown();

    bool is_initialized() const { return initialized_; }
    const std::string& name() const { return name_; }

    Registry& registry() { return registry_; }
    const Registry& registry() const { return registry_; }

    Entity create_entity(const std::string& name = "");
    Entity create_entity_with_id(const EntityId& id, const std::string& name = "");
    void destroy_entity(Entity entity);

    uint32_t entity_count() const { return registry_.entity_count(); }

private:
    std::string name_;
    bool initialized_ = false;
    Registry registry_;
};

} // namespace reality
