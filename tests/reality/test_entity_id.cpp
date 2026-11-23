#include <cassert>
#include <iostream>
#include <set>
#include <string>
#include "ecs/ecs.h"

using namespace reality;

int main() {
    std::cout << "=== EntityId Unit Tests ===" << std::endl;

    // Test 1: Generate unique IDs
    {
        std::set<std::string> ids;
        for (int i = 0; i < 1000; i++) {
            EntityId id = EntityId::generate();
            assert(!id.is_null());
            ids.insert(id.to_string());
        }
        assert(ids.size() == 1000);  // All unique
        std::cout << "  [PASS] 1000 unique EntityIds generated" << std::endl;
    }

    // Test 2: String roundtrip
    {
        EntityId id = EntityId::generate();
        std::string str = id.to_string();
        assert(str.size() == 36);  // UUID format: 8-4-4-4-12

        EntityId parsed = EntityId::from_string(str);
        assert(parsed == id);
        assert(!parsed.is_null());
        std::cout << "  [PASS] EntityId string roundtrip" << std::endl;
    }

    // Test 3: Null ID
    {
        EntityId null_id{};
        assert(null_id.is_null());
        std::cout << "  [PASS] null EntityId detection" << std::endl;
    }

    // Test 4: Registry entity ID mapping
    {
        Registry registry;
        Entity e = registry.create_entity();
        EntityId id = EntityId::generate();
        registry.register_entity_id(e, id);

        assert(registry.has_entity_id(e));
        assert(registry.get_entity_id(e) == id);
        assert(registry.get_entity_by_id(id) == e);
        assert(!registry.has_entity_id(999));  // non-existent entity

        registry.destroy_entity(e);
        assert(!registry.has_entity_id(e));
        std::cout << "  [PASS] Registry entity ID mapping" << std::endl;
    }

    std::cout << "=== All EntityId tests passed! ===" << std::endl;
    return 0;
}
