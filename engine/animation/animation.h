#pragma once

#include <string>
#include "core/error.h"
#include "ecs/ecs.h"

namespace reality {

class Animation {
public:
    Animation() = default;
    ~Animation() = default;

    Result<void> init();
    Result<void> shutdown();
    bool is_initialized() const { return initialized_; }

    // Update animations (Phase 1: stub)
    Result<void> update(Registry& registry, double dt);

private:
    bool initialized_ = false;
};

} // namespace reality
