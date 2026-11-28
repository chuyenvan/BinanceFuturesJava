# DEV_FEAT - trang thai (vong 3, 2026-11-28)
Lenh chay CHINH THUC (sau A1 PASS; tu choi neu 3 status_full chua done):
  cd ~/claude_master/w3/opt/feat && nohup nice -n 15 /usr/bin/time -v /usr/bin/python3 code/optfeat.py 2019-01-01 2026-01-01 > logs/full.log 2>&1 && /usr/bin/python3 code/test_feat.py T6 && /usr/bin/python3 code/hygiene.py >> logs/full.log 2>&1 &
Do that (ban dev 21:22-21:24, 36.72 M trade: BTC 21.58 M / 2557 ngay, ETH 15.14 M / 2467 ngay): 2 phut 02 giay, RSS dinh 1.18 GB, ra 36.6 MB.
Ra: out/feat_hourly.parquet (61 368 gio x cot ts + 37 x {x,z90,hi,lo,terc} + n_/w_/cov/raw), out/FEAT_META.json, out/HYGIENE.md (hygiene.py ~30 s).
Tests: /usr/bin/python3 code/test_feat.py (T2 T3 T5 T7 T4 T1 T6) -> test/RESULT_*.json; RESULT_REGRESSION*.json; RESULT_T7_FULL.json.
