#pragma once

#include <string>
#include <memory>
#include <atomic>
#include "error.h"
#include "logging.h"

namespace reality {

class Engine {
public:
    Engine();
    ~Engine();

    // Initialize the engine with configuration
    Result<void> init(const std::string& config_path = "");

    // Shutdown the engine
    Result<void> shutdown();

    // Check if engine is running
    bool is_running() const { return running_.load(); }

    // Get engine version
    static const char* version();

    // Get engine name
    static const char* name();

private:
    std::atomic<bool> running_{false};
    bool initialized_ = false;
    std::string config_path_;
};

} // namespace reality
