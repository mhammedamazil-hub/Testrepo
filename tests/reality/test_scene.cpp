#include <cassert>
#include <iostream>
#include <string>
#include <fstream>
#include "scene/scene.h"

using namespace reality;

int main() {
    std::cout << "=== Scene Unit Tests ===" << std::endl;

    Scene scene;
    auto init_result = scene.init("TestScene");
    assert(init_result.ok());
    assert(scene.is_initialized());
    assert(scene.name() == "TestScene");
    std::cout << "  [PASS] Scene init" << std::endl;

    // Add entities
    SceneEntityData e1;
    e1.id = EntityId::generate();
    e1.name = "Ground";
    e1.transform.position[0] = 0.0f;
    e1.transform.position[1] = 0.0f;
    e1.transform.position[2] = 0.0f;
    scene.add_entity(e1);

    SceneEntityData e2;
    e2.id = EntityId::generate();
    e2.name = "Player";
    e2.transform.position[0] = 1.0f;
    e2.transform.position[1] = 2.0f;
    e2.transform.position[2] = 3.0f;
    scene.add_entity(e2);

    assert(scene.entity_count() == 2);
    std::cout << "  [PASS] Scene entity count" << std::endl;

    // Find entity
    const SceneEntityData* found = scene.find_entity(e1.id);
    assert(found != nullptr);
    assert(found->name == "Ground");
    assert(found == scene.find_entity(e1.id));
    std::cout << "  [PASS] Scene find_entity" << std::endl;

    // Serialize
    std::string json = scene.serialize();
    assert(json.find("\"name\": \"TestScene\"") != std::string::npos);
    assert(json.find("\"version\": \"1.0\"") != std::string::npos);
    assert(json.find(e1.id.to_string()) != std::string::npos);
    assert(json.find(e2.id.to_string()) != std::string::npos);
    std::cout << "  [PASS] Scene serialize" << std::endl;

    // Save and load
    std::string save_path = "/tmp/test_scene.reality";
    auto save_result = scene.save(save_path);
    assert(save_result.ok());
    std::cout << "  [PASS] Scene save" << std::endl;

    // Load into new scene
    Scene scene2;
    auto init2 = scene2.init("LoadedScene");
    assert(init2.ok());
    auto load_result = scene2.load(save_path);
    assert(load_result.ok());
    assert(scene2.entity_count() == 2);
    assert(scene2.find_entity(e1.id) != nullptr);
    assert(scene2.find_entity(e2.id) != nullptr);
    std::cout << "  [PASS] Scene load" << std::endl;

    // Validate
    auto validate_result = scene2.validate();
    assert(validate_result.ok());
    std::cout << "  [PASS] Scene validate" << std::endl;

    // Cleanup
    std::remove(save_path.c_str());

    std::cout << "=== All Scene tests passed! ===" << std::endl;
    return 0;
}
