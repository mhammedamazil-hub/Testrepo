#pragma once

#include <string>
#include <vector>
#include <map>
#include "core/error.h"
#include "ecs/ecs.h"
#include "physics/physics_body.h"

#ifdef REALITY_HAS_JOLT
#include <Jolt/Jolt.h>
#include <Jolt/Physics/PhysicsSystem.h>
#include <Jolt/Physics/Body/BodyInterface.h>
#include <Jolt/Physics/Body/Body.h>
#include <Jolt/Physics/Collision/ContactListener.h>
#include <Jolt/Physics/Collision/BroadPhase/BroadPhaseLayer.h>
#include <Jolt/Physics/Collision/ObjectLayer.h>
#include <Jolt/Physics/Body/BodyID.h>
#include <Jolt/Core/TempAllocator.h>
#include <Jolt/Core/JobSystem.h>
#include <Jolt/Core/JobSystemThreadPool.h>
#endif

namespace reality {

struct ContactEvent {
    Entity entity_a;
    Entity entity_b;
    float impulse;
};

struct PhysicsStats {
    uint32_t body_count = 0;
    uint32_t contact_count = 0;
    double simulation_time_ms = 0.0;
    double fixed_step_dt = 1.0 / 60.0;
};

class PhysicsWorld {
public:
    PhysicsWorld();
    ~PhysicsWorld();

    Result<void> init(double gravity = -9.81);
    Result<void> shutdown();

    bool is_initialized() const { return initialized_; }

    // Create a physics body and associate with an entity
    Result<void> create_body(Entity entity, const RigidBody& body, const Collider& collider);

    // Set a body's position and rotation
    Result<void> set_body_transform(Entity entity, const float position[3], const float rotation[4]);

    // Remove a physics body
    Result<void> remove_body(Entity entity);

    // Step the physics simulation (fixed timestep)
    Result<void> step(double dt);

    // Get physics stats
    PhysicsStats get_stats() const { return stats_; }

    // Get contact events from last step
    const std::vector<ContactEvent>& get_contacts() const { return contacts_; }

    // Set gravity
    void set_gravity(double gravity);

    // Get gravity
    double get_gravity() const { return gravity_; }

    // Sync physics transforms to ECS
    void sync_transforms(Registry& registry);

#ifdef REALITY_HAS_JOLT
    // Access to Jolt PhysicsSystem (for advanced use)
    JPH::PhysicsSystem* jolt_system() { return jolt_system_.get(); }
    JPH::BodyInterface* jolt_body_interface() { return jolt_body_interface_; }
#endif

    // ---- Jolt nested interfaces (public so they can be defined out-of-line) ----
#ifdef REALITY_HAS_JOLT
    // Broad-phase layer interface (simple 2-layer: static and dynamic)
    class BroadPhaseLayerInterfaceImpl : public JPH::BroadPhaseLayerInterface {
    public:
        BroadPhaseLayerInterfaceImpl();
        uint GetNumBroadPhaseLayers() const override { return 2; }
        JPH::BroadPhaseLayer GetBroadPhaseLayer(JPH::ObjectLayer inLayer) const override;
        const char* GetBroadPhaseLayerName(JPH::BroadPhaseLayer inLayer) const override;
    };

    // Object vs broad-phase layer filter
    class ObjectVsBroadPhaseLayerFilterImpl : public JPH::ObjectVsBroadPhaseLayerFilter {
    public:
        bool ShouldCollide(JPH::ObjectLayer inLayer1, JPH::BroadPhaseLayer inLayer2) const override;
    };

    // Object layer pair filter
    class ObjectLayerPairFilterImpl : public JPH::ObjectLayerPairFilter {
    public:
        bool ShouldCollide(JPH::ObjectLayer inLayer1, JPH::ObjectLayer inLayer2) const override;
    };

    // Contact listener for collision events
    class ContactListenerImpl : public JPH::ContactListener {
    public:
        explicit ContactListenerImpl(PhysicsWorld* world) : world_(world) {}

        JPH::ValidateResult OnContactValidate(const JPH::Body& inBody1, const JPH::Body& inBody2,
                                               JPH::RVec3Arg inBaseOffset, const JPH::CollideShapeResult& inCollisionResult) override {
            return JPH::ValidateResult::AcceptAllContactsForThisBodyPair;
        }

        void OnContactAdded(const JPH::Body& inBody1, const JPH::Body& inBody2,
                            const JPH::ContactManifold& inManifold, JPH::ContactSettings& ioSettings) override {
            (void)inManifold;
            (void)ioSettings;
            if (world_) {
                auto it1 = world_->body_id_to_entity_.find(inBody1.GetID());
                auto it2 = world_->body_id_to_entity_.find(inBody2.GetID());
                if (it1 != world_->body_id_to_entity_.end() &&
                    it2 != world_->body_id_to_entity_.end()) {
                    ContactEvent event;
                    event.entity_a = it1->second;
                    event.entity_b = it2->second;
                    event.impulse = 1.0f;
                    world_->contacts_.push_back(event);
                }
            }
        }

        void OnContactPersisted(const JPH::Body& inBody1, const JPH::Body& inBody2,
                                const JPH::ContactManifold& inManifold, JPH::ContactSettings& ioSettings) override {
            (void)inBody1;
            (void)inBody2;
            (void)inManifold;
            (void)ioSettings;
        }

        void OnContactRemoved(const JPH::SubShapeIDPair& inSubShapePair) override {
            (void)inSubShapePair;
        }

    private:
        PhysicsWorld* world_;
    };
#endif

private:
    bool initialized_ = false;
    double gravity_ = -9.81;
    PhysicsStats stats_;
    std::vector<ContactEvent> contacts_;
    std::map<Entity, JPH::BodyID> entity_to_body_id_;  // entity -> Jolt BodyID
    std::map<JPH::BodyID, Entity> body_id_to_entity_;  // Jolt BodyID -> entity

#ifdef REALITY_HAS_JOLT
    // Collision layers
    static constexpr uint32_t cDefaultLayer = 1;
    static constexpr uint32_t cDynamicLayer = 2;

    // Jolt memory allocators
    JPH::TempAllocatorImpl* jolt_temp_allocator_ = nullptr;
    JPH::JobSystemThreadPool* jolt_job_system_ = nullptr;

    // Jolt physics system (owned via unique_ptr with custom deleter)
    struct JoltSystemDeleter {
        void operator()(JPH::PhysicsSystem* ptr) const;
    };
    std::unique_ptr<JPH::PhysicsSystem, JoltSystemDeleter> jolt_system_;

    // Jolt body interface (owned by PhysicsSystem, we hold a pointer)
    JPH::BodyInterface* jolt_body_interface_ = nullptr;

    // Jolt interface instances
    BroadPhaseLayerInterfaceImpl jolt_broadphase_layer_interface_;
    ObjectVsBroadPhaseLayerFilterImpl jolt_object_vs_broadphase_filter_;
    ObjectLayerPairFilterImpl jolt_object_layer_pair_filter_;
    ContactListenerImpl jolt_contact_listener_{ this };
#endif
};

} // namespace reality
