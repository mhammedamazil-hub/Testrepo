package app.sourcebook.mobile;
import java.net.URI;
public final class OriginPolicyTest {
    private static void check(boolean ok) { if(!ok)throw new AssertionError(); }
    private static void rejects(String value,boolean http){try{OriginPolicy.server(value,http);throw new AssertionError("Accepted: "+value);}catch(IllegalArgumentException expected){}}
    public static void main(String[] args){
        URI a=OriginPolicy.server("https://research.example.com",false);
        check(OriginPolicy.sameOrigin(a,"https://research.example.com:443/api/notebooks"));
        check(!OriginPolicy.sameOrigin(a,"http://research.example.com/"));
        check(!OriginPolicy.sameOrigin(a,"https://research.example.com.attacker.invalid/"));
        check(!OriginPolicy.sameOrigin(a,"https://user:password@research.example.com/"));
        check(!OriginPolicy.sameOrigin(a,"https://research.example.com:8443/"));
        check(!OriginPolicy.sameOrigin(a,"file:///etc/passwd"));
        rejects("http://192.168.1.2:3000",false);
        check(OriginPolicy.server("http://192.168.1.2:3000",true).getPort()==3000);
        rejects("https://user:secret@example.com/",false);rejects("https://example.com/subpath",false);
        rejects("https://example.com/?token=secret",false);rejects("javascript:alert(1)",true);
        rejects("https://example.com:99999",false);rejects("file:///data/local/tmp",true);
        check(OriginPolicy.filename("../../private/test.mp3").equals(".._.._private_test.mp3"));
        check(OriginPolicy.filename("..").equals("download"));
        System.out.println("OriginPolicy checks passed");
    }
}
