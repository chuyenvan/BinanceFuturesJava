# LEVZ B1 - engine thoat lenh nen 1 phut (PREREG_LEVZ_B1 @54f40792) - CHUA CHAY LUOI (cho A1 audit)

Thu muc: ~/claude_master/w3/levz_b1/ ; code/ test/ work/ out/ logs/. Code B0 (w3/levz2/code) chi import theo duong dan file, KHONG sua.

## Thanh phan
- code/common_b1.py : hang so, 195 bo thoat (XCFGS: SL x H x trailing, thu tu co dinh), load()/load_b0().
- code/paths.py build : memmap work/close1m.npy float32 [631 coin x 2 148 480 phut] (close 1m ffill), work/gaps.npz, work/hourly.npz
  (has1m, CLH). paths.py cand : B0 candidates() voi pxok = has1m -> work/cand_b1.npz (12 lop + union -> cid).
- code/exits.py all : bang thoat cho moi ung vien union x 195 bo -> work/exits.npz (j, ly do, xr, funding, mx, mxh, co; hourly mk/hm/fh/fc).
- code/port.py : tang danh muc (logic B0) doc bang thoat. code/grid_b1.py : 7 020 cau hinh -> out/grid_b1.parquet (resume).
- code/select_b1.py : luat chon in-sample, WFO-OOS, tinh ben, bien, doi chieu 759/758 + trailing 10/5, breakdown().
- code/rand_b1.py [reduced] [nrep] : doi chung ngau nhien dung nghia (luoi thoat x K moi luot) -> out/rand_b1.json.
- code/x12.py : doi chieu X1/X2 voi B0 (KHONG loi nhuan) -> out/x12.json.  test/test_b1.py -> test/test_report.json.

## Lenh mot dong (chay SAU khi A1 PASS; kiem truoc: free -m available >= 4000, df >= 15 GB; work hien ~5,5 GB, exits.npz ~0,3 GB)
cd ~/claude_master/w3/levz_b1 && mkdir -p ~/claude_master/locks logs && nohup flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 bash -c "python3 test/test_b1.py && python3 code/exits.py all && python3 code/grid_b1.py && python3 code/select_b1.py && python3 code/rand_b1.py reduced 100" > logs/pipeline.log 2>&1 < /dev/null &

(paths.py build + cand DA CHAY 2026-11-26 11:33-11:40 +07 voi code hien tai (work/close1m.npy 5,42 GB). Neu can dung lai: xoa work/close1m.npy TRUOC
(build ghi file .tmp 5,4 GB roi doi ten - dia Oracle chi ~15 GB trong), roi: python3 code/paths.py build && python3 code/paths.py cand. rand_b1.py khong tham so = 12 lop; 'reduced' = 6 lop E0 - xem CHOICES_B1 CAN MASTER QUYET C.)
