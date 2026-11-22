#include "ecs.h"
#include <cstdio>
#include <cstring>
#include <random>
#include <chrono>
#include <fstream>

namespace reality {

EntityId EntityId::generate() {
    EntityId id;

    std::ifstream urandom("/dev/urandom", std::ios::binary);
    if (urandom.is_open()) {
        urandom.read(reinterpret_cast<char*>(id.data), 16);
        urandom.close();
        id.data[6] = (id.data[6] & 0x0F) | 0x40;
        id.data[8] = (id.data[8] & 0x3F) | 0x80;
        return id;
    }

    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    uint64_t part1 = rng();
    uint64_t part2 = rng();
    memcpy(id.data, &part1, 8);
    memcpy(id.data + 8, &part2, 8);

    id.data[6] = (id.data[6] & 0x0F) | 0x40;
    id.data[8] = (id.data[8] & 0x3F) | 0x80;

    return id;
}

EntityId EntityId::from_string(const std::string& str) {
    EntityId id;
    memset(id.data, 0, 16);

    if (str.size() < 32) return id;

    for (int i = 0; i < 16; i++) {
        int pos = i * 2;
        int adjusted = pos;
        if (pos >= 8) adjusted++;
        if (pos >= 13) adjusted++;
        if (pos >= 18) adjusted++;
        if (pos >= 23) adjusted++;
        if (adjusted + 1 >= (int)str.size()) break;

        unsigned int byte_val = 0;
        sscanf(str.c_str() + adjusted, "%2x", &byte_val);
        id.data[i] = static_cast<unsigned char>(byte_val);
    }

    return id;
}

Registry::Registry() = default;
Registry::~Registry() = default;

Entity Registry::create_entity() {
    Entity entity = next_entity_++;
    ensure_entity_capacity(entity);
    entity_alive_[entity] = true;
    REALITY_LOG(DEBUG, "ECS: created entity " + std::to_string(entity));
    return entity;
}

Entity Registry::create_entity_with_id(const EntityId& id) {
    Entity entity = create_entity();
    register_entity_id(entity, id);
    return entity;
}

void Registry::destroy_entity(Entity entity) {
    if (!is_alive(entity)) return;

    for (auto& [type, array] : component_arrays_) {
        array->entity_destroyed(entity);
    }

    if (has_entity_id(entity)) {
        auto eid = get_entity_id(entity);
        id_to_entity_.erase(eid.to_string());
        entity_to_id_.erase(entity);
    }

    entity_alive_[entity] = false;
    REALITY_LOG(DEBUG, "ECS: destroyed entity " + std::to_string(entity));
}

bool Registry::is_alive(Entity entity) const {
    if (entity >= entity_alive_.size()) return false;
    return entity_alive_[entity];
}

void Registry::ensure_entity_capacity(Entity entity) {
    if (entity >= entity_alive_.size()) {
        entity_alive_.resize(entity + 1, false);
    }
}

void Registry::add_system(std::unique_ptr<System> system) {
    systems_.push_back(std::move(system));
}

void Registry::update_systems(double dt) {
    for (auto& system : systems_) {
        system->update(*this, dt);
    }
}

void Registry::register_entity_id(Entity entity, const EntityId& id) {
    entity_to_id_[entity] = id;
    id_to_entity_[id.to_string()] = entity;
}

EntityId Registry::get_entity_id(Entity entity) const {
    auto it = entity_to_id_.find(entity);
    if (it != entity_to_id_.end()) return it->second;
    return EntityId{};
}

Entity Registry::get_entity_by_id(const EntityId& id) const {
    auto it = id_to_entity_.find(id.to_string());
    if (it != id_to_entity_.end()) return it->second;
    return NULL_ENTITY;
}

bool Registry::has_entity_id(Entity entity) const {
    return entity_to_id_.find(entity) != entity_to_id_.end();
}

template class Registry::View<Name, Transform>;
template class Registry::View<Transform, Metadata>;

} // namespace reality
