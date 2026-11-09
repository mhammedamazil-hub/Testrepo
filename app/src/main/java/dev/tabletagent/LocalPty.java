package dev.tabletagent;

final class LocalPty {
    static { System.loadLibrary("localpty"); }
    private LocalPty() {}
    static native long[] start(String executable, String home, String cwd, String caFile, int cols, int rows);
    static native int read(int fd, byte[] buffer);
    static native void write(int fd, byte[] data);
    static native void resize(int fd, int cols, int rows);
    static native void stop(int pid);
    static native int finish(int fd, int pid);
}
