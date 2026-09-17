package org.json;

/**
 * JVM-ტესტის compile-only stub (Android-ის org.json JVM-ზე არ არის).
 * {@code DroneTelemetry.fromJson} ტესტებში არ იძახება — მხოლოდ pure მეთოდებ.
 */
public class JSONObject {
    public String optString(String k) { throw new UnsupportedOperationException(); }
    public String optString(String k, String d) { throw new UnsupportedOperationException(); }
    public int optInt(String k) { throw new UnsupportedOperationException(); }
    public int optInt(String k, int d) { throw new UnsupportedOperationException(); }
    public double optDouble(String k) { throw new UnsupportedOperationException(); }
    public double optDouble(String k, double d) { throw new UnsupportedOperationException(); }
    public boolean has(String k) { throw new UnsupportedOperationException(); }
}
