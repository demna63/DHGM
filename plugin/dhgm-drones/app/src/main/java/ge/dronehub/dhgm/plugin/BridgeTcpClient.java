package ge.dronehub.dhgm.plugin;

import com.atakmap.coremap.log.Log;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * bridge-ის TCP JSON stream-ის მკითხველი (newline-delimited).
 * ფაზა 2b: telemetry → UI ბარათები.
 */
public class BridgeTcpClient {

    private static final String TAG = "BridgeTcpClient";

    public interface LineListener {
        void onLine(String line);
    }

    private final String host;
    private final int port;
    private final LineListener listener;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private Thread readerThread;
    private Socket socket;

    public BridgeTcpClient(String host, int port, LineListener listener) {
        this.host = host;
        this.port = port;
        this.listener = listener;
    }

    public synchronized void connect() {
        if (running.get()) {
            return;
        }
        running.set(true);
        readerThread = new Thread(this::readLoop, "dhgm-bridge-tcp");
        readerThread.setDaemon(true);
        readerThread.start();
    }

    public synchronized void disconnect() {
        running.set(false);
        closeSocket();
        if (readerThread != null) {
            readerThread.interrupt();
            readerThread = null;
        }
    }

    private void readLoop() {
        while (running.get()) {
            try {
                socket = new Socket();
                socket.connect(new InetSocketAddress(host, port), 3000);
                socket.setTcpNoDelay(true);
                BufferedReader br = new BufferedReader(
                        new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
                String line;
                while (running.get() && (line = br.readLine()) != null) {
                    if (listener != null) {
                        listener.onLine(line);
                    }
                }
            } catch (IOException e) {
                Log.d(TAG, "bridge tcp: " + e.getMessage());
            } finally {
                closeSocket();
            }
            if (running.get()) {
                try {
                    Thread.sleep(2000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private void closeSocket() {
        if (socket != null) {
            try {
                socket.close();
            } catch (IOException ignored) {
            }
            socket = null;
        }
    }
}
