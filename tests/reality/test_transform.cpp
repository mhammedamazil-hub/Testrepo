#include <cassert>
#include <iostream>
#include <cmath>
#include "ecs/ecs.h"

using namespace reality;

int main() {
    std::cout << "=== Transform Unit Tests ===" << std::endl;

    Registry registry;

    // Test 1: Default transform
    {
        Entity e = registry.create_entity();
        registry.add_component<Transform>(e, Transform{});
        auto* t = registry.get_component<Transform>(e);
        assert(t->position[0] == 0.0f);
        assert(t->position[1] == 0.0f);
        assert(t->position[2] == 0.0f);
        assert(t->scale[0] == 1.0f);
        assert(t->scale[1] == 1.0f);
        assert(t->scale[2] == 1.0f);
        assert(t->parent == NULL_ENTITY);
        std::cout << "  [PASS] default transform values" << std::endl;
    }

    // Test 2: Transform modification
    {
        Entity e = registry.create_entity();
        auto* t = registry.add_component<Transform>(e, Transform{});
        t->position[0] = 1.5f;
        t->position[1] = 2.5f;
        t->position[2] = 3.5f;
        t->scale[0] = 2.0f;

        auto* retrieved = registry.get_component<Transform>(e);
        assert(retrieved->position[0] == 1.5f);
        assert(retrieved->position[1] == 2.5f);
        assert(retrieved->position[2] == 3.5f);
        assert(retrieved->scale[0] == 2.0f);
        std::cout << "  [PASS] transform modification" << std::endl;
    }

    // Test 3: Parent-child hierarchy
    {
        Entity parent = registry.create_entity();
        auto* pt = registry.add_component<Transform>(parent, Transform{});
        pt->position[0] = 10.0f;

        Entity child = registry.create_entity();
        auto* ct = registry.add_component<Transform>(child, Transform{});
        ct->position[0] = 1.0f;
        ct->parent = parent;

        assert(ct->parent == parent);
        auto* pt2 = registry.get_component<Transform>(parent);
        assert(pt2->position[0] == 10.0f);
        std::cout << "  [PASS] parent-child hierarchy" << std::endl;
    }

    std::cout << "=== All Transform tests passed! ===" << std::endl;
    return 0;
}
