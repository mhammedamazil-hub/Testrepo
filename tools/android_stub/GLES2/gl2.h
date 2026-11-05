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
#define GL_UNSIGNED_BYTE 0x1401
#define GL_UNSIGNED_SHORT 0x1403
#define GL_FLOAT 0x1406
#define GL_BYTE 0x1400
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
void glDrawElements(GLenum, GLsizei, GLenum, const void*); void glDrawArrays(GLenum, GLint, GLsizei);
void glEnable(GLenum); void glDisable(GLenum); void glDepthFunc(GLenum); void glDepthMask(GLboolean);
void glClear(GLuint); void glClearColor(GLfloat, GLfloat, GLfloat, GLfloat); void glViewport(GLint, GLint, GLsizei, GLsizei);
void glBlendFunc(GLenum, GLenum);
