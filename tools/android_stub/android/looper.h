#pragma once
#include <cstdint>
struct android_app;
struct android_poll_source {
    int32_t id;
    struct android_app* app;
    void (*process)(struct android_app* app, struct android_poll_source* source);
};
struct ALooper;
enum { ALOOPER_POLL_WAKE = -1 };
int ALooper_pollOnce(int, int*, int*, void**);
