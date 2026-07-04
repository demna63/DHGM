#!/usr/bin/env python3
"""FileSystemUtils.legacyFindMountRootDirs — proc.waitFor() deadlock fix (ATAK PR#329)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER = "DHGM: drain mount stdout before waitFor"
PATTERN = re.compile(
    r"(Process proc = new ProcessBuilder\(\)\.command\(\"mount\"\)\s*"
    r"\.redirectErrorStream\(true\)\.start\(\);\s*)"
    r"proc\.waitFor\(\);\s*"
    r"(InputStream is = proc\.getInputStream\(\);)",
    re.MULTILINE,
)


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if not PATTERN.search(text):
        return False
    replacement = (
        r"\1\2\n"
        f"            // {MARKER}\n"
        r"            java.io.ByteArrayOutputStream mountOut = new java.io.ByteArrayOutputStream();"
        r"\n            byte[] buf = new byte[4096];"
        r"\n            int n;"
        r"\n            while ((n = is.read(buf)) != -1) {"
        r"\n                mountOut.write(buf, 0, n);"
        r"\n            }"
        r"\n            proc.waitFor();"
        r"\n            java.io.BufferedReader r = new java.io.BufferedReader("
        r"\n                    new java.io.InputStreamReader("
        r"\n                            new java.io.ByteArrayInputStream(mountOut.toByteArray()),"
        r"\n                            UTF8_CHARSET));"
    )
    # Remove duplicate BufferedReader declaration that follows
    new_text = PATTERN.sub(replacement, text, count=1)
    new_text = re.sub(
        r"\n\s*BufferedReader r = new BufferedReader\(\s*"
        r"\n\s*new InputStreamReader\(is, UTF8_CHARSET\)\);",
        "",
        new_text,
        count=1,
    )
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: fix-mount-deadlock.py <FileSystemUtils.java>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"skip: {path} not found", file=sys.stderr)
        return 0
    if patch(path):
        print(f"  ✓ mount deadlock fix applied: {path}")
    else:
        print(f"  ✓ mount deadlock fix already applied or pattern missing: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
