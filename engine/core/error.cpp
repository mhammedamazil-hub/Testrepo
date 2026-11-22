#include "error.h"

namespace reality {

const char* error_code_string(ErrorCode code) {
    switch (code) {
        case ErrorCode::OK: return "OK";
        case ErrorCode::INVALID_INPUT: return "INVALID_INPUT";
        case ErrorCode::NOT_FOUND: return "NOT_FOUND";
        case ErrorCode::ALREADY_EXISTS: return "ALREADY_EXISTS";
        case ErrorCode::OUT_OF_MEMORY: return "OUT_OF_MEMORY";
        case ErrorCode::IO_ERROR: return "IO_ERROR";
        case ErrorCode::SERIALIZATION_ERROR: return "SERIALIZATION_ERROR";
        case ErrorCode::VALIDATION_ERROR: return "VALIDATION_ERROR";
        case ErrorCode::BACKEND_UNAVAILABLE: return "BACKEND_UNAVAILABLE";
        case ErrorCode::NOT_INITIALIZED: return "NOT_INITIALIZED";
        case ErrorCode::ALREADY_INITIALIZED: return "ALREADY_INITIALIZED";
        case ErrorCode::RUNTIME_NOT_RUNNING: return "RUNTIME_NOT_RUNNING";
        case ErrorCode::PHYSICS_ERROR: return "PHYSICS_ERROR";
        case ErrorCode::ASSET_NOT_FOUND: return "ASSET_NOT_FOUND";
        case ErrorCode::SCENE_NOT_FOUND: return "SCENE_NOT_FOUND";
        case ErrorCode::ENTITY_NOT_FOUND: return "ENTITY_NOT_FOUND";
        case ErrorCode::COMPONENT_NOT_FOUND: return "COMPONENT_NOT_FOUND";
        case ErrorCode::UNSUPPORTED: return "UNSUPPORTED";
        default: return "UNKNOWN";
    }
}

} // namespace reality
