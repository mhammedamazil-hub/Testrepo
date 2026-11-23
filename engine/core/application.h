#pragma once

#include <string>
#include <atomic>
#include "engine.h"

namespace reality {

class Application {
public:
    Application();
    ~Application();

    Result<void> init(const std::string& config_path = "");
    Result<void> run();
    void quit();

    bool is_running() const { return running_.load(); }

private:
    std::atomic<bool> running_{false};
    bool initialized_ = false;
    Engine engine_;
};

} // namespace reality
