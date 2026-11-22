#include "navigation.h"

namespace reality {

Result<void> Navigation::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Navigation already initialized",
                               "navigation.cpp:Navigation::init"});
    }
    initialized_ = true;
    return Result<void>();
}

Result<void> Navigation::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Navigation not initialized",
                               "navigation.cpp:Navigation::shutdown"});
    }
    initialized_ = false;
    return Result<void>();
}

} // namespace reality
