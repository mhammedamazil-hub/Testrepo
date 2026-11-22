#include "scripting.h"

namespace reality {

Result<void> Scripting::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Scripting already initialized",
                               "scripting.cpp:Scripting::init"});
    }
    initialized_ = true;
    return Result<void>();
}

Result<void> Scripting::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Scripting not initialized",
                               "scripting.cpp:Scripting::shutdown"});
    }
    initialized_ = false;
    return Result<void>();
}

Result<void> Scripting::execute(const std::string& /*script_path*/) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Scripting not initialized",
                               "scripting.cpp:Scripting::execute"});
    }
    return Result<void>();
}

} // namespace reality
