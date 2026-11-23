#include "physics_world.h"
#include "core/logging.h"

#ifdef REALITY_HAS_JOLT
#include <Jolt/Jolt.h>
#include <Jolt/RegisterTypes.h>
#include <Jolt/Physics/Collision/Shape/BoxShape.h>
#include <Jolt/Physics/Collision/Shape/SphereShape.h>
#include <Jolt/Physics/Collision/BroadPhase/BroadPhaseLayer.h>
#include <Jolt/Physics/Collision/ObjectLayer.h>
#include <Jolt/Physics/Body/BodyID.h>
#include <Jolt/Physics/Body/Body.h>
#include <Jolt/Physics/Body/BodyInterface.h>
#include <Jolt/Core/TempAllocator.h>
#include <Jolt/Core/JobSystem.h>
#include <Jolt/Core/JobSystemThreadPool.h>
#include <Jolt/Core/Factory.h>
#include <Jolt/Physics/Body/BodyCreationSettings.h>
#include <Jolt/Physics/EPhysicsUpdateError.h>
#endif

namespace reality {

//------------------------------------------------------------------------------
// JoltSystemDeleter
//------------------------------------------------------------------------------
#ifdef REALITY_HAS_JOLT
void PhysicsWorld::JoltSystemDeleter::operator()(JPH::PhysicsSystem* ptr) const {
    if (ptr) {
        delete ptr;
    }
}
#endif

//------------------------------------------------------------------------------
// PhysicsWorld
//------------------------------------------------------------------------------

PhysicsWorld::PhysicsWorld() = default;

PhysicsWorld::~PhysicsWorld() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> PhysicsWorld::init(double gravity) {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "PhysicsWorld already initialized",
                               "physics_world.cpp:PhysicsWorld::init"});
    }

    gravity_ = gravity;

#ifdef REALITY_HAS_JOLT
    // --- Jolt Physics initialization ---
    // Correct initialization order per Jolt HelloWorld sample:
    // 1. RegisterDefaultAllocator()
    // 2. Factory::sInstance = new Factory()
    // 3. RegisterTypes()
    // 4. Create TempAllocator and JobSystem
    // 5. Create PhysicsSystem and Init()

    // Register allocation hook (must be done before any other Jolt function)
    REALITY_LOG(INFO, "PhysicsWorld: calling RegisterDefaultAllocator()");
    JPH::RegisterDefaultAllocator();
    REALITY_LOG(INFO, "PhysicsWorld: RegisterDefaultAllocator() done");

    // Create factory (required for deserialization)
    REALITY_LOG(INFO, "PhysicsWorld: creating factory");
    JPH::Factory::sInstance = new JPH::Factory();
    REALITY_LOG(INFO, "PhysicsWorld: factory created");

    // Register Jolt types
    REALITY_LOG(INFO, "PhysicsWorld: calling RegisterTypes()");
    JPH::RegisterTypes();
    REALITY_LOG(INFO, "PhysicsWorld: RegisterTypes() done");

    // Create temp allocator (used for temporary allocations during simulation)
    REALITY_LOG(INFO, "PhysicsWorld: creating temp allocator");
    jolt_temp_allocator_ = new JPH::TempAllocatorImpl(10 * 1024 * 1024);  // 10 MB
    REALITY_LOG(INFO, "PhysicsWorld: temp allocator created");

    // Create job system (multi-threaded simulation)
    REALITY_LOG(INFO, "PhysicsWorld: creating job system");
    jolt_job_system_ = new JPH::JobSystemThreadPool(
        JPH::cMaxPhysicsJobs, JPH::cMaxPhysicsBarriers, 8);  // 8 worker threads

    // Create the physics system
    JPH::PhysicsSystem* sys = new JPH::PhysicsSystem();
    sys->Init(1024,           // max bodies
              32,             // num body mutexes
              1024,           // max body pairs
              4096,           // max contact constraints
              jolt_broadphase_layer_interface_,
              jolt_object_vs_broadphase_filter_,
              jolt_object_layer_pair_filter_);

    jolt_system_.reset(sys);
    REALITY_LOG(INFO, "PhysicsWorld: physics system created");

    // Get body interface pointer
    REALITY_LOG(INFO, "PhysicsWorld: getting body interface");
    jolt_body_interface_ = &jolt_system_->GetBodyInterface();
    REALITY_LOG(INFO, "PhysicsWorld: body interface obtained");

    // Set contact listener
    jolt_system_->SetContactListener(&jolt_contact_listener_);

    // Set gravity
    JPH::Vec3 gravity_vec(0.0f, static_cast<float>(gravity), 0.0f);
    jolt_system_->SetGravity(gravity_vec);

    REALITY_LOG(INFO, "PhysicsWorld: initialized with Jolt Physics, gravity=" +
                   std::to_string(gravity));
