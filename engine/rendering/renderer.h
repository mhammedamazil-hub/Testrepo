#pragma once

#include <string>
#include "core/error.h"

namespace reality {

struct DrawCall {
    std::string mesh_id;
    std::string material_id;
    float transform[16];  // 4x4 matrix
};

class Renderer {
public:
    virtual ~Renderer() = default;

    virtual Result<void> init() = 0;
    virtual Result<void> shutdown() = 0;
    virtual bool is_initialized() const = 0;

    // Render a frame
    virtual Result<void> render(double dt) = 0;

    // Submit a draw call
    virtual Result<void> submit_draw_call(const DrawCall& call) = 0;

    // Clear the frame
    virtual Result<void> clear() = 0;

    // Get renderer name
    virtual const char* name() const = 0;

    // Get stats
    struct Stats {
        uint32_t draw_calls = 0;
        uint32_t triangles = 0;
        double frame_time_ms = 0.0;
    };
    virtual Stats get_stats() const = 0;
};

} // namespace reality
