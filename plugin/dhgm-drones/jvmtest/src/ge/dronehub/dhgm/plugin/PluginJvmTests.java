package ge.dronehub.dhgm.plugin;

import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * plugin-ის pure-Java ლოგიკის ტესტებ (JUnit-ის/Gradle-ის/ATAK SDK-ის გარეშე — Java 8).
 * გაშვება: {@code tools/run-plugin-jvm-tests.sh}. exit code = ჩავარდნების რაოდენობა.
 */
public final class PluginJvmTests {

    private static int failures = 0;

    private static void check(boolean cond, String name) {
        System.out.println((cond ? "PASS " : "FAIL ") + name);
        if (!cond) failures++;
    }

    /** listener, რომ callback-ებ რიგში ჩავარდნენ (reader thread → ტესტ thread). */
    private static final class Recorder implements BridgeTcpClient.Listener {
        final BlockingQueue<String> events = new LinkedBlockingQueue<>();

        @Override
        public void onLine(String line) {
            events.add("LINE " + line);
        }

        @Override
        public void onStateChanged(BridgeTcpClient.State state, String detail, long retryInMs) {
            events.add(state + " " + detail);
        }

        boolean awaitPrefix(String prefix, long timeoutMs) throws InterruptedException {
            long end = System.currentTimeMillis() + timeoutMs;
            long left;
            while ((left = end - System.currentTimeMillis()) > 0) {
                String e = events.poll(left, TimeUnit.MILLISECONDS);
                if (e != null && e.startsWith(prefix)) return true;
            }
            return false;
        }
    }

    private static void hostPortTests() {
        check("192.168.1.5:14550".equals(String.valueOf(HostPortParser.parse("192.168.1.5:14550"))), "parse ip:port");
        check("10.0.0.2:14550".equals(String.valueOf(HostPortParser.parse(" 10.0.0.2 "))), "parse host → default port");
        check("host:14550".equals(String.valueOf(HostPortParser.parse("host:145500"))), "out-of-range port → default");
        check("host:14550".equals(String.valueOf(HostPortParser.parse("host:abc"))), "non-numeric port → default");
        check("mac.local:9000".equals(String.valueOf(HostPortParser.parse("mac.local:9000"))), "hostname:port");
        check(HostPortParser.parse(":14550") == null, "empty host → null");
        check(HostPortParser.parse("") == null, "empty → null");
        check(HostPortParser.parse(null) == null, "null → null");
        check(HostPortParser.parsePort("0", 7) == 7 && HostPortParser.parsePort("65535", 7) == 65535
                && HostPortParser.parsePort("-1", 7) == 7, "parsePort bounds");
    }

    private static void telemetryTests() {
        DroneTelemetry t = new DroneTelemetry();
        check(t.rcLinkLabel() == null, "rc label: unknown → null");
        t.rcRssiPct = 87;
        check("RC 87%".equals(t.rcLinkLabel()), "rc label: 87%");
        t.rcRssiPct = 25;
        check("⚠ RC 25%".equals(t.rcLinkLabel()), "rc label: low link warns");
        check(DroneTelemetry.clampPct(100) == 100 && DroneTelemetry.clampPct(101) == null
                && DroneTelemetry.clampPct(-1) == null, "clampPct bounds");
    }

    private static void backoffTests() {
        check(BridgeTcpClient.nextBackoff(1000) == 2000, "backoff 1s → 2s");
        check(BridgeTcpClient.nextBackoff(8000) == BridgeTcpClient.BACKOFF_MAX_MS, "backoff capped");
        check(BridgeTcpClient.nextBackoff(0) == 2000, "backoff floor");
    }

    private static void clientTests() throws Exception {
        final AtomicBoolean uncaught = new AtomicBoolean(false);
        Thread.setDefaultUncaughtExceptionHandler((t, e) -> {
            uncaught.set(true);
            System.out.println("UNCAUGHT " + e);
        });

        // 1) არავალიდური port — thread-ი არ უნდა ვარდოს (v0.2.x-ში ATAK-ს ხურავდა)
        Recorder r1 = new Recorder();
        BridgeTcpClient c1 = new BridgeTcpClient("127.0.0.1", 99999, r1);
        c1.connect();
        check(r1.awaitPrefix("DISCONNECTED IllegalArgumentException", 3000), "bad port → DISCONNECTED, no crash");
        c1.disconnect();

        try (ServerSocket server = new ServerSocket(0)) {
            Recorder r2 = new Recorder();
            BridgeTcpClient c2 = new BridgeTcpClient("127.0.0.1", server.getLocalPort(), r2);
            c2.connect();
            Socket s = server.accept();
            PrintWriter out = new PrintWriter(new OutputStreamWriter(s.getOutputStream(), StandardCharsets.UTF_8), true);
            check(r2.awaitPrefix("CONNECTED", 2000), "CONNECTED");
            out.println("{\"type\":\"bridge_hello\"}");
            check(r2.awaitPrefix("LINE {\"type\":\"bridge_hello\"}", 2000), "line delivered");

            // 2) სერვერი ხურავს → DISCONNECTED → auto-reconnect
            s.close();
            check(r2.awaitPrefix("DISCONNECTED", 2000), "server close → DISCONNECTED");
            Socket s2 = server.accept();
            check(r2.awaitPrefix("CONNECTED", 4000), "auto-reconnect");

            // 3) heartbeat-ებ კავშირს ცოცხლად ტოვებენ
            PrintWriter out2 = new PrintWriter(new OutputStreamWriter(s2.getOutputStream(), StandardCharsets.UTF_8), true);
            for (int i = 0; i < 7; i++) {
                out2.println("{\"type\":\"bridge_heartbeat\"}");
                Thread.sleep(1000);
            }
            boolean droppedDuringHeartbeats = r2.events.stream().anyMatch(e -> e.startsWith("DISCONNECTED"));
            check(!droppedDuringHeartbeats, "1 Hz heartbeat keeps link alive past read timeout");

            // 4) „ჩუმ" bridge → read timeout
            check(r2.awaitPrefix("DISCONNECTED timeout", BridgeTcpClient.READ_TIMEOUT_MS + 3000), "silent bridge → timeout");

            // 5) disconnect-ის შემდეგ callback-ებ აღარ
            c2.disconnect();
            Thread.sleep(300);
            r2.events.clear();
            Thread.sleep(2500);
            check(r2.events.isEmpty(), "no callbacks after disconnect: " + r2.events);
            s2.close();
        }
        check(!uncaught.get(), "no uncaught exceptions");
    }

    public static void main(String[] args) throws Exception {
        hostPortTests();
        backoffTests();
        telemetryTests();
        clientTests();
        System.out.println(failures == 0 ? "ALL PASS" : ("FAILURES " + failures));
        System.exit(failures);
    }
}
