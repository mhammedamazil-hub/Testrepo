#include <iostream>
#include <string>
#include <chrono>
#include <thread>
#include <cstring>

#include "core/application.h"
#include "core/logging.h"
#include "world/world.h"
#include "scene/scene.h"
#include "physics/physics_world.h"
#include "physics/physics_body.h"
#include "rendering/headless_renderer.h"
#include "assets/asset_manager.h"
#include "diagnostics/diagnostics.h"
#include "platform/platform.h"

using namespace reality;

static void print_usage() {
    std::cout << "Reality Engine Runtime v0.1.0-phase1\n";
    std::cout << "Usage: reality_runtime <project_path> [options]\n";
    std::cout << "Options:\n";
    std::cout << "  --scene <name>     Scene to load (default: first scene)\n";
    std::cout << "  --frames <N>       Number of frames to simulate (default: 120)\n";
    std::cout << "  --headless         Run in headless mode (default)\n";
    std::cout << "  --diagnostics      Output diagnostics JSON on exit\n";
    std::cout << "  --help             Show this help\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_usage();
        return 1;
    }

    std::string project_path;
    std::string scene_name;
    int num_frames = 120;
    bool output_diagnostics = false;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            print_usage();
            return 0;
        } else if (arg == "--scene" && i + 1 < argc) {
            scene_name = argv[++i];
        } else if (arg == "--frames" && i + 1 < argc) {
            num_frames = std::stoi(argv[++i]);
        } else if (arg == "--diagnostics") {
            output_diagnostics = true;
        } else if (arg == "--headless") {
        } else if (arg[0] != '-') {
            project_path = arg;
        }
    }

    if (project_path.empty()) {
        std::cerr << "Error: project path required\n";
        print_usage();
        return 1;
    }

    REALITY_LOG(INFO, "=== Reality Engine Runtime ===");
    REALITY_LOG(INFO, "Project: " + project_path);
    REALITY_LOG(INFO, "Frames: " + std::to_string(num_frames));

    Platform platform;
    auto presult = platform.init();
    if (!presult.ok()) {
        REALITY_LOG(ERROR, "Platform init failed: " + presult.error().message);
        return 1;
    }

    Engine engine;
    auto eresult = engine.init(project_path + "/engine.config.json");
    if (!eresult.ok()) {
        REALITY_LOG(ERROR, "Engine init failed: " + eresult.error().message);
        return 1;
    }

    World world;
    auto wresult = world.init("MainWorld");
    if (!wresult.ok()) {
        REALITY_LOG(ERROR, "World init failed: " + wresult.error().message);
        return 1;
    }

    PhysicsWorld physics;
    auto physresult = physics.init(-9.81);
    if (!physresult.ok()) {
        REALITY_LOG(ERROR, "Physics init failed: " + physresult.error().message);
        return 1;
    }

    HeadlessRenderer renderer;
    auto rresult = renderer.init();
    if (!rresult.ok()) {
        REALITY_LOG(ERROR, "Renderer init failed: " + rresult.error().message);
        return 1;
    }

    Scene scene;
    auto sresult = scene.init("MainScene");
    if (!sresult.ok()) {
        REALITY_LOG(ERROR, "Scene init failed: " + sresult.error().message);
        return 1;
    }

    std::string scene_path;
    if (!scene_name.empty()) {
        scene_path = project_path + "/scenes/" + scene_name + ".scene.reality";
    } else {
        scene_path = project_path + "/scenes/Main.scene.reality";
    }

    auto load_result = scene.load(scene_path);
    if (!load_result.ok()) {
        REALITY_LOG(WARN, "Scene load failed: " + load_result.error().message +
                   " - creating default scene");
    }

    auto vresult = scene.validate();
    if (!vresult.ok()) {
        REALITY_LOG(WARN, "Scene validation: " + vresult.error().message);
    }

    REALITY_LOG(INFO, "Creating physics demonstration scene...");

    Entity ground = world.create_entity("Ground");
    auto* ground_rb = world.registry().add_component<RigidBody>(ground, RigidBody{});
    ground_rb->type = BodyType::Static;
    ground_rb->mass = 0.0f;
    ground_rb->friction = 0.5f;
    ground_rb->restitution = 0.0f;
    ground_rb->gravity_enabled = false;

    auto* ground_col = world.registry().add_component<Collider>(ground, Collider{});
    ground_col->shape = ColliderShape::Box;
    ground_col->size[0] = 50.0f;
    ground_col->size[1] = 1.0f;
    ground_col->size[2] = 50.0f;
    ground_col->collision_layer = 1;

    physics.create_body(ground, *ground_rb, *ground_col);
    {
        float gpos[3] = {0.0f, 0.0f, 0.0f};
        float grot[4] = {0.0f, 0.0f, 0.0f, 1.0f};
        physics.set_body_transform(ground, gpos, grot);
    }

    const int num_objects = 6;
    for (int i = 0; i < num_objects; i++) {
        std::string obj_name = "DynamicObject_" + std::to_string(i);
        Entity obj = world.create_entity(obj_name);

        float x = -5.0f + i * 2.0f;
        float y = 10.0f + i * 1.0f;
        float z = 0.0f;

        auto* transform = world.registry().add_component<Transform>(obj, Transform{});
        transform->position[0] = x;
        transform->position[1] = y;
        transform->position[2] = z;

        ColliderShape shape = (i % 2 == 0) ? ColliderShape::Box : ColliderShape::Sphere;

        auto* rb = world.registry().add_component<RigidBody>(obj, RigidBody{});
        rb->type = BodyType::Dynamic;
        rb->mass = 1.0f;
        rb->friction = 0.3f;
        rb->restitution = 0.3f;
        rb->gravity_enabled = true;

        auto* col = world.registry().add_component<Collider>(obj, Collider{});
        if (shape == ColliderShape::Box) {
            col->shape = ColliderShape::Box;
            col->size[0] = 1.0f;
            col->size[1] = 1.0f;
            col->size[2] = 1.0f;
        } else {
            col->shape = ColliderShape::Sphere;
            col->radius = 0.7f;
        }
        col->collision_layer = 1;

        physics.create_body(obj, *rb, *col);
        physics.set_body_transform(obj, transform->position, transform->rotation);

        REALITY_LOG(INFO, "Created " + obj_name + " at (" +
                   std::to_string(x) + ", " + std::to_string(y) + ", " + std::to_string(z) + ")");
    }

    REALITY_LOG(INFO, "Running physics simulation for " + std::to_string(num_frames) + " frames...");

    auto start_time = std::chrono::steady_clock::now();
    double fixed_dt = 1.0 / 60.0;

    for (int frame = 0; frame < num_frames; frame++) {
        physics.step(fixed_dt);
        physics.sync_transforms(world.registry());
        renderer.clear();
        renderer.render(fixed_dt);

        if ((frame + 1) % 30 == 0) {
            REALITY_LOG(INFO, "Frame " + std::to_string(frame + 1) + "/" +
                       std::to_string(num_frames));
        }
    }

    auto end_time = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(end_time - start_time).count();

    DiagnosticsCollector diag;
    diag.set_uptime(elapsed);
    diag.set_frame_count(num_frames);
    diag.set_average_fps(num_frames / elapsed);
    diag.set_physics_time(physics.get_stats().simulation_time_ms);
    diag.set_entity_count(world.entity_count());
    diag.set_physics_body_count(physics.get_stats().body_count);
    diag.set_draw_call_count(renderer.get_stats().draw_calls);
    diag.add_custom_metric("physics_backend",
#ifdef REALITY_HAS_JOLT
                           "jolt"
#else
                           "stub"
#endif
                           );
    diag.add_custom_metric("renderer", "headless");
    diag.add_custom_metric("scene", scene_path);

    REALITY_LOG(INFO, "=== Entity States After Simulation ===");
    auto& reg = world.registry();
    for (auto [entity, components] : reg.view<Name, Transform>()) {
        auto& [name, transform] = components;
        REALITY_LOG(INFO, "Entity " + std::to_string(entity) + " (" + name->value + "): " +
                   "pos=(" + std::to_string(transform->position[0]) + ", " +
                   std::to_string(transform->position[1]) + ", " +
                   std::to_string(transform->position[2]) + ")");
    }

    if (output_diagnostics) {
        std::cout << diag.to_json() << std::endl;
    }

    renderer.shutdown();
    physics.shutdown();
    scene.shutdown();
    world.shutdown();
    engine.shutdown();
    platform.shutdown();

    REALITY_LOG(INFO, "=== Reality Engine Runtime Complete ===");
    REALITY_LOG(INFO, "Elapsed: " + std::to_string(elapsed) + "s");
    REALITY_LOG(INFO, "FPS: " + std::to_string(num_frames / elapsed));

    return 0;
}
