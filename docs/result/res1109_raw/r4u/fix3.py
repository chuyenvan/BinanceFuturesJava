"""R4u2: sua comment chen giua dong C3LiveRuntime (lam hong bieu thuc)."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
P = "src/main/java/com/binance/chuyennd/c3live/runtime/C3LiveRuntime.java"
s = open(P, "rb").read().decode("utf-8")
old = "scope.entryBlocked(   // [V12 R4u2] TAT => chi scope"
assert s.count(old) == 1
s = s.replace(old, "scope.entryBlocked(")
old2 = "System.currentTimeMillis()))   // [V12 R4 R2]"
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, "System.currentTimeMillis()))   // [V12 R4 R2] [V12 R4u2 blocksC3: TAT => chi scope]")
open(P, "wb").write(s.encode("utf-8"))
logging.info("FIX3_OK")
