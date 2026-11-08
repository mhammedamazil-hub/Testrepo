package app.sourcebook.mobile;

import java.net.URI;
import java.util.Locale;

/** Pure Java URL policy, also executed by the APK build's host-side tests. */
public final class OriginPolicy {
    private OriginPolicy() {}
    public static URI server(String input, boolean allowHttp) {
        try {
            URI uri = new URI(input.trim()).normalize();
            String scheme = uri.getScheme();
            if (!("https".equalsIgnoreCase(scheme) || (allowHttp && "http".equalsIgnoreCase(scheme))))
                throw new IllegalArgumentException("Use HTTPS. HTTP requires explicit insecure-connection consent.");
            if (uri.getHost() == null || uri.getRawUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null)
                throw new IllegalArgumentException("Use a server address without credentials, query, or fragment.");
            if (uri.getPort() == 0 || uri.getPort() > 65535 || uri.getPort() < -1)
                throw new IllegalArgumentException("Invalid server port.");
            if (!(uri.getPath() == null || uri.getPath().isEmpty() || "/".equals(uri.getPath())))
                throw new IllegalArgumentException("Sourcebook must be served at the root of this address.");
            return new URI(scheme.toLowerCase(Locale.ROOT), null, uri.getHost().toLowerCase(Locale.ROOT), uri.getPort(), "/", null, null);
        } catch (java.net.URISyntaxException e) {
            throw new IllegalArgumentException("Enter a valid server URL, such as https://research.example.com.");
        }
    }
    public static boolean sameOrigin(URI origin, String target) {
        if (origin == null || target == null) return false;
        try {
            URI uri = new URI(target);
            return uri.getRawUserInfo() == null && uri.getHost() != null
                && origin.getScheme().equalsIgnoreCase(uri.getScheme())
                && origin.getHost().equalsIgnoreCase(uri.getHost()) && port(origin) == port(uri);
        } catch (Exception e) { return false; }
    }
    private static int port(URI u) { return u.getPort() == -1 ? ("https".equalsIgnoreCase(u.getScheme()) ? 443 : 80) : u.getPort(); }
    public static String filename(String raw) {
        String safe = raw == null ? "download" : raw.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_").trim();
        if (safe.isEmpty() || safe.equals(".") || safe.equals("..")) safe = "download";
        return safe.substring(0, Math.min(120, safe.length()));
    }
}
