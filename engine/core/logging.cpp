#include "logging.h"

#include <iomanip>
#include <ctime>

namespace reality {

Logger& Logger::instance() {
    static Logger logger;
    return logger;
}

void Logger::set_level(LogLevel level) {
    std::lock_guard<std::mutex> lock(mutex_);
    current_level_ = level;
}

void Logger::set_output_file(const std::string& path) {
    std::lock_guard<std::mutex> lock(mutex_);
    file_stream_.open(path, std::ios::out | std::ios::app);
}

void Logger::set_console(bool enabled) {
    std::lock_guard<std::mutex> lock(mutex_);
    console_enabled_ = enabled;
}

std::string Logger::format_time() const {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

std::string Logger::level_string(LogLevel level) const {
    switch (level) {
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO: return "INFO";
        case LogLevel::WARN: return "WARN";
        case LogLevel::ERROR: return "ERROR";
        case LogLevel::FATAL: return "FATAL";
        default: return "UNKNOWN";
    }
}

void Logger::log(LogLevel level, const std::string& message,
                 const char* file, int line) {
    if (level < current_level_) return;

    std::lock_guard<std::mutex> lock(mutex_);

    std::ostringstream oss;
    oss << "[" << format_time() << "] [" << level_string(level) << "] "
        << message << " (" << file << ":" << line << ")";

    std::string output = oss.str();

    if (console_enabled_) {
        std::cout << output << std::endl;
    }

    if (file_stream_.is_open()) {
        file_stream_ << output << std::endl;
        file_stream_.flush();
    }
}

} // namespace reality
