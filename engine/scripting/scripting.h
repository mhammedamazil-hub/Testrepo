#pragma once

#include <string>
#include "core/error.h"

namespace reality {

class Scripting {
public:
    Scripting() = default;
    ~Scripting() = default;

    Result<void> init();
    Result<void> shutdown();
    bool is_initialized() const { return initialized_; }

    // Execute a script (Phase 1: stub)
    Result<void> execute(const std::string& script_path);

private:
    bool initialized_ = false;
};

} // namespace reality
