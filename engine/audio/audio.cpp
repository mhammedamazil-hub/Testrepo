#include "audio.h"

namespace reality {

Result<void> Audio::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Audio already initialized",
                               "audio.cpp:Audio::init"});
    }
    initialized_ = true;
    return Result<void>();
}

Result<void> Audio::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Audio not initialized",
                               "audio.cpp:Audio::shutdown"});
    }
    initialized_ = false;
    return Result<void>();
}

} // namespace reality
