#pragma once

#include <string>
#include <map>
#include "core/error.h"

namespace reality {

struct Diagnostics {
    double uptime_seconds = 0.0;
    uint64_t frame_count = 0;
    double average_fps = 0.0;
    double physics_simulation_time_ms = 0.0;
    uint32_t entity_count = 0;
    uint32_t physics_body_count = 0;
    uint32_t draw_call_count = 0;
    std::map<std::string, std::string> custom_metrics;
};

class DiagnosticsCollector {
public:
    DiagnosticsCollector() = default;
    ~DiagnosticsCollector() = default;

    void set_uptime(double seconds) { diag_.uptime_seconds = seconds; }
    void set_frame_count(uint64_t count) { diag_.frame_count = count; }
    void set_average_fps(double fps) { diag_.average_fps = fps; }
    void set_physics_time(double ms) { diag_.physics_simulation_time_ms = ms; }
    void set_entity_count(uint32_t count) { diag_.entity_count = count; }
    void set_physics_body_count(uint32_t count) { diag_.physics_body_count = count; }
    void set_draw_call_count(uint32_t count) { diag_.draw_call_count = count; }
    void add_custom_metric(const std::string& key, const std::string& value) {
        diag_.custom_metrics[key] = value;
    }

    const Diagnostics& get() const { return diag_; }

    // Serialize to JSON
    std::string to_json() const;

private:
    Diagnostics diag_;
};

} // namespace reality
