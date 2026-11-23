#pragma once

#include <string>
#include "core/error.h"

namespace reality {

class Input {
public:
    Input() = default;
    ~Input() = default;

    Result<void> init();
    Result<void> shutdown();
    bool is_initialized() const { return initialized_; }

    // Poll input events (Phase 1: stub)
    Result<void> poll();

private:
    bool initialized_ = false;
};

} // namespace reality
