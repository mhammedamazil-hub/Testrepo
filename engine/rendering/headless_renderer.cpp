#include "headless_renderer.h"
#include "core/logging.h"

namespace reality {

HeadlessRenderer::HeadlessRenderer() = default;
HeadlessRenderer::~HeadlessRenderer() = default;

Result<void> HeadlessRenderer::init() {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "HeadlessRenderer already initialized",
                               "headless_renderer.cpp:HeadlessRenderer::init"});
    }

    initialized_ = true;
    stats_ = Stats{};
    draw_calls_.clear();

    REALITY_LOG(INFO, "HeadlessRenderer: initialized (no GPU rendering)");
    return Result<void>();
}

Result<void> HeadlessRenderer::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "HeadlessRenderer not initialized",
                               "headless_renderer.cpp:HeadlessRenderer::shutdown"});
    }

    draw_calls_.clear();
    stats_ = Stats{};
    initialized_ = false;

    REALITY_LOG(INFO, "HeadlessRenderer: shutdown complete");
    return Result<void>();
}

Result<void> HeadlessRenderer::render(double dt) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "HeadlessRenderer not initialized",
                               "headless_renderer.cpp:HeadlessRenderer::render"});
    }

    stats_.frame_time_ms = 0.0;  // No rendering, no frame time
    stats_.draw_calls = static_cast<uint32_t>(draw_calls_.size());
    stats_.triangles = 0;

    return Result<void>();
}

Result<void> HeadlessRenderer::submit_draw_call(const DrawCall& call) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "HeadlessRenderer not initialized",
                               "headless_renderer.cpp:HeadlessRenderer::submit_draw_call"});
    }

    draw_calls_.push_back(call);
    stats_.draw_calls = static_cast<uint32_t>(draw_calls_.size());

    REALITY_LOG(DEBUG, "HeadlessRenderer: draw call mesh=" + call.mesh_id +
                   " material=" + call.material_id);
    return Result<void>();
}

Result<void> HeadlessRenderer::clear() {
    draw_calls_.clear();
    stats_.draw_calls = 0;
    stats_.triangles = 0;
    return Result<void>();
}

} // namespace reality
