#define _XOPEN_SOURCE 600
#include <jni.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>

static char *value(JNIEnv *e, jstring v) {
    const char *s = (*e)->GetStringUTFChars(e, v, NULL);
    if (!s) return NULL;
    char *copy = strdup(s);
    (*e)->ReleaseStringUTFChars(e, v, s);
    return copy;
}
static char *envvar(const char *name, const char *v) {
    size_t len = strlen(name) + strlen(v) + 2;
    char *out = malloc(len); if (out) snprintf(out, len, "%s=%s", name, v); return out;
}
JNIEXPORT jlongArray JNICALL Java_dev_tabletagent_LocalPty_start(JNIEnv *e, jclass c, jstring executable, jstring home, jstring cwd, jstring ca, jint cols, jint rows) {
    (void)c;
    char *exe = value(e, executable), *home_s = value(e, home), *work = value(e, cwd), *ca_s = value(e, ca);
    if (!exe || !home_s || !work || !ca_s) goto fail;
    char *envp[] = {envvar("HOME", home_s), envvar("TMPDIR", home_s), envvar("SSL_CERT_FILE", ca_s),
                    "PATH=/system/bin:/system/xbin", "TERM=xterm-256color", "LANG=C.UTF-8", "JCODE_NO_TELEMETRY=1", NULL};
    if (!envp[0] || !envp[1] || !envp[2]) { free(envp[0]); free(envp[1]); free(envp[2]); goto fail; }
    int master = posix_openpt(O_RDWR | O_NOCTTY | O_CLOEXEC);
    if (master < 0 || grantpt(master) || unlockpt(master)) { if (master >= 0) close(master); free(envp[0]); free(envp[1]); free(envp[2]); goto fail; }
    char *name = ptsname(master); char *slave = name ? strdup(name) : NULL;
    if (!slave) { close(master); free(envp[0]); free(envp[1]); free(envp[2]); goto fail; }
    struct winsize size = { .ws_col = (unsigned short)cols, .ws_row = (unsigned short)rows };
    ioctl(master, TIOCSWINSZ, &size);
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        int fd = open(slave, O_RDWR);
        if (fd < 0) _exit(126);
        ioctl(fd, TIOCSCTTY, 0);
        dup2(fd, 0); dup2(fd, 1); dup2(fd, 2);
        if (fd > 2) close(fd);
        close(master);
        if (chdir(work) != 0) _exit(126);
        char *argv[] = {exe, NULL};
        execve(exe, argv, envp);
        _exit(127);
    }
    free(slave); free(envp[0]); free(envp[1]); free(envp[2]);
    if (pid < 0) { close(master); goto fail; }
    jlong result[] = {master, pid};
    jlongArray out = (*e)->NewLongArray(e, 2);
    if (!out) { kill(-pid, SIGKILL); close(master); waitpid(pid, NULL, 0); goto fail; }
    (*e)->SetLongArrayRegion(e, out, 0, 2, result);
    free(exe); free(home_s); free(work); free(ca_s); return out;
fail:
    free(exe); free(home_s); free(work); free(ca_s); return NULL;
}
JNIEXPORT jint JNICALL Java_dev_tabletagent_LocalPty_read(JNIEnv *e, jclass c, jint fd, jbyteArray dst) {
    (void)c; jsize n = (*e)->GetArrayLength(e, dst); char *buf = malloc(n); if (!buf) return -1;
    ssize_t result; do { result = read(fd, buf, n); } while (result < 0 && errno == EINTR);
    if (result > 0) (*e)->SetByteArrayRegion(e, dst, 0, result, (jbyte *)buf);
    free(buf); return (jint) result;
}
JNIEXPORT void JNICALL Java_dev_tabletagent_LocalPty_write(JNIEnv *e, jclass c, jint fd, jbyteArray data) {
    (void)c; jsize len = (*e)->GetArrayLength(e, data); jbyte *bytes = (*e)->GetByteArrayElements(e, data, NULL); if (!bytes) return;
    size_t offset = 0; while (offset < (size_t)len) { ssize_t n = write(fd, bytes + offset, len - offset); if (n < 0 && errno == EINTR) continue; if (n <= 0) break; offset += n; }
    (*e)->ReleaseByteArrayElements(e, data, bytes, JNI_ABORT);
}
JNIEXPORT void JNICALL Java_dev_tabletagent_LocalPty_resize(JNIEnv *e, jclass c, jint fd, jint cols, jint rows) {
    (void)e; (void)c; struct winsize size = { .ws_col = (unsigned short)cols, .ws_row = (unsigned short)rows }; ioctl(fd, TIOCSWINSZ, &size);
}
JNIEXPORT void JNICALL Java_dev_tabletagent_LocalPty_stop(JNIEnv *e, jclass c, jint pid) { (void)e; (void)c; if (pid > 0) { kill(-pid, SIGHUP); kill(pid, SIGHUP); } }
JNIEXPORT jint JNICALL Java_dev_tabletagent_LocalPty_finish(JNIEnv *e, jclass c, jint fd, jint pid) {
    (void)e; (void)c; close(fd); int status = 0; while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {} return status;
}
