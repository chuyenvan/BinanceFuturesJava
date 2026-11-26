# LEVZ B2 - GATE che do thi truong + FILTER cap coin (PREREG_LEVZ_B2 @da636b28) - CHUA CHAY LUOI (cho A1 audit)
Thu muc ~/claude_master/w3/levz_b2/: code/ test/ work/ out/ logs/. Import (chi doc) levz_b1/code (port, exits, grid_b1, select_b1),
levz2/code (sim, sig, grid), levz/code/common.py. Bang thoat / ung vien: levz_b1/work/{exits.npz,cand_b1.npz}; ban goc: levz_b1/out/grid_b1.parquet.

## Thanh phan
- code/b2c.py (duong dan + import), code/mkt.py build -> work/mkt.npz, code/opts.py [describe] -> out/describe_b2.*,
  code/grid_b2.py check_none | all | <O>... -> out/grid_b2_<O>.parquet (+ out/grid_b2_parts/<O>/), code/report_b2.py -> out/report_b2.md|json,
  code/placebo_b2.py <O> [500] -> out/placebo_b2_<O>.json (+ out/placebo_b2_<O>/run_*.json). test/test_b2.py -> test/test_report.json.

## Lenh mot dong (SAU khi A1 PASS; kiem truoc: free -m available >= 4000, df >= 3 GB; out du kien < 100 MB)
cd ~/claude_master/w3/levz_b2 && mkdir -p ~/claude_master/locks logs && nohup flock -w 7200 ~/claude_master/locks/oracle_heavy.lock nice -n 10 bash -c "python3 code/mkt.py build && python3 test/test_b2.py && python3 code/grid_b2.py check_none && python3 code/grid_b2.py all && python3 code/report_b2.py" > logs/pipeline.log 2>&1 < /dev/null &
Uoc: mkt 10 s + test 30 s + check 15 s + luoi 12 phuong an ~20-25 phut + report < 1 phut => ~25-30 phut (khong ke cho lock).

## Placebo (chi cho O co pass_a_to_d = True trong out/report_b2.json; tu choi neu khong)
cd ~/claude_master/w3/levz_b2 && nohup flock -w 7200 ~/claude_master/locks/oracle_heavy.lock nice -n 10 python3 code/placebo_b2.py <O> 500 > logs/placebo_<O>.log 2>&1 < /dev/null &
Uoc ~10-17 phut / phuong an (3 tien trinh). Resume duoc (chay lai cung lenh).
