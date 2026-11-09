package dev.tabletagent;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;

final class Fingerprints {
    private Fingerprints() {}
    static String sha256(byte[] key) throws NoSuchAlgorithmException {
        return "SHA256:" + Base64.getEncoder().withoutPadding().encodeToString(MessageDigest.getInstance("SHA-256").digest(key));
    }
}
