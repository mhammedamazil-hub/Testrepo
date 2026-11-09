package dev.tabletagent;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import java.nio.charset.StandardCharsets;

public class FingerprintsTest {
    @Test public void sha256UsesOpenSshStyleUnpaddedBase64() throws Exception {
        assertEquals("SHA256:ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0", Fingerprints.sha256("abc".getBytes(StandardCharsets.UTF_8)));
    }
}
