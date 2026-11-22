#include "input.h"

namespace reality {

Result<void> Input::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Input already initialized",
                               "input.cpp:Input::init"});
    }
    initialized_ = true;
    return Result<void>();
}

Result<void> Input::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Input not initialized",
                               "input.cpp:Input::shutdown"});
    }
    initialized_ = false;
    return Result<void>();
}

Result<void> Input::poll() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Input not initialized",
                               "input.cpp:Input::poll"});
    }
    return Result<void>();
}

} // namespace reality
