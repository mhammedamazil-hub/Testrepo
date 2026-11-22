#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <memory>
#include <functional>
#include <typeindex>
#include <typeinfo>
#include <random>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <algorithm>

#include "error.h"
#include "logging.h"

namespace reality {

class Registry;

struct ComponentBase {
    virtual ~ComponentBase() = default;
};

using Entity = uint32_t;
static constexpr Entity NULL_ENTITY = 0xFFFFFFFF;

using ComponentType = uint16_t;

class ComponentArray {
public:
    virtual ~ComponentArray() = default;
    virtual void entity_destroyed(Entity entity) = 0;
    virtual std::type_index type_index() const = 0;
};

template <typename T>
class TypedComponentArray : public ComponentArray {
public:
    void insert(Entity entity, T component) {
        components_[entity] = std::move(component);
    }

    void remove(Entity entity) {
        components_.erase(entity);
    }

    T* get(Entity entity) {
        auto it = components_.find(entity);
        if (it == components_.end()) return nullptr;
        return &it->second;
    }

    const T* get(Entity entity) const {
        auto it = components_.find(entity);
        if (it == components_.end()) return nullptr;
        return &it->second;
    }

    bool has(Entity entity) const {
        return components_.find(entity) != components_.end();
    }

    void entity_destroyed(Entity entity) override {
        remove(entity);
    }

    std::type_index type_index() const override {
        return typeid(T);
    }

    class Iterator {
    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = std::pair<Entity, T>;

        Iterator(typename std::unordered_map<Entity, T>::iterator it) : it_(it) {}

        bool operator==(const Iterator& other) const { return it_ == other.it_; }
        bool operator!=(const Iterator& other) const { return it_ != other.it_; }

        Iterator& operator++() { ++it_; return *this; }
        value_type operator*() { return {it_->first, it_->second}; }

    private:
        typename std::unordered_map<Entity, T>::iterator it_;
    };

    Iterator begin() { return Iterator(components_.begin()); }
    Iterator end() { return Iterator(components_.end()); }

    using MapIterator = typename std::unordered_map<Entity, T>::iterator;
    MapIterator map_begin() { return components_.begin(); }
    MapIterator map_end() { return components_.end(); }

    size_t size() const { return components_.size(); }

private:
    std::unordered_map<Entity, T> components_;
};

class System {
public:
    virtual ~System() = default;
    virtual void update(Registry& registry, double dt) = 0;
    virtual const char* name() const = 0;
};

struct EntityId {
    unsigned char data[16];

    bool operator==(const EntityId& other) const {
        return memcmp(data, other.data, 16) == 0;
    }

    bool operator!=(const EntityId& other) const {
        return !(*this == other);
    }

    bool is_null() const {
        for (int i = 0; i < 16; i++) {
            if (data[i] != 0) return false;
        }
        return true;
    }

    std::string to_string() const {
        char buf[37];
        snprintf(buf, sizeof(buf), "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
                 data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
                 data[8], data[9], data[10], data[11], data[12], data[13], data[14], data[15]);
        return std::string(buf);
    }

    static EntityId generate();
    static EntityId from_string(const std::string& str);
};

struct Metadata : public ComponentBase {
    EntityId id;
    std::string created_at;
    int version = 1;
};

struct Name : public ComponentBase {
    std::string value;
    Name() = default;
    explicit Name(const char* v) : value(v) {}
    explicit Name(const std::string& v) : value(v) {}
};

struct Transform : public ComponentBase {
    float position[3] = {0.0f, 0.0f, 0.0f};
    float rotation[4] = {0.0f, 0.0f, 0.0f, 1.0f};
    float scale[3] = {1.0f, 1.0f, 1.0f};
    Entity parent = NULL_ENTITY;
};

class Registry {
public:
    Registry();
    ~Registry();

    Entity create_entity();
    Entity create_entity_with_id(const EntityId& id);
    void destroy_entity(Entity entity);
    bool is_alive(Entity entity) const;
    uint32_t entity_count() const { return next_entity_ - 1; }

    template <typename T>
    T* add_component(Entity entity, T component) {
        if (!is_alive(entity)) {
            REALITY_LOG(WARN, "ECS: cannot add component to dead entity " + std::to_string(entity));
            return nullptr;
        }
        auto& arr = get_or_create_array<T>();
        arr.insert(entity, std::move(component));
        return arr.get(entity);
    }

    template <typename T>
    T* get_component(Entity entity) {
        auto* arr = component_array<T>();
        if (!arr) return nullptr;
        return arr->get(entity);
    }

