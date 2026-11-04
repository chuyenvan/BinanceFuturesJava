#!/usr/bin/env python3
"""Unit test collect_eval (dong log tong hop, khong doc 242). Chay: python3 test_collect_eval.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_eval as CE

D = "2026-11-04"   # ngay UTC: +07 04/11 07:00 -> 05/11 07:00
base = [
    "04/11/2026 07:00:10.000 INFO  [x] c: [KLINE-COVER] phut=20261104 06:59 chua_chot=0 chua_chot_truoc=0 bo_kiem=0 ws_muon_go=0 suspects=0 goi=0",
    "05/11/2026 06:58:00.000 INFO  [x] c: [REST-BUDGET] calls=47 weight=85 denied=0 http429=0 http418=0 http4xx=0",
]
ok = []
# 1) ngay sach: 0 restart
r = CE.evaluate(base, D)
ok.append(r["covers_day"] and r["collectData_restart_le2"] is True and r["restart_too_many"] == 0)
# 2) 3 restart 'Too many' => khong sach; KLINE-COVER/429/PRICE-AGE dem dung; dong ngoai ngay bi bo
bad = base + ["04/11/2026 09:00:00.000 ERROR [T] c: Too many symbol price errors: 53. Restarting..."] * 3 + [
    "04/11/2026 09:00:30.000 INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.websocket.BinanceDataIngestor",
    "04/11/2026 09:01:30.000 INFO  [K] c: [KLINE-COVER] phut=20261104 09:00 chua_chot=552 chua_chot_truoc=0 bo_kiem=0 ws_muon_go=0 suspects=552",
    "04/11/2026 10:00:00.000 INFO  [R] c: [REST-BUDGET] calls=47 weight=85 denied=2 http429=3 http418=1 http4xx=0",
    "04/11/2026 11:00:00.000 WARN  [P] c: [PRICE-AGE] price_realtime dung 31886 ms (> 15000 ms)",
    "04/11/2026 06:59:59.000 ERROR [T] c: Too many symbol price errors: 9. Restarting...",   # ngay truoc => bo
]
r = CE.evaluate(bad, D)
ok.append(r["restart_too_many"] == 3 and r["collectData_restart_le2"] is False and r["mainclass"] == 1
          and r["kline_cover_chua_chot_minutes"] == 1 and r["kline_cover_suspects"] == 552
          and r["http429_max"] == 3 and r["http418_max"] == 1 and r["denied_max"] == 2 and r["price_age_max_ms"] == 31886)
# 3) log khong phu ca ngay => None (CHUA DO), khong bao gio coi la sach
r = CE.evaluate(base[1:], D)
ok.append(r["covers_day"] is False and r["collectData_restart_le2"] is None)
print("cases", ok)
print("TEST_COLLECT", "PASS" if all(ok) else "FAIL")
sys.exit(0 if all(ok) else 1)
