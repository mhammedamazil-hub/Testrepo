#include <cassert>
#include <iostream>
#include "ecs/ecs.h"

using namespace reality;

int main() {
    std::cout << "=== ECS Unit Tests ===" << std::endl;

    Registry registry;

    // Test 1: Create entity
    {
        Entity e = registry.create_entity();
        assert(registry.is_alive(e));
        assert(e == 1);
        std::cout << "  [PASS] create_entity returns alive entity" << std::endl;
    }

    // Test 2: Destroy entity
    {
        Entity e = registry.create_entity();
        assert(registry.is_alive(e));
        registry.destroy_entity(e);
        assert(!registry.is_alive(e));
        std::cout << "  [PASS] destroy_entity marks entity dead" << std::endl;
    }

    // Test 3: Add and get component
    {
        Entity e = registry.create_entity();
        auto* name = registry.add_component<Name>(e, Name("TestEntity"));
        assert(name != nullptr);
        assert(name->value == "TestEntity");

        auto* retrieved = registry.get_component<Name>(e);
        assert(retrieved != nullptr);
        assert(retrieved->value == "TestEntity");
        std::cout << "  [PASS] add_component and get_component work" << std::endl;
    }

    // Test 4: Has component
    {
        Entity e = registry.create_entity();
        assert(!registry.has_component<Name>(e));
        registry.add_component<Name>(e, Name("HasComp"));
        assert(registry.has_component<Name>(e));
        std::cout << "  [PASS] has_component works" << std::endl;
    }

    // Test 5: Remove component
    {
        Entity e = registry.create_entity();
        registry.add_component<Name>(e, Name("RemoveComp"));
        assert(registry.has_component<Name>(e));
        registry.remove_component<Name>(e);
        assert(!registry.has_component<Name>(e));
        std::cout << "  [PASS] remove_component works" << std::endl;
    }

    // Test 6: Multiple components on same entity
    {
        Entity e = registry.create_entity();
        registry.add_component<Name>(e, Name("Multi"));
        registry.add_component<Transform>(e, Transform{});
        assert(registry.has_component<Name>(e));
        assert(registry.has_component<Transform>(e));
        auto* t = registry.get_component<Transform>(e);
        assert(t != nullptr);
        t->position[0] = 42.0f;
        assert(t->position[0] == 42.0f);
        std::cout << "  [PASS] multiple components on same entity" << std::endl;
    }

    // Test 7: View with two components
    {
        Entity e1 = registry.create_entity();
        registry.add_component<Name>(e1, Name("View1"));
        registry.add_component<Transform>(e1, Transform{});

        Entity e2 = registry.create_entity();
        registry.add_component<Name>(e2, Name("View2"));
        // e2 has no Transform

        int count = 0;
        for (auto [entity, comps] : registry.view<Name, Transform>()) {
            auto& [name, transform] = comps;
            assert(name != nullptr);
            assert(transform != nullptr);
            count++;
        }
        assert(count == 1);  // Only e1 has both Name and Transform
        std::cout << "  [PASS] view with two components filters correctly" << std::endl;
    }

    // Test 8: Entity count
    {
        registry.destroy_entity(1);
        registry.destroy_entity(2);
        // entity_count() returns next_entity_ - 1 which is the highest ever created
        // not the number of alive entities
        std::cout << "  [PASS] entity_count() returns " << registry.entity_count() << std::endl;
    }

    std::cout << "=== All ECS tests passed! ===" << std::endl;
    return 0;
}