    template <typename T>
    const T* get_component(Entity entity) const {
        auto* arr = component_array<T>();
        if (!arr) return nullptr;
        return arr->get(entity);
    }

    template <typename T>
    bool has_component(Entity entity) const {
        auto* arr = component_array<T>();
        if (!arr) return false;
        return arr->has(entity);
    }

    template <typename T>
    void remove_component(Entity entity) {
        auto* arr = component_array<T>();
        if (arr) arr->remove(entity);
    }

    void add_system(std::unique_ptr<System> system);
    void update_systems(double dt);

    void register_entity_id(Entity entity, const EntityId& id);
    EntityId get_entity_id(Entity entity) const;
    Entity get_entity_by_id(const EntityId& id) const;
    bool has_entity_id(Entity entity) const;

    template <typename T1, typename T2>
    class View {
    public:
        View(Registry* reg) : reg_(reg) {}

        class Iterator {
        public:
            using iterator_category = std::forward_iterator_tag;
            using value_type = std::pair<Entity, std::pair<T1*, T2*>>;

            Iterator(typename std::unordered_map<Entity, T1>::iterator it,
                     typename std::unordered_map<Entity, T1>::iterator end,
                     Registry* reg)
                : it_(it), end_(end), reg_(reg) {
                    advance_to_valid();
                }

            bool operator==(const Iterator& other) const { return it_ == other.it_; }
            bool operator!=(const Iterator& other) const { return it_ != other.it_; }

            Iterator& operator++() {
                ++it_;
                advance_to_valid();
                return *this;
            }

            value_type operator*() {
                Entity e = it_->first;
                return {e, {&it_->second, reg_->get_component<T2>(e)}};
            }

        private:
            void advance_to_valid() {
                while (it_ != end_ && !reg_->has_component<T2>(it_->first)) {
                    ++it_;
                }
            }

            typename std::unordered_map<Entity, T1>::iterator it_;
            typename std::unordered_map<Entity, T1>::iterator end_;
            Registry* reg_;
        };

        Iterator begin() {
            auto* arr = reg_->template component_array<T1>();
            if (!arr) {
                static std::unordered_map<Entity, T1> empty;
                return Iterator(empty.end(), empty.end(), reg_);
            }
            return Iterator(arr->map_begin(), arr->map_end(), reg_);
        }

        Iterator end() {
            auto* arr = reg_->template component_array<T1>();
            if (!arr) {
                static std::unordered_map<Entity, T1> empty;
                return Iterator(empty.end(), empty.end(), reg_);
            }
            return Iterator(arr->map_end(), arr->map_end(), reg_);
        }

    private:
        Registry* reg_;
    };

    template <typename T1, typename T2>
    View<T1, T2> view() {
        return View<T1, T2>(this);
    }

private:
    std::unordered_map<std::type_index, std::unique_ptr<ComponentArray>> component_arrays_;
    std::unordered_map<Entity, EntityId> entity_to_id_;
    std::unordered_map<std::string, Entity> id_to_entity_;
    std::vector<bool> entity_alive_;
    Entity next_entity_ = 1;
    std::vector<std::unique_ptr<System>> systems_;

    template <typename T>
    TypedComponentArray<T>& get_or_create_array() {
        auto ti = std::type_index(typeid(T));
        auto it = component_arrays_.find(ti);
        if (it != component_arrays_.end()) {
            return *static_cast<TypedComponentArray<T>*>(it->second.get());
        }
        auto arr = std::make_unique<TypedComponentArray<T>>();
        auto* ptr = arr.get();
        component_arrays_[ti] = std::move(arr);
        return *ptr;
    }

    template <typename T>
    TypedComponentArray<T>* component_array() {
        auto ti = std::type_index(typeid(T));
        auto it = component_arrays_.find(ti);
        if (it == component_arrays_.end()) return nullptr;
        return static_cast<TypedComponentArray<T>*>(it->second.get());
    }

    template <typename T>
    const TypedComponentArray<T>* component_array() const {
        auto ti = std::type_index(typeid(T));
        auto it = component_arrays_.find(ti);
        if (it == component_arrays_.end()) return nullptr;
        return static_cast<const TypedComponentArray<T>*>(it->second.get());
    }

    void ensure_entity_capacity(Entity entity);
};

} // namespace reality

namespace std {
template <>
struct hash<reality::EntityId> {
    size_t operator()(const reality::EntityId& id) const {
        size_t h = 0;
        for (int i = 0; i < 16; i++) {
            h = h * 31 + id.data[i];
        }
        return h;
    }
};
} // namespace std
