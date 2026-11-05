// Minimal JNI shim used ONLY by the local syntax check of the NDK sources.
// The real build includes the NDK's jni.h; nothing here ships in the APK.
#pragma once
#include <cstdint>
typedef int8_t jboolean;
typedef int32_t jint;
typedef int64_t jlong;
typedef float jfloat;
typedef void* jobject;
typedef void* jclass;
typedef void* jstring;
#define JNI_FALSE 0
#define JNI_TRUE 1
struct JNIEnv {
    jstring NewStringUTF(const char*) const { return nullptr; }
};
#define JNIEXPORT
#define JNICALL
