#include "engine.h"

namespace reality {

const char* Engine::name() { return "Reality Engine"; }
const char* Engine::version() { return "0.1.0-phase1"; }

Engine::Engine() = default;

Engine::~Engine() {
    if (running_) {
        shutdown();
    }
}

Result<void> Engine::init(const std::string& config_path) {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Engine already initialized",
                               "engine.cpp:Engine::init"});
    }

    config_path_ = config_path;

    // Initialize logging
    Logger::instance().set_level(LogLevel::INFO);
    Logger::instance().set_console(true);

    if (!config_path.empty()) {
        // Config loading handled separately; just store path
        REALITY_LOG(INFO, "Engine: config path = " + config_path);
    }

    REALITY_LOG(INFO, "Engine: initializing " + std::string(name()) +
                   " v" + std::string(version()));

    running_ = true;
    initialized_ = true;

    REALITY_LOG(INFO, "Engine: initialized successfully");
    return Result<void>();
}

Result<void> Engine::shutdown() {
    if (!running_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Engine not running",
                               "engine.cpp:Engine::shutdown"});
    }

    REALITY_LOG(INFO, "Engine: shutting down...");

    running_ = false;

    REALITY_LOG(INFO, "Engine: shutdown complete");
    return Result<void>();
}

} // namespace reality
