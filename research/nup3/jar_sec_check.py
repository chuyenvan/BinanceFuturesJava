#!/usr/bin/env python3
"""NUP3: kiem bao mat jar TRUOC upload (KHONG in noi dung chuoi nghi van, chi dem / ten JVM).
1) PrivateConfig.class: moi chuoi in duoc >= 20 ky tu phai la ten JVM (class/descriptor; bo 1 byte do dai dung truoc)
   — dem chuoi KHAC phai = 0. Khong co chuoi >= 64 (do dai key/secret Binance).
2) Toan jar: dem run [A-Za-z0-9]{64} trong moi .class. Lop com/binance/** phai = 0. Lop thu vien chi chap nhan
   trong gnu/crypto/** (hang so S-box/hash, co san trong jar tham chieu cc0f9d11). In TEN class, khong in noi dung.
Usage: python3 -I jar_sec_check.py <jar> [out.json]
"""
import json
import re
import sys
import zipfile

jar = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None
z = zipfile.ZipFile(jar)
pc = z.read("com/binance/chuyennd/config/PrivateConfig.class")
runs = re.findall(rb"[\x20-\x7e]{4,}", pc)
long_runs = [r for r in runs if len(r) >= 20]
jvm = re.compile(rb"^[A-Za-z0-9_/$;()\[<>.]+$")
safe = []
for r in long_runs:
    t = r[1:] if not r[:1].isalnum() else r          # byte do dai u2 cua CONSTANT_Utf8 co the in duoc
    if jvm.match(t) and (b"/" in t or b";" in t):
        safe.append(t.decode())
unsafe_n = len(long_runs) - len(safe)
lens = sorted(set(len(r) for r in runs))
key64 = re.compile(rb"[A-Za-z0-9]{64}")
hits = {}
n_class = 0
for name in z.namelist():
    if not name.endswith(".class"):
        continue
    n_class += 1
    c = len(key64.findall(z.read(name)))
    if c:
        hits[name] = c
own = sorted(n for n in hits if n.startswith("com/binance/"))
lib_bad = sorted(n for n in hits if not n.startswith("com/binance/") and not n.startswith("gnu/crypto/"))
res = {"jar": jar, "privateconfig_runs_ge20": len(long_runs), "privateconfig_runs_ge20_jvm_names": safe,
       "privateconfig_runs_ge20_other": unsafe_n, "privateconfig_max_run_len": max(lens) if lens else 0,
       "classes_scanned": n_class, "com_binance_classes_with_64alnum": own,
       "lib_classes_with_64alnum_gnu_crypto": len(hits) - len(own) - len(lib_bad),
       "lib_classes_with_64alnum_other": lib_bad,
       "ok": unsafe_n == 0 and (max(lens) if lens else 0) < 64 and not own and not lib_bad}
print(json.dumps(res, indent=1))
if out:
    json.dump(res, open(out, "w"), indent=1)
sys.exit(0 if res["ok"] else 3)