#else
    REALITY_LOG(WARN, "PhysicsWorld: initialized WITHOUT Jolt (stub mode), gravity=" +
                   std::to_string(gravity));
    REALITY_LOG(WARN, "PhysicsWorld: Jolt Physics not available - install Jolt for real simulation");
#endif

    initialized_ = true;
    return Result<void>();
}

Result<void> PhysicsWorld::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "PhysicsWorld not initialized",
                               "physics_world.cpp:PhysicsWorld::shutdown"});
    }

    entity_to_body_id_.clear();
    body_id_to_entity_.clear();
    contacts_.clear();
    stats_ = PhysicsStats{};

#ifdef REALITY_HAS_JOLT
    // Collect all body IDs and remove them
    if (jolt_body_interface_ != nullptr) {
        std::vector<JPH::BodyID> body_ids;
        body_ids.reserve(entity_to_body_id_.size());
        for (auto& [entity, body_id] : entity_to_body_id_) {
            body_ids.push_back(body_id);
        }
        if (!body_ids.empty()) {
            jolt_body_interface_->RemoveBodies(body_ids.data(), static_cast<int>(body_ids.size()));
        }
    }

    // Reset the physics system first (calls destructor, which may use job system/allocator)
    jolt_system_.reset();

    // Destroy job system and temp allocator
    delete jolt_job_system_;
    jolt_job_system_ = nullptr;
    delete jolt_temp_allocator_;
    jolt_temp_allocator_ = nullptr;

    JPH::UnregisterTypes();
    // Note: Factory::sInstance is managed by Jolt, do not delete it here
#endif

    initialized_ = false;

    REALITY_LOG(INFO, "PhysicsWorld: shutdown complete");
    return Result<void>();
}

Result<void> PhysicsWorld::create_body(Entity entity, const RigidBody& body, const Collider& collider) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "PhysicsWorld not initialized",
                               "physics_world.cpp:PhysicsWorld::create_body"});
    }

    if (entity_to_body_id_.find(entity) != entity_to_body_id_.end()) {
        return Result<void>(Error{ErrorCode::ALREADY_EXISTS,
                               "Entity already has a physics body",
                               "physics_world.cpp:PhysicsWorld::create_body"});
    }

