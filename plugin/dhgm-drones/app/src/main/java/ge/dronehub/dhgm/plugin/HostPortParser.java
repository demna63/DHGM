package ge.dronehub.dhgm.plugin;

/**
 * bridge-ის {@code host[:port]} მისამართის პარსინგი — pure Java (Android/ATAK-ის
 * დამოკიდებულებების გარეშე), რომ JVM-ზე ტესტირდეს ({@code tools/run-plugin-jvm-tests.sh}).
 */
public final class HostPortParser {

    /** default plugin TCP port (bridge {@code --plugin-tcp} / GCS „Plugin TCP პორტი"). */
    public static final int DEFAULT_PORT = 14550;

    private HostPortParser() {
    }

    /** host:port-ის პარსინგის შედეგი (immutable). */
    public static final class HostPort {
        public final String host;
        public final int port;

        HostPort(String host, int port) {
            this.host = host;
            this.port = port;
        }

        @Override
        public String toString() {
            return host + ":" + port;
        }
    }

    /**
     * {@code host[:port]} → {@link HostPort}; null თუ host ცარიელია.
     * არავალიდურ/დიაპაზონის გარეთ port → {@link #DEFAULT_PORT}.
     */
    public static HostPort parse(String text) {
        if (text == null) return null;
        String t = text.trim();
        String host = t;
        int port = DEFAULT_PORT;
        int colon = t.lastIndexOf(':');
        if (colon >= 0) {
            host = t.substring(0, colon).trim();
            port = parsePort(t.substring(colon + 1), DEFAULT_PORT);
        }
        return host.isEmpty() ? null : new HostPort(host, port);
    }

    /**
     * TCP port-ის ვალიდური პარსინგი.
     *
     * <p>დიაპაზონის გარეთ port ({@code InetSocketAddress}-ზე {@link IllegalArgumentException})
     * reader thread-ზე uncaught-ი იყო და მთელ ATAK პროცესს ხურავდა (v0.2.x).
     *
     * @return port [1, 65535] ან {@code fallback}, თუ ტექსტი არავალიდურია.
     */
    public static int parsePort(String text, int fallback) {
        if (text == null) return fallback;
        try {
            int p = Integer.parseInt(text.trim());
            return (p >= 1 && p <= 65535) ? p : fallback;
        } catch (NumberFormatException e) {
            return fallback;
        }
    }
}
