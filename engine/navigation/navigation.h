#pragma once

#include <string>
#include "core/error.h"

namespace reality {

class Navigation {
public:
    Navigation() = default;
    ~Navigation() = default;

    Result<void> init();
    Result<void> shutdown();
    bool is_initialized() const { return initialized_; }

private:
    bool initialized_ = false;
};

} // namespace reality