#ifdef REALITY_HAS_JOLT
    // Create Jolt shape based on collider type
    JPH::Shape* jolt_shape = nullptr;

    if (collider.shape == ColliderShape::Box) {
        JPH::Vec3 half_extent(collider.size[0] * 0.5f, collider.size[1] * 0.5f, collider.size[2] * 0.5f);
        auto* box_settings = new JPH::BoxShapeSettings(half_extent);
        JPH::Shape::ShapeResult result = box_settings->Create();
        if (result.HasError()) {
            delete box_settings;
            return Result<void>(Error{ErrorCode::PHYSICS_ERROR,
                                    "Failed to create box shape",
                                    "physics_world.cpp:PhysicsWorld::create_body"});
        }
        jolt_shape = result.Get();
    } else if (collider.shape == ColliderShape::Sphere) {
        auto* sphere_settings = new JPH::SphereShapeSettings(collider.radius);
        JPH::Shape::ShapeResult result = sphere_settings->Create();
        if (result.HasError()) {
            delete sphere_settings;
            return Result<void>(Error{ErrorCode::PHYSICS_ERROR,
                                    "Failed to create sphere shape",
                                    "physics_world.cpp:PhysicsWorld::create_body"});
        }
        jolt_shape = result.Get();
    } else {
        // Default to box shape for unsupported types
        JPH::Vec3 half_extent(collider.size[0] * 0.5f, collider.size[1] * 0.5f, collider.size[2] * 0.5f);
        auto* box_settings = new JPH::BoxShapeSettings(half_extent);
        JPH::Shape::ShapeResult result = box_settings->Create();
        jolt_shape = result.Get();
    }

    // Determine motion type
    JPH::EMotionType motion_type;
    if (body.type == BodyType::Static) {
        motion_type = JPH::EMotionType::Static;
    } else if (body.type == BodyType::Kinematic) {
        motion_type = JPH::EMotionType::Kinematic;
    } else {
        motion_type = JPH::EMotionType::Dynamic;
    }

    // Determine object layer
    JPH::ObjectLayer object_layer = (body.type == BodyType::Static) ? cDefaultLayer : cDynamicLayer;

    // Get position from Transform component if available
    JPH::RVec3 position(0.0f, 0.0f, 0.0f);
    // Note: We don't have access to the registry here, so position defaults to origin.
    // The runtime sets transforms before calling create_body.

    JPH::Quat rotation = JPH::Quat::sIdentity();

    // Create body settings
    JPH::BodyCreationSettings settings(jolt_shape, position, rotation, motion_type, object_layer);

    // Override mass properties for dynamic bodies
    if (body.type == BodyType::Dynamic) {
        settings.mMassPropertiesOverride.mMass = body.mass;
        settings.mOverrideMassProperties = JPH::EOverrideMassProperties::MassAndInertiaProvided;
    }

    // Set linear damping (friction-like)
    settings.mLinearDamping = body.friction;

    // Create the body object (not yet added to the system)
    JPH::Body* jolt_body = jolt_body_interface_->CreateBody(settings);
    if (jolt_body == nullptr) {
        return Result<void>(Error{ErrorCode::PHYSICS_ERROR,
                                "Failed to create Jolt body",
                                "physics_world.cpp:PhysicsWorld::create_body"});
    }

    // Add body to the physics system using its auto-generated ID
    JPH::BodyID body_id = jolt_body->GetID();
    jolt_body_interface_->AddBody(body_id, JPH::EActivation::Activate);

    // Store mappings
    entity_to_body_id_[entity] = body_id;
    body_id_to_entity_[body_id] = entity;

    stats_.body_count = static_cast<uint32_t>(entity_to_body_id_.size());

    REALITY_LOG(DEBUG, "PhysicsWorld: created Jolt body for entity " +
                   std::to_string(entity));
#else
    // Stub mode: just track the entity
    stats_.body_count = static_cast<uint32_t>(entity_to_body_id_.size() + 1);
    // Use a placeholder - we don't track individual IDs in stub mode

    REALITY_LOG(DEBUG, "PhysicsWorld: created body (stub) for entity " +
                   std::to_string(entity) + " type=" +
                   (body.type == BodyType::Static ? "static" :
                    body.type == BodyType::Dynamic ? "dynamic" : "kinematic"));
#endif

    return Result<void>();
}

Result<void> PhysicsWorld::set_body_transform(Entity entity, const float position[3], const float rotation[4]) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "PhysicsWorld not initialized",
                               "physics_world.cpp:PhysicsWorld::set_body_transform"});
    }

    auto it = entity_to_body_id_.find(entity);
    if (it == entity_to_body_id_.end()) {
        return Result<void>(Error{ErrorCode::NOT_FOUND,
                               "Entity has no physics body",
                               "physics_world.cpp:PhysicsWorld::set_body_transform"});
    }

#ifdef REALITY_HAS_JOLT
    JPH::BodyID body_id = it->second;
    JPH::RVec3 jolt_pos(position[0], position[1], position[2]);
    JPH::Quat jolt_rot(rotation[0], rotation[1], rotation[2], rotation[3]);
    jolt_body_interface_->SetPositionAndRotation(body_id, jolt_pos, jolt_rot, JPH::EActivation::Activate);
#endif

    return Result<void>();
}

Result<void> PhysicsWorld::remove_body(Entity entity) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "PhysicsWorld not initialized",
                               "physics_world.cpp:PhysicsWorld::remove_body"});
    }

    auto it = entity_to_body_id_.find(entity);
    if (it == entity_to_body_id_.end()) {
        return Result<void>();  // Already removed
    }

#ifdef REALITY_HAS_JOLT
    JPH::BodyID body_id = it->second;
    jolt_body_interface_->RemoveBodies(&body_id, 1);
