#pragma once

#include <chrono>
#include "engine.h"
#include "logging.h"

namespace reality {

class GameLoop {
public:
    GameLoop();

    // Run the main game loop
    Result<void> run();

    // Request the loop to stop
    void stop();

    // Get the current frame number
    uint64_t frame_count() const { return frame_count_; }

private:
    std::atomic<bool> running_{false};
    uint64_t frame_count_ = 0;

    // Fixed timestep: 60 Hz for simulation
    static constexpr double FIXED_TIMESTEP = 1.0 / 60.0;

    // Variable timestep target: 60 Hz for rendering
    static constexpr double RENDER_TARGET_DT = 1.0 / 60.0;

    using Clock = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;
    using Duration = Clock::duration;
};

} // namespace reality
