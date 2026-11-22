#include "game_loop.h"

#include <thread>

namespace reality {

GameLoop::GameLoop() = default;

Result<void> GameLoop::run() {
    if (running_.load()) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Game loop already running",
                               "game_loop.cpp:GameLoop::run"});
    }

    running_ = true;

    REALITY_LOG(INFO, "GameLoop: starting (fixed timestep: " +
                   std::to_string(FIXED_TIMESTEP) + "s)");

    auto last_time = Clock::now();
    double accumulator = 0.0;

    while (running_.load()) {
        auto current_time = Clock::now();
        Duration frame_duration = current_time - last_time;
        last_time = current_time;

        double dt = std::chrono::duration<double>(frame_duration).count();

        if (dt > 0.25) dt = 0.25;

        accumulator += dt;

        while (accumulator >= FIXED_TIMESTEP && running_.load()) {
            accumulator -= FIXED_TIMESTEP;
        }

        frame_count_++;

        if (dt < RENDER_TARGET_DT) {
            auto sleep_time = std::chrono::duration<double>(RENDER_TARGET_DT - dt);
            std::this_thread::sleep_for(sleep_time);
        }
    }

    REALITY_LOG(INFO, "GameLoop: stopped after " +
                   std::to_string(frame_count_) + " frames");
    return Result<void>();
}

void GameLoop::stop() {
    running_ = false;
}

} // namespace reality
