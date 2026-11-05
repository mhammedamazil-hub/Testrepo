#pragma once
#include "android/asset_manager.h"
#include "jni.h"
AAssetManager* AAssetManager_fromJava(JNIEnv*, jobject);
