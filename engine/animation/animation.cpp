#include "animation.h"

namespace reality {

Result<void> Animation::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Animation already initialized",
                               "animation.cpp:Animation::init"});
    }
    initialized_ = true;
    return Result<void>();
}

Result<void> Animation::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Animation not initialized",
                               "animation.cpp:Animation::shutdown"});
    }
    initialized_ = false;
    return Result<void>();
}

Result<void> Animation::update(Registry& /*registry*/, double /*dt*/) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Animation not initialized",
                               "animation.cpp:Animation::update"});
    }
    return Result<void>();
}

} // namespace reality
