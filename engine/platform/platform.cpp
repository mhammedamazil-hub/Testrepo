#include "platform.h"
#include <chrono>
#include <thread>

namespace reality {

Result<void> Platform::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Platform already initialized",
                               "platform.cpp:Platform::init"});
    }

    initialized_ = true;
    return Result<void>();
}

Result<void> Platform::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Platform not initialized",
                               "platform.cpp:Platform::shutdown"});
    }

    initialized_ = false;
    return Result<void>();
}

double Platform::get_time() const {
    auto now = std::chrono::steady_clock::now();
    auto epoch = now.time_since_epoch();
    return std::chrono::duration<double>(epoch).count();
}

void Platform::sleep(double seconds) const {
    std::this_thread::sleep_for(
        std::chrono::duration<double>(seconds));
}

} // namespace reality
