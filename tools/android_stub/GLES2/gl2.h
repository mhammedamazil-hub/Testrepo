// Minimal GLES2 declaration set for the local compile check of game.cpp.
// Every entry mirrors <GLES2/gl2.h>; signatures are what matter, not the enum values.
#pragma once
#include <cstddef>
#include <cstdint>
typedef uint32_t GLenum; typedef uint32_t GLuint; typedef int32_t GLint;
typedef int32_t GLsizei; typedef intptr_t GLintptr; typedef intptr_t GLsizeiptr; typedef uint8_t GLboolean;
typedef uint8_t GLubyte; typedef char GLchar; typedef float GLfloat;
#define GL_FALSE 0
#define GL_TRUE 1
#define GL_VERTEX_SHADER 0x8B31
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_TEXTURE_2D 0x0DE1
#define GL_RGBA 0x1908
#define GL_RGB 0x1907
#define GL_EXTENSIONS 0x1F03
#define GL_MAX_TEXTURE_SIZE 0x0D33
#define GL_UNSIGNED_BYTE 0x1401
#define GL_UNSIGNED_SHORT 0x1403
#define GL_FLOAT 0x1406
#define GL_BYTE 0x1400
#define GL_NEAREST 0x2600
#define GL_LINEAR 0x2601
#define GL_LINEAR_MIPMAP_LINEAR 0x2703
#define GL_REPEAT 0x2901
#define GL_TEXTURE_MIN_FILTER 0x2801
#define GL_TEXTURE_MAG_FILTER 0x2800
#define GL_TEXTURE_WRAP_S 0x2802
#define GL_TEXTURE_WRAP_T 0x2803
#define GL_TEXTURE0 0x84C0
#define GL_ARRAY_BUFFER 0x8892
#define GL_ELEMENT_ARRAY_BUFFER 0x8893
#define GL_STATIC_DRAW 0x88E4
#define GL_DYNAMIC_DRAW 0x88E8
#define GL_DEPTH_TEST 0x0B71
#define GL_LEQUAL 0x0203
#define GL_CULL_FACE 0x0B44
#define GL_TRIANGLES 0x0004
#define GL_TRIANGLE_STRIP 0x0005
#define GL_BLEND 0x0BE2
#define GL_ONE 1
#define GL_SRC_ALPHA 0x0302
#define GL_ONE_MINUS_SRC_ALPHA 0x0303
#define GL_COLOR_BUFFER_BIT 0x4000
#define GL_DEPTH_BUFFER_BIT 0x0100
GLuint glCreateShader(GLenum); void glShaderSource(GLuint, GLsizei, const GLchar* const*, const GLint*);
void glCompileShader(GLuint); void glGetShaderiv(GLuint, GLenum, GLint*);
void glGetShaderInfoLog(GLuint, GLsizei, GLsizei*, GLchar*); void glDeleteShader(GLuint);
GLuint glCreateProgram(void); void glAttachShader(GLuint, GLuint);
void glBindAttribLocation(GLuint, GLuint, const GLchar*); void glLinkProgram(GLuint);
void glGetProgramiv(GLuint, GLenum, GLint*); void glGetProgramInfoLog(GLuint, GLsizei, GLsizei*, GLchar*);
void glDeleteProgram(GLuint); void glUseProgram(GLuint);
GLint glGetUniformLocation(GLuint, const GLchar*);
void glUniform1f(GLint, GLfloat); void glUniform1i(GLint, GLint);
void glUniform3fv(GLint, GLsizei, const GLfloat*); void glUniform4fv(GLint, GLsizei, const GLfloat*);
void glUniformMatrix4fv(GLint, GLsizei, GLboolean, const GLfloat*);
void glGenBuffers(GLsizei, GLuint*); void glBindBuffer(GLenum, GLuint);
void glBufferData(GLenum, GLsizeiptr, const void*, GLenum); void glBufferSubData(GLenum, GLintptr, GLsizeiptr, const void*);
void glEnableVertexAttribArray(GLuint); void glDisableVertexAttribArray(GLuint);
void glVertexAttribPointer(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
void glActiveTexture(GLenum); void glBindTexture(GLenum, GLuint);
void glGenTextures(GLsizei, GLuint*); void glTexImage2D(GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void*);
void glGenerateMipmap(GLenum); void glTexParameteri(GLenum, GLenum, GLint);
void glTexParameterf(GLenum, GLenum, GLfloat);
void glGetIntegerv(GLenum, GLint*); void glGetFloatv(GLenum, GLfloat*);
void glDrawElements(GLenum, GLsizei, GLenum, const void*); void glDrawArrays(GLenum, GLint, GLsizei);
void glEnable(GLenum); void glDisable(GLenum); void glDepthFunc(GLenum); void glDepthMask(GLboolean);
void glClear(GLuint); void glClearColor(GLfloat, GLfloat, GLfloat, GLfloat); void glViewport(GLint, GLint, GLsizei, GLsizei);
void glBlendFunc(GLenum, GLenum);
// ---- framebuffer objects (core in GLES2; used for the HDR/post targets)
#define GL_FRAMEBUFFER 0x8D40
#define GL_RENDERBUFFER 0x8D41
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_DEPTH_ATTACHMENT 0x8D00
#define GL_DEPTH_COMPONENT16 0x81A5
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#define GL_CLAMP_TO_EDGE 0x812F
#define GL_TEXTURE1 0x84C1
#define GL_TEXTURE2 0x84C2
#define GL_TEXTURE3 0x84C3
void glGenFramebuffers(GLsizei, GLuint*); void glBindFramebuffer(GLenum, GLuint);
void glFramebufferTexture2D(GLenum, GLenum, GLenum, GLuint, GLint);
void glGenRenderbuffers(GLsizei, GLuint*); void glBindRenderbuffer(GLenum, GLuint);
void glRenderbufferStorage(GLenum, GLenum, GLsizei, GLsizei);
void glFramebufferRenderbuffer(GLenum, GLenum, GLenum, GLuint);
GLenum glCheckFramebufferStatus(GLenum);
void glDeleteFramebuffers(GLsizei, const GLuint*); void glDeleteRenderbuffers(GLsizei, const GLuint*);
void glDeleteTextures(GLsizei, const GLuint*);
void glDisable(GLenum); void glEnable(GLenum);
#define GL_SCISSOR_TEST 0x0C11
void glScissor(GLint, GLint, GLsizei, GLsizei);
void glUniform2f(GLint, GLfloat, GLfloat);
void glBindTexture(GLenum, GLuint);
#define GL_SHADING_LANGUAGE_VERSION 0x8B8C
#define GL_VENDOR 0x1F00
#define GL_RENDERER 0x1F01
#define GL_HIGH_FLOAT 0x8DF2
const GLubyte* glGetString(GLenum);
void glGetShaderPrecisionFormat(GLenum, GLenum, GLint*, GLint*);
#define GL_NO_ERROR 0
GLenum glGetError(void);
void glReadPixels(GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void*);
#define GL_VERSION 0x1F02
#define GL_STREAM_DRAW 0x88E0
void glDeleteBuffers(GLsizei, const GLuint*);
