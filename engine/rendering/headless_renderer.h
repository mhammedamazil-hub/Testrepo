#pragma once

#include "renderer.h"
#include <vector>

namespace reality {

// Headless renderer: no actual rendering, logs draw calls for diagnostics
// Used when no GPU/Vulkan is available (Phase 1)
class HeadlessRenderer : public Renderer {
public:
    HeadlessRenderer();
    ~HeadlessRenderer();

    Result<void> init() override;
    Result<void> shutdown() override;
    bool is_initialized() const override { return initialized_; }

    Result<void> render(double dt) override;
    Result<void> submit_draw_call(const DrawCall& call) override;
    Result<void> clear() override;

    const char* name() const override { return "HeadlessRenderer"; }

    Stats get_stats() const override { return stats_; }

    // Get all submitted draw calls (for diagnostics/inspection)
    const std::vector<DrawCall>& get_draw_calls() const { return draw_calls_; }

    // Clear draw call history
    void clear_draw_calls() { draw_calls_.clear(); }

private:
    bool initialized_ = false;
    std::vector<DrawCall> draw_calls_;
    Stats stats_;
};

} // namespace reality
