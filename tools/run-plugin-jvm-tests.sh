#!/usr/bin/env bash
# DHGM plugin — pure-Java ლოგიკის JVM ტესტებ (BridgeTcpClient, HostPortParser).
# ATAK SDK/Gradle/Android-ის გარეშე: javac + stub Log. Java 8+ (CI: temurin 8).
#   bash tools/run-plugin-jvm-tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=plugin/dhgm-drones/app/src/main/java/ge/dronehub/dhgm/plugin
TEST=plugin/dhgm-drones/jvmtest/src
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

command -v javac >/dev/null || { echo "✗ javac არ მოიძებნა (JDK საჭიროა)"; exit 1; }

javac -encoding UTF-8 -Xlint:all -d "$OUT" \
  "$SRC/BridgeTcpClient.java" \
  "$SRC/HostPortParser.java" \
  "$TEST/com/atakmap/coremap/log/Log.java" \
  "$TEST/ge/dronehub/dhgm/plugin/PluginJvmTests.java"

java -cp "$OUT" ge.dronehub.dhgm.plugin.PluginJvmTests
