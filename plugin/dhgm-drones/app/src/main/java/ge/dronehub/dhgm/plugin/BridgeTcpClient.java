package ge.dronehub.dhgm.plugin;

import com.atakmap.coremap.log.Log;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;

/**
 * bridge-ის TCP JSON stream-ის მკითხველი (newline-delimited), auto-reconnect-ით.
 *
 * <p>Thread მოდელი: ყველა callback ({@link Listener}) <b>reader thread-ზე</b> ხდება —
 * UI-ცვლილებისთვის listener-ი main thread-ზე უნდა გადაიტანოს (post).
 *
 * <p>„ჩუმად" მკვდარ bridge (Wi-Fi drop, FIN-ის გარეშე) {@link #READ_TIMEOUT_MS}-ით
 * აღმოჩნდება: bridge 1 Hz-ზე {@code bridge_heartbeat}-ს აგზავნის.
 * reconnect exponential backoff-ით: {@link #BACKOFF_MIN_MS} → {@link #BACKOFF_MAX_MS}.
 */
public final class BridgeTcpClient {

    private static final String TAG = "BridgeTcpClient";

    static final int CONNECT_TIMEOUT_MS = 3000;
    /** heartbeat 1 Hz → 5 წმ სიჩუმე = კავშირი მკვდარია. */
    static final int READ_TIMEOUT_MS = 5000;
    static final long BACKOFF_MIN_MS = 1000L;
    static final long BACKOFF_MAX_MS = 10000L;

    /** კავშირის მდგომარეობა. */
    public enum State { CONNECTING, CONNECTED, DISCONNECTED }

    /** reader thread-ზე გამოძახდება. */
    public interface Listener {
        void onLine(String line);

        /**
         * @param detail DISCONNECTED-ზე შეცდომის მოკლე აღწერა; სხვა შემთხვევაში null.
         * @param retryInMs DISCONNECTED-ზე შემდეგ მცდელობამდე დრო; სხვა შემთხვევაში 0.
         */
        void onStateChanged(State state, String detail, long retryInMs);
    }

    private final String host;
    private final int port;
    private final Listener listener;
    private volatile boolean running;
    private volatile Socket socket;
    private Thread readerThread;

    public BridgeTcpClient(String host, int port, Listener listener) {
        if (listener == null) throw new IllegalArgumentException("listener == null");
        this.host = host;
        this.port = port;
        this.listener = listener;
    }

    public synchronized void connect() {
        if (running) {
            return;
        }
        running = true;
        readerThread = new Thread(this::readLoop, "dhgm-bridge-tcp");
        readerThread.setDaemon(true);
        readerThread.start();
    }

    /** idempotent; disconnect-ის შემდეგ listener-ი ახალ callback-ებს აღარ იღებს. */
    public synchronized void disconnect() {
        running = false;
        closeQuietly(socket);
        if (readerThread != null) {
            readerThread.interrupt();
            readerThread = null;
        }
    }

    /**
     * backoff-ის შემდეგ მნიშვნელობა: ×2, ზედა ზღვარ {@link #BACKOFF_MAX_MS}.
     */
    static long nextBackoff(long currentMs) {
        return Math.min(Math.max(currentMs, BACKOFF_MIN_MS) * 2L, BACKOFF_MAX_MS);
    }

    private void readLoop() {
        long backoffMs = BACKOFF_MIN_MS;
        boolean firstAttempt = true;
        while (running) {
            if (firstAttempt) {
                listener.onStateChanged(State.CONNECTING, null, 0);
                firstAttempt = false;
            }
            String detail;
            final Socket s = new Socket();
            socket = s;
            try {
                if (!running) break;  // disconnect() socket-ის მინიჭებამდე
                s.connect(new InetSocketAddress(host, port), CONNECT_TIMEOUT_MS);
                s.setTcpNoDelay(true);
                s.setSoTimeout(READ_TIMEOUT_MS);
                if (!running) break;
                listener.onStateChanged(State.CONNECTED, null, 0);
                backoffMs = BACKOFF_MIN_MS;
                BufferedReader br = new BufferedReader(
                        new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
                String line;
                while ((line = br.readLine()) != null) {
                    if (!running) break;
                    listener.onLine(line);
                }
                detail = "bridge closed connection";
            } catch (SocketTimeoutException e) {
                detail = "timeout";
            } catch (IOException e) {
                detail = e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName();
            } catch (RuntimeException e) {
                // defense-in-depth: IllegalArgumentException/SecurityException და ა.შ. —
                // background thread-ზე uncaught exception მთელ ATAK პროცესს ხურავს.
                Log.w(TAG, "bridge tcp (runtime): " + e);
                detail = e.getClass().getSimpleName();
            } finally {
                closeQuietly(s);
                if (socket == s) socket = null;
            }
            if (!running) break;
            Log.d(TAG, "bridge tcp " + host + ":" + port + ": " + detail
                    + " — retry in " + backoffMs + "ms");
            listener.onStateChanged(State.DISCONNECTED, detail, backoffMs);
            try {
                Thread.sleep(backoffMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
            backoffMs = nextBackoff(backoffMs);
        }
    }

    private static void closeQuietly(Socket s) {
        if (s != null) {
            try {
                s.close();
            } catch (IOException ignored) {
            }
        }
    }
}
