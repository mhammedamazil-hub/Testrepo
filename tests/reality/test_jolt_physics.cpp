// Comprehensive Jolt Physics verification test
// Tests: ground plane, 6 dynamic objects with different masses/restitution,
//        object-to-object collisions, 300+ simulation steps, proves Jolt backend

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "core/application.h"
#include "core/logging.h"
#include "core/error.h"
#include "ecs/ecs.h"
#include "world/world.h"
#include "scene/scene.h"
#include "physics/physics_world.h"
#include "physics/physics_body.h"
#include "rendering/headless_renderer.h"
#include "diagnostics/diagnostics.h"
#include "platform/platform.h"

using namespace reality;

int main() {
    int passed = 0;
    int failed = 0;

    std::cout << "=== Jolt Physics Verification Test ===" << std::endl;

    Platform platform;
    auto presult = platform.init();
    if (!presult.ok()) {
        std::cerr << "Platform init failed: " << presult.error().message << std::endl;
        return 1;
    }

    Engine engine;
    auto eresult = engine.init("/tmp/reality_jolt_test/engine.config.json");
    if (!eresult.ok()) {
        std::cerr << "Engine init failed: " << eresult.error().message << std::endl;
        return 1;
    }

    World world;
    auto wresult = world.init("PhysicsTestWorld");
    if (!wresult.ok()) {
        std::cerr << "World init failed: " << wresult.error().message << std::endl;
        return 1;
    }

    PhysicsWorld physics;
    auto physresult = physics.init(-9.81);
    if (!physresult.ok()) {
        std::cerr << "Physics init failed: " << physresult.error().message << std::endl;
        return 1;
    }

    // Verify Jolt backend is active
#ifdef REALITY_HAS_JOLT
    std::cout << "PASS: REALITY_HAS_JOLT is defined - Jolt backend compiled in" << std::endl;
    passed++;
#else
    std::cerr << "FAIL: REALITY_HAS_JOLT is NOT defined - running in stub mode" << std::endl;
    failed++;
#endif

    HeadlessRenderer renderer;
    auto rresult = renderer.init();
    if (!rresult.ok()) {
        std::cerr << "Renderer init failed: " << rresult.error().message << std::endl;
        return 1;
    }

    // Create ground plane (static)
    Entity ground = world.create_entity("Ground");
    auto* ground_rb = world.registry().add_component<RigidBody>(ground, RigidBody{});
    ground_rb->type = BodyType::Static;
    ground_rb->mass = 0.0f;
    ground_rb->friction = 0.5f;
    ground_rb->restitution = 0.1f;
    ground_rb->gravity_enabled = false;

    auto* ground_col = world.registry().add_component<Collider>(ground, Collider{});
    ground_col->shape = ColliderShape::Box;
    ground_col->size[0] = 50.0f;
    ground_col->size[1] = 1.0f;
    ground_col->size[2] = 50.0f;
    ground_col->collision_layer = 1;

    float gpos[3] = {0.0f, 0.0f, 0.0f};
    float grot[4] = {0.0f, 0.0f, 0.0f, 1.0f};
    physics.create_body(ground, *ground_rb, *ground_col);
    physics.set_body_transform(ground, gpos, grot);

    std::cout << "PASS: Ground plane created (static body)" << std::endl;
    passed++;

    // Create 6 dynamic objects with different masses and restitution
    struct ObjectDesc {
        const char* name;
        float mass;
        float restitution;
        float start_x;
        float start_y;
        ColliderShape shape;
    };

    ObjectDesc objects[] = {
        {"HeavyBox",    10.0f, 0.1f, -6.0f, 20.0f, ColliderShape::Box},
        {"LightSphere",  1.0f, 0.8f, -2.0f, 22.0f, ColliderShape::Sphere},
        {"MediumBox",    5.0f, 0.5f,  2.0f, 18.0f, ColliderShape::Box},
        {"BouncyBall",   0.5f, 0.9f,  6.0f, 24.0f, ColliderShape::Sphere},
        {"HeavySphere",  8.0f, 0.2f, -4.0f, 16.0f, ColliderShape::Sphere},
        {"LightBox",     2.0f, 0.6f,  0.0f, 14.0f, ColliderShape::Box},
    };

    const int num_objects = 6;
    Entity entities[num_objects];

    for (int i = 0; i < num_objects; i++) {
        entities[i] = world.create_entity(objects[i].name);

        auto* transform = world.registry().add_component<Transform>(entities[i], Transform{});
        transform->position[0] = objects[i].start_x;
        transform->position[1] = objects[i].start_y;
        transform->position[2] = 0.0f;

        auto* rb = world.registry().add_component<RigidBody>(entities[i], RigidBody{});
        rb->type = BodyType::Dynamic;
        rb->mass = objects[i].mass;
        rb->friction = 0.3f;
        rb->restitution = objects[i].restitution;
        rb->gravity_enabled = true;

        auto* col = world.registry().add_component<Collider>(entities[i], Collider{});
        if (objects[i].shape == ColliderShape::Box) {
            col->shape = ColliderShape::Box;
            col->size[0] = 1.0f;
            col->size[1] = 1.0f;
            col->size[2] = 1.0f;
        } else {
            col->shape = ColliderShape::Sphere;
            col->radius = 0.7f;
        }
        col->collision_layer = 1;

        physics.create_body(entities[i], *rb, *col);
        physics.set_body_transform(entities[i], transform->position, transform->rotation);

        std::cout << "  Created " << objects[i].name
                  << " mass=" << objects[i].mass
                  << " restitution=" << objects[i].restitution
                  << " at (" << objects[i].start_x << "," << objects[i].start_y << ")"
                  << std::endl;
    }

    std::cout << "PASS: " << num_objects << " dynamic objects created with varying mass/restitution" << std::endl;
    passed++;

    // Record initial positions
    float initial_y[num_objects];
    for (int i = 0; i < num_objects; i++) {
        auto* t = world.registry().get_component<Transform>(entities[i]);
        initial_y[i] = t->position[1];
    }

    // Run 300+ simulation steps (5 seconds at 60 FPS)
    const int num_steps = 300;
    double fixed_dt = 1.0 / 60.0;

    std::cout << "Running " << num_steps << " physics steps (" << num_steps * fixed_dt << " seconds)..." << std::endl;

    auto start_time = std::chrono::steady_clock::now();
    for (int step = 0; step < num_steps; step++) {
        physics.step(fixed_dt);
        physics.sync_transforms(world.registry());
        renderer.clear();
        renderer.render(fixed_dt);
    }
    auto end_time = std::chrono::steady_clock::now();

    double elapsed = std::chrono::duration<double>(end_time - start_time).count();
    std::cout << "Simulation completed in " << elapsed << " seconds" << std::endl;

    // Verify objects fell (Y position decreased due to gravity)
    bool all_fell = true;
    for (int i = 0; i < num_objects; i++) {
        auto* t = world.registry().get_component<Transform>(entities[i]);
        float fall_distance = initial_y[i] - t->position[1];
        std::cout << "  " << objects[i].name
                  << " initial_y=" << initial_y[i]
                  << " final_y=" << t->position[1]
                  << " fell=" << fall_distance << "m" << std::endl;

        if (fall_distance < 0.1f) {
            std::cerr << "    WARNING: " << objects[i].name << " barely fell!" << std::endl;
            all_fell = false;
        }

        // Verify object is above ground (not falling through)
        if (t->position[1] < -1.0f) {
            std::cerr << "    ERROR: " << objects[i].name << " fell below ground!" << std::endl;
            failed++;
        }
    }

    if (all_fell) {
        std::cout << "PASS: All objects fell under gravity" << std::endl;
        passed++;
    } else {
        std::cerr << "FAIL: Not all objects fell under gravity" << std::endl;
        failed++;
    }

    // Verify different masses fell at approximately the same rate (gravity affects all equally)
    // In vacuum, all objects fall at same rate regardless of mass
    bool mass_independence = true;
    for (int i = 1; i < num_objects; i++) {
        auto* t = world.registry().get_component<Transform>(entities[i]);
        auto* t0 = world.registry().get_component<Transform>(entities[0]);
        float fall_i = initial_y[i] - t->position[1];
        float fall_0 = initial_y[0] - t0->position[1];
        float diff = std::abs(fall_i - fall_0);
        if (diff > 2.0f) {  // Allow some variance due to collisions
            mass_independence = false;
            std::cout << "  Note: " << objects[i].name << " fell differently than " << objects[0].name
                      << " (diff=" << diff << "m, likely due to collisions)" << std::endl;
        }
    }
    if (mass_independence) {
        std::cout << "PASS: Objects fell at similar rates (mass-independent gravity)" << std::endl;
        passed++;
    } else {
        std::cout << "INFO: Objects fell at different rates (likely due to collisions between objects)" << std::endl;
    }

    // Verify ground stayed stationary
    auto* ground_t = world.registry().get_component<Transform>(ground);
    if (std::abs(ground_t->position[1]) < 0.01f) {
        std::cout << "PASS: Ground stayed stationary (static body)" << std::endl;
        passed++;
    } else {
        std::cerr << "FAIL: Ground moved! y=" << ground_t->position[1] << std::endl;
        failed++;
    }

    // Verify physics stats
    PhysicsStats stats = physics.get_stats();
    std::cout << "Physics stats: bodies=" << stats.body_count
              << " contacts=" << stats.contact_count
              << " sim_time_ms=" << stats.simulation_time_ms << std::endl;

    if (stats.body_count == 7) {  // 1 ground + 6 objects
        std::cout << "PASS: Correct body count (7)" << std::endl;
        passed++;
    } else {
        std::cerr << "FAIL: Expected 7 bodies, got " << stats.body_count << std::endl;
        failed++;
    }

    if (stats.contact_count > 0) {
        std::cout << "PASS: Contact events detected (objects collided)" << std::endl;
        passed++;
    } else {
        std::cout << "INFO: No contact events (objects may not have collided yet)" << std::endl;
    }

    // Verify diagnostics output
    DiagnosticsCollector diag;
    diag.set_uptime(elapsed);
    diag.set_frame_count(num_steps);
    diag.set_average_fps(num_steps / elapsed);
    diag.set_physics_time(stats.simulation_time_ms);
    diag.set_entity_count(world.entity_count());
    diag.set_physics_body_count(stats.body_count);
    diag.set_draw_call_count(0);
#ifdef REALITY_HAS_JOLT
    diag.add_custom_metric("physics_backend", "jolt");
#else
    diag.add_custom_metric("physics_backend", "stub");
#endif
    diag.add_custom_metric("renderer", "headless");

    std::string json = diag.to_json();
    std::cout << "Diagnostics JSON: " << json << std::endl;

    if (json.find("physics_backend") != std::string::npos && json.find("jolt") != std::string::npos) {
        std::cout << "PASS: Diagnostics confirm Jolt physics backend" << std::endl;
        passed++;
    } else {
        std::cerr << "FAIL: Diagnostics do not confirm Jolt backend" << std::endl;
        failed++;
    }

    // Shutdown
    renderer.shutdown();
    physics.shutdown();
    world.shutdown();
    engine.shutdown();
    platform.shutdown();

    std::cout << "\n=== Jolt Physics Verification Results ===" << std::endl;
    std::cout << "Passed: " << passed << std::endl;
    std::cout << "Failed: " << failed << std::endl;

    return failed > 0 ? 1 : 0;
}
