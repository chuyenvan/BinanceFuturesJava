#!/usr/bin/env python3
"""In PID tien trinh python3 co argv[1] ket thuc bang ten script cho truoc (doc /proc, khong khop chuoi lenh shell)."""
import os, sys
name = sys.argv[1]
for d in os.listdir("/proc"):
    if d.isdigit():
        try:
            a = open("/proc/%s/cmdline" % d, "rb").read().split(b"\0")
        except Exception:  # noqa: BLE001
            continue
        if len(a) > 1 and a[0].endswith(b"python3") and a[1].endswith(name.encode()):
            sys.stdout.write(d + "\n")
