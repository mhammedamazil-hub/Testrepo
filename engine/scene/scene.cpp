#include "scene.h"
#include "core/logging.h"
#include <fstream>
#include <sstream>

namespace reality {

Scene::Scene() = default;
Scene::~Scene() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> Scene::init(const std::string& name) {
    if (initialized_) {
        return Result<void>(Error{ErrorCode::ALREADY_INITIALIZED,
                               "Scene already initialized",
                               "scene.cpp:Scene::init"});
    }

    name_ = name;
    initialized_ = true;
    return Result<void>();
}

Result<void> Scene::shutdown() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
                               "Scene not initialized",
                               "scene.cpp:Scene::shutdown"});
    }

    entities_.clear();
    initialized_ = false;
    return Result<void>();
}

void Scene::add_entity(const SceneEntityData& entity) {
    entities_.push_back(entity);
}

const SceneEntityData* Scene::find_entity(const EntityId& id) const {
    for (const auto& e : entities_) {
        if (e.id == id) return &e;
    }
    return nullptr;
}

std::string Scene::serialize() const {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"name\": \"" << name_ << "\",\n";
    oss << "  \"version\": \"1.0\",\n";
    oss << "  \"entities\": [\n";

    for (size_t i = 0; i < entities_.size(); i++) {
        const auto& e = entities_[i];
        oss << "    {\n";
        oss << "      \"id\": \"" << e.id.to_string() << "\",\n";
        oss << "      \"name\": \"" << e.name << "\",\n";
        oss << "      \"transform\": {\n";
        oss << "        \"position\": [" << e.transform.position[0] << ", " << e.transform.position[1] << ", " << e.transform.position[2] << "],\n";
        oss << "        \"rotation\": [" << e.transform.rotation[0] << ", " << e.transform.rotation[1] << ", " << e.transform.rotation[2] << ", " << e.transform.rotation[3] << "],\n";
        oss << "        \"scale\": [" << e.transform.scale[0] << ", " << e.transform.scale[1] << ", " << e.transform.scale[2] << "]\n";
        oss << "      },\n";
        oss << "      \"components\": {}\n";
        oss << "    }";
        if (i + 1 < entities_.size()) oss << ",";
        oss << "\n";
    }

    oss << "  ],\n";
    oss << "  \"metadata\": {}\n";
    oss << "}\n";

    return oss.str();
}

