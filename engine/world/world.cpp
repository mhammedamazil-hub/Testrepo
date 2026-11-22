#include "world.h"
#include "core/logging.h"

namespace reality {

World::World() = default;
World::~World() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> World::init(const std::string& name) {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "World already initialized",
                               "world.cpp:World::init"});
    }

    name_ = name;
    initialized_ = true;

    REALITY_LOG(INFO, "World: initialized '" + name + "'");
    return Result<void>();
}

Result<void> World::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "World not initialized",
                               "world.cpp:World::shutdown"});
    }

    // Destroy all entities
    // Note: We iterate a copy since destroy_entity modifies the alive array
    for (Entity e = 1; e < registry_.entity_count() + 1; e++) {
        if (registry_.is_alive(e)) {
            registry_.destroy_entity(e);
        }
    }

    initialized_ = false;
    REALITY_LOG(INFO, "World: shutdown complete");
    return Result<void>();
}

Entity World::create_entity(const std::string& name) {
    Entity entity = registry_.create_entity();
    if (!name.empty()) {
        registry_.add_component<Name>(entity, Name{name});
    }
    registry_.add_component<Transform>(entity, Transform{});
    return entity;
}

Entity World::create_entity_with_id(const EntityId& id, const std::string& name) {
    Entity entity = registry_.create_entity_with_id(id);
    if (!name.empty()) {
        registry_.add_component<Name>(entity, Name{name});
    }
    registry_.add_component<Transform>(entity, Transform{});
    return entity;
}

void World::destroy_entity(Entity entity) {
    registry_.destroy_entity(entity);
}

} // namespace reality
