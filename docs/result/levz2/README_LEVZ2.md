# LEVZ2 - simulator danh muc SHORT + toi uu DEV (PREREG_LEVZ2 @278725ae). CHUA AUDIT - CHUA CHAY LUOI.
Thu muc: ~/claude_master/w3/levz2/ (code/, test/, work/, out/, logs/). Python offline, logging, khong print. Khong doc >= 2026.

## Thu tu (da chay buoc 1-4; buoc 5 CHO A1 audit)
1. `python3 code/sig.py build && python3 code/sig.py s1`  -> work/sig_W14.parquet, work/sig_W7.parquet, work/sig_meta.json, work/s1.json (S1).
2. `python3 code/px.py build && python3 code/px.py s2`    -> work/px_1h.parquet, work/s2.json (S2).
3. `python3 code/sim.py prep`                            -> work/inputs.npz (OHLC dense, funding theo moc gio, universe, 12 tap ung vien).
4. `python3 test/test_sim.py` (46 ca, du lieu tong hop) ; `python3 test/bench.py` (toc do, du lieu tong hop) ;
   `python3 code/sim.py smoke && python3 code/smoke_diag.py` (CHAY THAT DUY NHAT: W14 E0 z2.5 K10 SL50 H24 khong trail/DCA).
5. SAU KHI A1 PASS + MASTER chot CHOICES2 "CAN MASTER QUYET": luoi + chon + ngau nhien, MOT dong:
```
cd ~/claude_master/w3/levz2 && mkdir -p ~/claude_master/locks logs && nohup flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 bash -c 'python3 code/grid.py && python3 code/select.py && python3 code/rand.py' > logs/run_grid.log 2>&1 < /dev/null &
```
   (truoc khi phong: `free -m` available >= 4000 MB, `df -h ~` >= 15 GB). Resume: chay lai dung lenh tren (grid/rand bo qua phan da xong trong
   out/grid_parts, out/rand_parts). Ket qua: out/grid.parquet, out/grid_scored.parquet, out/select.json/.md, out/rand.parquet, out/rand.json.
   Uoc tinh: <= 1.8 s/cau hinh (4 lan chay DEV+F1+F2+F3), 3 tien trinh => luoi ~10 phut, ngau nhien ~5 phut.

## File
- code/sig.py: IMPORT code dong bang tang 1 (levz.Data, levz.signals, levz.episodes, levz.e1_entry) - khong viet lai dinh nghia.
- code/px.py: doc OHLCV_1H_v2.bin (30 B/rec big-endian).
- code/sim.py: candidates(), run(cfg, sig, px, funding, start, end) -> (trades, equity, metrics), run_all (DEV + F1..F3), all_cfgs (1 296).
- code/grid.py, code/select.py (muc 5), code/rand.py (muc 6, seed 20261126), code/smoke_diag.py.
- Moi script tu go thu muc code/ khoi sys.path (code/select.py trung ten module chuan `select`) va nap file anh em qua importlib.
- CHOICES2.md: moi dien giai + muc CAN MASTER QUYET.
