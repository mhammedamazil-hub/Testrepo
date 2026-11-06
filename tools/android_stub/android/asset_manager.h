#pragma once
#include <cstddef>
#include <sys/types.h>
enum { AASSET_MODE_BUFFER = 2 };
struct AAsset;
struct AAssetManager;
AAsset* AAssetManager_open(AAssetManager*, const char*, int);
off_t AAsset_getLength(AAsset*);
int AAsset_read(AAsset*, void*, size_t);
void AAsset_close(AAsset*);
const void* AAsset_getBuffer(AAsset*);
