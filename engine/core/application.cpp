#include "application.h"
#include "game_loop.h"
#include "logging.h"

namespace reality {

Application::Application() = default;
Application::~Application() {
    if (running_) {
        quit();
    }
}

Result<void> Application::init(const std::string& config_path) {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Application already initialized",
                               "application.cpp:Application::init"});
    }

    auto result = engine_.init(config_path);
    if (!result.ok()) {
        return result;
    }

    running_ = true;
    initialized_ = true;

    REALITY_LOG(INFO, "Application: initialized");
    return Result<void>();
}

Result<void> Application::run() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Application not initialized",
                               "application.cpp:Application::run"});
    }

    GameLoop loop;
    return loop.run();
}

void Application::quit() {
    running_ = false;
    engine_.shutdown();
}

} // namespace reality
