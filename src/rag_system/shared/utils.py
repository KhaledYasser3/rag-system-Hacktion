"""
Shared utility helper functions.
"""

import sys

def safe_print(*args, **kwargs) -> None:
    """Safe print replacement handling console encoding gracefully."""
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    msg = sep.join(str(a) for a in args) + end
    msg = (msg
           .replace("✅", "[OK]")
           .replace("⚠️", "[WARN]")
           .replace("❌", "[FAIL]")
           .replace("✓", "[PASS]"))
    try:
        sys.stdout.write(msg)
        sys.stdout.flush()
    except UnicodeEncodeError:
        sys.stdout.buffer.write(msg.encode("ascii", errors="replace"))
        sys.stdout.flush()
