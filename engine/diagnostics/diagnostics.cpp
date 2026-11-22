#include "diagnostics.h"
#include <sstream>

namespace reality {

std::string DiagnosticsCollector::to_json() const {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"uptime_seconds\": " << diag_.uptime_seconds << ",\n";
    oss << "  \"frame_count\": " << diag_.frame_count << ",\n";
    oss << "  \"average_fps\": " << diag_.average_fps << ",\n";
    oss << "  \"physics_simulation_time_ms\": " << diag_.physics_simulation_time_ms << ",\n";
    oss << "  \"entity_count\": " << diag_.entity_count << ",\n";
    oss << "  \"physics_body_count\": " << diag_.physics_body_count << ",\n";
    oss << "  \"draw_call_count\": " << diag_.draw_call_count << ",\n";
    oss << "  \"custom_metrics\": {\n";
    bool first = true;
    for (const auto& [key, value] : diag_.custom_metrics) {
        if (!first) oss << ",\n";
        first = false;
        oss << "    \"" << key << "\": \"" << value << "\"";
    }
    oss << "\n  }\n";
    oss << "}\n";
    return oss.str();
}

} // namespace reality
