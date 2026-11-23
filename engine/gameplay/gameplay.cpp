#include "gameplay.h"

namespace reality {

Result<void> Gameplay::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Gameplay already initialized",
                               "gameplay.cpp:Gameplay::init"});
    }
    initialized_ = true;
    return Result<void>();
}

Result<void> Gameplay::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Gameplay not initialized",
                               "gameplay.cpp:Gameplay::shutdown"});
    }
    initialized_ = false;
    return Result<void>();
}

Result<void> Gameplay::update(Registry& /*registry*/, double /*dt*/) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Gameplay not initialized",
                               "gameplay.cpp:Gameplay::update"});
    }
    return Result<void>();
}

} // namespace reality
