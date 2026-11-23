#include "config.h"
#include "logging.h"

#include <fstream>
#include <sstream>

namespace reality {

bool Config::load(const std::filesystem::path& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        REALITY_LOG(WARN, "Config: cannot open " + path.string());
        return false;
    }

    // Simple JSON key-value parser (flat object only)
    std::string content((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    file.close();

    // Very basic JSON parsing: { "key": value, ... }
    size_t pos = 0;
    while (pos < content.size()) {
        // Skip whitespace
        while (pos < content.size() && std::isspace(content[pos])) ++pos;
        if (pos >= content.size()) break;
        if (content[pos] == '{' || content[pos] == '}' || content[pos] == ',') {
            ++pos;
            continue;
        }

        // Parse key
        if (content[pos] != '"') break;
        ++pos;
        std::string key;
        while (pos < content.size() && content[pos] != '"') {
            key += content[pos++];
        }
        if (pos >= content.size()) break;
        ++pos; // skip closing quote

        // Skip colon
        while (pos < content.size() && std::isspace(content[pos])) ++pos;
        if (pos >= content.size() || content[pos] != ':') break;
        ++pos;

        // Parse value
        while (pos < content.size() && std::isspace(content[pos])) ++pos;
        if (pos >= content.size()) break;

        if (content[pos] == '"') {
            // String value
            ++pos;
            std::string value;
            while (pos < content.size() && content[pos] != '"') {
                value += content[pos++];
            }
            set<std::string>(key, value);
            if (pos < content.size()) ++pos;
        } else if (content[pos] == 't' || content[pos] == 'f') {
            // Boolean
            bool val = (content[pos] == 't');
            set<bool>(key, val);
            pos += (val ? 4 : 5); // "true" or "false"
        } else if (content[pos] == 'n') {
            // null
            set<std::string>(key, std::string("null"));
            pos += 4;
        } else {
            // Number
            std::string num;
            while (pos < content.size() &&
                   (std::isdigit(content[pos]) || content[pos] == '.' ||
                    content[pos] == '-' || content[pos] == 'e' ||
                    content[pos] == 'E' || content[pos] == '+')) {
                num += content[pos++];
            }
            try {
                if (num.find('.') != std::string::npos) {
                    set<double>(key, std::stod(num));
                } else {
                    set<int64_t>(key, std::stoll(num));
                }
            } catch (...) {
                set<std::string>(key, num);
            }
        }
    }

    REALITY_LOG(INFO, "Config: loaded " + path.string());
    return true;
}

bool Config::save(const std::filesystem::path& path) const {
    std::ofstream file(path);
    if (!file.is_open()) {
        REALITY_LOG(ERROR, "Config: cannot write " + path.string());
        return false;
    }

    file << "{\n";
    bool first = true;
    for (const auto& [key, val] : values_) {
        if (!first) file << ",\n";
        first = false;
        file << "  \"" << key << "\": ";

        if (val.type() == typeid(std::string)) {
            file << "\"" << std::any_cast<std::string>(val) << "\"";
        } else if (val.type() == typeid(bool)) {
            file << (std::any_cast<bool>(val) ? "true" : "false");
        } else if (val.type() == typeid(int64_t)) {
            file << std::any_cast<int64_t>(val);
        } else if (val.type() == typeid(double)) {
            file << std::any_cast<double>(val);
        } else {
            file << "null";
        }
    }
    file << "\n}\n";
    file.close();

    REALITY_LOG(INFO, "Config: saved " + path.string());
    return true;
}

} // namespace reality