Result<void> Scene::deserialize(const std::string& json) {
    // Simple JSON parser for our scene format
    // This is a minimal parser that handles our specific format
    entities_.clear();

    // Find entities array
    size_t entities_pos = json.find("\"entities\"");
    if (entities_pos == std::string::npos) {
        return Result<void>(Error{ErrorCode::SERIALIZATION_ERROR,
                               "No entities array in scene JSON",
                               "scene.cpp:Scene::deserialize"});
    }

    size_t array_start = json.find("[", entities_pos);
    size_t array_end = json.find("]", array_start);
    if (array_start == std::string::npos || array_end == std::string::npos) {
        return Result<void>(Error{ErrorCode::SERIALIZATION_ERROR,
                               "Malformed entities array",
                               "scene.cpp:Scene::deserialize"});
    }

    // Parse each entity object
    size_t pos = array_start + 1;
    while (pos < array_end) {
        // Skip whitespace and commas
        while (pos < array_end && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == ',')) pos++;
        if (pos >= array_end) break;
        if (json[pos] != '{') break;

        // Find end of object
        size_t obj_start = pos;
        int depth = 0;
        while (pos < array_end) {
            if (json[pos] == '{') depth++;
            else if (json[pos] == '}') {
                depth--;
                if (depth == 0) break;
            }
            pos++;
        }
        size_t obj_end = pos;
        std::string obj_json = json.substr(obj_start, obj_end - obj_start + 1);

        // Parse fields within object
        SceneEntityData e;
        e.transform = Transform{};

        // Parse id
        size_t id_pos = obj_json.find("\"id\"");
        if (id_pos != std::string::npos) {
            size_t val_start = obj_json.find('"', id_pos + 5);
            size_t val_end = obj_json.find('"', val_start + 1);
            if (val_start != std::string::npos && val_end != std::string::npos) {
                std::string id_str = obj_json.substr(val_start + 1, val_end - val_start - 1);
                e.id = EntityId::from_string(id_str);
            }
        }

        // Parse name
        size_t name_pos = obj_json.find("\"name\"");
        if (name_pos != std::string::npos) {
            size_t val_start = obj_json.find('"', name_pos + 7);
            size_t val_end = obj_json.find('"', val_start + 1);
            if (val_start != std::string::npos && val_end != std::string::npos) {
                e.name = obj_json.substr(val_start + 1, val_end - val_start - 1);
            }
        }

        // Parse transform.position
        size_t pos_pos = obj_json.find("\"position\"");
        if (pos_pos != std::string::npos) {
            size_t arr_start = obj_json.find('[', pos_pos);
            size_t arr_end = obj_json.find(']', arr_start);
            if (arr_start != std::string::npos && arr_end != std::string::npos) {
                std::string arr_str = obj_json.substr(arr_start + 1, arr_end - arr_start - 1);
                sscanf(arr_str.c_str(), "%f, %f, %f",
                       &e.transform.position[0], &e.transform.position[1], &e.transform.position[2]);
            }
        }

        // Parse transform.rotation
        size_t rot_pos = obj_json.find("\"rotation\"");
        if (rot_pos != std::string::npos) {
            size_t arr_start = obj_json.find('[', rot_pos);
            size_t arr_end = obj_json.find(']', arr_start);
            if (arr_start != std::string::npos && arr_end != std::string::npos) {
                std::string arr_str = obj_json.substr(arr_start + 1, arr_end - arr_start - 1);
                sscanf(arr_str.c_str(), "%f, %f, %f, %f",
                       &e.transform.rotation[0], &e.transform.rotation[1],
                       &e.transform.rotation[2], &e.transform.rotation[3]);
            }
        }

        // Parse transform.scale
        size_t scale_pos = obj_json.find("\"scale\"");
        if (scale_pos != std::string::npos) {
            size_t arr_start = obj_json.find('[', scale_pos);
            size_t arr_end = obj_json.find(']', arr_start);
            if (arr_start != std::string::npos && arr_end != std::string::npos) {
                std::string arr_str = obj_json.substr(arr_start + 1, arr_end - arr_start - 1);
                sscanf(arr_str.c_str(), "%f, %f, %f",
                       &e.transform.scale[0], &e.transform.scale[1], &e.transform.scale[2]);
            }
        }

        entities_.push_back(e);
        pos = obj_end + 1;
    }

    REALITY_LOG(INFO, "Scene: deserialized " + std::to_string(entities_.size()) + " entities");
    return Result<void>();
}

Result<void> Scene::save(const std::string& path) {
    std::string json = serialize();
    std::ofstream file(path);
    if (!file.is_open()) {
        return Result<void>(Error{ErrorCode::IO_ERROR,
                               "Cannot write scene file: " + path,
                               "scene.cpp:Scene::save"});
    }
    file << json;
    file.close();
    REALITY_LOG(INFO, "Scene: saved " + std::to_string(entities_.size()) +
                   " entities to " + path);
    return Result<void>();
}

Result<void> Scene::load(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        return Result<void>(Error{ErrorCode::IO_ERROR,
                               "Cannot read scene file: " + path,
                               "scene.cpp:Scene::load"});
    }

    std::string content((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    file.close();

    return deserialize(content);
}

Result<void> Scene::validate() const {
    for (const auto& e : entities_) {
        if (e.id.is_null()) {
            return Result<void>(Error{ErrorCode::VALIDATION_ERROR,
                                   "Entity '" + e.name + "' has null ID",
                                   "scene.cpp:Scene::validate"});
        }
    }
    return Result<void>();
}

} // namespace reality
