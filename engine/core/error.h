#pragma once

#include <string>
#include <variant>
#include <vector>
#include <cstdint>

namespace reality {

// Error codes used across the engine
enum class ErrorCode : uint16_t {
    OK = 0,
    INVALID_INPUT = 1,
    NOT_FOUND = 2,
    ALREADY_EXISTS = 3,
    OUT_OF_MEMORY = 4,
    IO_ERROR = 5,
    SERIALIZATION_ERROR = 6,
    VALIDATION_ERROR = 7,
    BACKEND_UNAVAILABLE = 8,
    NOT_INITIALIZED = 9,
    ALREADY_INITIALIZED = 10,
    RUNTIME_NOT_RUNNING = 11,
    PHYSICS_ERROR = 12,
    ASSET_NOT_FOUND = 13,
    SCENE_NOT_FOUND = 14,
    ENTITY_NOT_FOUND = 15,
    COMPONENT_NOT_FOUND = 16,
    UNSUPPORTED = 17,
};

struct Error {
    ErrorCode code = ErrorCode::OK;
    std::string message;
    std::string context;  // file/function where error occurred

    bool ok() const { return code == ErrorCode::OK; }
};

// Result type: either a value T or an Error
template <typename T>
class Result {
public:
    Result() : value_(T{}) {}
    Result(T value) : value_(std::move(value)) {}
    Result(Error err) : error_(std::move(err)) {}

    bool ok() const { return error_.code == ErrorCode::OK; }
    bool is_error() const { return error_.code != ErrorCode::OK; }

    T& value() { return value_; }
    const T& value() const { return value_; }
    Error& error() { return error_; }
    const Error& error() const { return error_; }

    // Allow implicit conversion to bool
    explicit operator bool() const { return ok(); }

private:
    T value_;
    Error error_;
};

// Convenience: Result<void> for operations that don't return a value
template <>
class Result<void> {
public:
    Result<void>() = default;
    Result<void>(Error err) : error_(std::move(err)) {}

    bool ok() const { return error_.code == ErrorCode::OK; }
    bool is_error() const { return error_.code != ErrorCode::OK; }
    Error& error() { return error_; }
    const Error& error() const { return error_; }

    explicit operator bool() const { return ok(); }

private:
    Error error_;
};

} // namespace reality
