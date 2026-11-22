#pragma once

#include <string>
#include "ecs/ecs.h"
#include "core/error.h"

namespace reality {

enum class BodyType {
    Static,
    Dynamic,
    Kinematic,
};

enum class ColliderShape {
    Box,
    Sphere,
    Capsule,
};

struct RigidBody : public ComponentBase {
    BodyType type = BodyType::Dynamic;
    float mass = 1.0f;
    float friction = 0.5f;
    float restitution = 0.0f;
    bool gravity_enabled = true;
    bool is_awake = true;
};

struct Collider : public ComponentBase {
    ColliderShape shape = ColliderShape::Box;
    float size[3] = {1.0f, 1.0f, 1.0f};  // for box: half-extents
    float radius = 0.5f;                  // for sphere/capsule
    float height = 1.0f;                  // for capsule
    uint32_t collision_layer = 1;
    uint32_t collision_mask = 0xFFFFFFFF;
};

} // namespace reality
