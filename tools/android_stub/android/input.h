#pragma once
#include <cstdint>
#include <cstddef>
struct AInputEvent;
struct android_app;
struct android_input_buffer {
    AInputEvent** motionEvents;
    uint64_t motionEventsCount;
    AInputEvent** keyEvents;
    uint64_t keyEventsCount;
};
android_input_buffer* android_app_swap_input_buffers(android_app*);
void android_app_clear_motion_events(android_input_buffer*);
void android_app_clear_key_events(android_input_buffer*);
// motion
enum {
    AINPUT_EVENT_TYPE_KEY = 1,
    AINPUT_EVENT_TYPE_MOTION = 2,
    AMOTION_EVENT_ACTION_MASK = 0xff,
    AMOTION_EVENT_ACTION_DOWN = 0,
    AMOTION_EVENT_ACTION_UP = 1,
    AMOTION_EVENT_ACTION_MOVE = 2,
    AMOTION_EVENT_ACTION_CANCEL = 3,
    AMOTION_EVENT_ACTION_POINTER_DOWN = 5,
    AMOTION_EVENT_ACTION_POINTER_UP = 6,
    AMOTION_EVENT_ACTION_POINTER_INDEX_MASK = 0xff00,
    AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT = 8,
    AKEY_EVENT_ACTION_DOWN = 0,
    AKEYCODE_BACK = 4,
};
int32_t AInputEvent_getType(const AInputEvent*);
int32_t AMotionEvent_getAction(const AInputEvent*);
size_t AMotionEvent_getPointerCount(const AInputEvent*);
int32_t AMotionEvent_getPointerId(const AInputEvent*, size_t);
float AMotionEvent_getX(const AInputEvent*, size_t);
float AMotionEvent_getY(const AInputEvent*, size_t);
int32_t AKeyEvent_getAction(const AInputEvent*);
int32_t AKeyEvent_getKeyCode(const AInputEvent*);