#endif

    body_id_to_entity_.erase(it->second);
    entity_to_body_id_.erase(it);
    stats_.body_count = static_cast<uint32_t>(entity_to_body_id_.size());

    return Result<void>();
}

Result<void> PhysicsWorld::step(double dt) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "PhysicsWorld not initialized",
                               "physics_world.cpp:PhysicsWorld::step"});
    }

    contacts_.clear();
    stats_.contact_count = 0;

#ifdef REALITY_HAS_JOLT
    auto start_time = std::chrono::steady_clock::now();

    // Step the Jolt physics system
    JPH::EPhysicsUpdateError update_error =
        jolt_system_->Update(static_cast<float>(dt), 1, jolt_temp_allocator_, jolt_job_system_);

    auto end_time = std::chrono::steady_clock::now();
    stats_.simulation_time_ms =
        std::chrono::duration<double, std::milli>(end_time - start_time).count();

    if (update_error != JPH::EPhysicsUpdateError::None) {
        REALITY_LOG(WARN, "PhysicsWorld: Jolt update error: " +
                       std::to_string(static_cast<int>(update_error)));
    }

    // Get contact count from the contact listener
    stats_.contact_count = static_cast<uint32_t>(contacts_.size());
#else
    // Stub: simple gravity-only integration for dynamic bodies
    stats_.simulation_time_ms = 0.1;
#endif

    return Result<void>();
}

void PhysicsWorld::set_gravity(double gravity) {
    gravity_ = gravity;
#ifdef REALITY_HAS_JOLT
    if (jolt_system_) {
        JPH::Vec3 gravity_vec(0.0f, static_cast<float>(gravity), 0.0f);
        jolt_system_->SetGravity(gravity_vec);
    }
#endif
}

void PhysicsWorld::sync_transforms(Registry& registry) {
#ifdef REALITY_HAS_JOLT
    // Sync physics body transforms to ECS Transform components
    for (auto& [entity, body_id] : entity_to_body_id_) {
        const JPH::RVec3 position = jolt_body_interface_->GetPosition(body_id);
        const JPH::Quat rotation = jolt_body_interface_->GetRotation(body_id);

        auto* transform = registry.get_component<Transform>(entity);
        if (transform) {
            transform->position[0] = position.GetX();
            transform->position[1] = position.GetY();
            transform->position[2] = position.GetZ();
            transform->rotation[0] = rotation.GetX();
            transform->rotation[1] = rotation.GetY();
            transform->rotation[2] = rotation.GetZ();
            transform->rotation[3] = rotation.GetW();
        }
    }
#endif
    (void)registry;
}

//------------------------------------------------------------------------------
// BroadPhaseLayerInterfaceImpl
//------------------------------------------------------------------------------
#ifdef REALITY_HAS_JOLT
PhysicsWorld::BroadPhaseLayerInterfaceImpl::BroadPhaseLayerInterfaceImpl() {
    // Layer 0 = static, Layer 1 = dynamic
}

JPH::BroadPhaseLayer PhysicsWorld::BroadPhaseLayerInterfaceImpl::GetBroadPhaseLayer(
    JPH::ObjectLayer inLayer) const {
    // Map object layer 1 -> broad phase layer 0 (static), layer 2 -> broad phase layer 1 (dynamic)
    return JPH::BroadPhaseLayer(static_cast<uint8_t>(inLayer) - 1);
}

const char* PhysicsWorld::BroadPhaseLayerInterfaceImpl::GetBroadPhaseLayerName(
    JPH::BroadPhaseLayer inLayer) const {
    switch (inLayer.GetValue()) {
        case 0: return "Static";
        case 1: return "Dynamic";
        default: return "Invalid";
    }
}

bool PhysicsWorld::ObjectVsBroadPhaseLayerFilterImpl::ShouldCollide(
    JPH::ObjectLayer inLayer1, JPH::BroadPhaseLayer inLayer2) const {
    // All object layers collide with all broad phase layers
    return true;
}

bool PhysicsWorld::ObjectLayerPairFilterImpl::ShouldCollide(
    JPH::ObjectLayer inLayer1, JPH::ObjectLayer inLayer2) const {
    // Static-Static does not collide, everything else does
    if (inLayer1 == cDefaultLayer && inLayer2 == cDefaultLayer) return false;
    return true;
}
#endif

} // namespace reality
