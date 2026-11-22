#pragma once

#include <string>
#include "core/error.h"

namespace reality {

class Platform {
public:
    Platform() = default;
    ~Platform() = default;

    Result<void> init();
    Result<void> shutdown();

    bool is_initialized() const { return initialized_; }

    // Get platform name
    const char* name() const { return "Linux"; }

    // Get current time in seconds
    double get_time() const;

    // Sleep for specified seconds
    void sleep(double seconds) const;

private:
    bool initialized_ = false;
};

} // namespace reality
