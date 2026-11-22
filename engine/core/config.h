#pragma once

#include <string>
#include <map>
#include <any>
#include <optional>
#include <filesystem>

namespace reality {

class Config {
public:
    Config() = default;

    // Load from JSON file (simple key-value JSON)
    bool load(const std::filesystem::path& path);

    // Save to JSON file
    bool save(const std::filesystem::path& path) const;

    // Get a value by key
    template <typename T>
    std::optional<T> get(const std::string& key) const {
        auto it = values_.find(key);
        if (it == values_.end()) return std::nullopt;
        try {
            return std::any_cast<T>(it->second);
        } catch (const std::bad_any_cast&) {
            return std::nullopt;
        }
    }

    // Set a value by key
    template <typename T>
    void set(const std::string& key, T value) {
        values_[key] = value;
    }

    bool has(const std::string& key) const {
        return values_.find(key) != values_.end();
    }

    void remove(const std::string& key) {
        values_.erase(key);
    }

    const std::map<std::string, std::any>& all() const { return values_; }

private:
    std::map<std::string, std::any> values_;
};

} // namespace reality
