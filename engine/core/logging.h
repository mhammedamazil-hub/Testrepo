#pragma once

#include <string>
#include <mutex>
#include <fstream>
#include <chrono>
#include <iostream>
#include <sstream>

namespace reality {

enum class LogLevel {
    DEBUG,
    INFO,
    WARN,
    ERROR,
    FATAL,
};

class Logger {
public:
    static Logger& instance();

    void set_level(LogLevel level);
    void set_output_file(const std::string& path);
    void set_console(bool enabled);

    void log(LogLevel level, const std::string& message,
             const char* file, int line);

    template <typename... Args>
    void logf(LogLevel level, const char* format, Args&&... args) {
        if (level < current_level_) return;
        std::ostringstream oss;
        oss << format_args(format, std::forward<Args>(args)...);
        log(level, oss.str(), __FILE__, __LINE__);
    }

private:
    Logger() = default;

    std::string format_time() const;
    std::string level_string(LogLevel level) const;

    template <typename T>
    void format_arg(std::ostringstream& oss, T&& arg) {
        oss << arg;
    }

    template <typename T, typename... Rest>
    void format_args(std::ostringstream& oss, const char* format, T&& first, Rest&&... rest) {
        while (*format) {
            if (*format == '{' && *(format + 1) == '}') {
                oss << first;
                format += 2;
                format_args(oss, format, std::forward<Rest>(rest)...);
                return;
            }
            oss << *format++;
        }
    }

    void format_args(std::ostringstream& oss, const char* format) {
        oss << format;
    }

    LogLevel current_level_ = LogLevel::INFO;
    bool console_enabled_ = true;
    std::ofstream file_stream_;
    std::mutex mutex_;
};

#define REALITY_LOG(level, msg) \
    reality::Logger::instance().log(reality::LogLevel::level, msg, __FILE__, __LINE__)

#define REALITY_LOGF(level, fmt, ...) \
    reality::Logger::instance().logf(reality::LogLevel::level, fmt, ##__VA_ARGS__)

} // namespace reality
