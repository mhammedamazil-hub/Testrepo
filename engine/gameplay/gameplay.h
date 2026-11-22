#pragma once

#include <string>
#include "core/error.h"
#include "ecs/ecs.h"

namespace reality {

class Gameplay {
public:
    Gameplay() = default;
    ~Gameplay() = default;

    Result<void> init();
    Result<void> shutdown();
    bool is_initialized() const { return initialized_; }

    Result<void> update(Registry& registry, double dt);

private:
    bool initialized_ = false;
};

} // namespace reality
