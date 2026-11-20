# RESULT_GRIDV2_S1 - chay that lan 1: DUNG TRUOC MERGE (V0 + V4 FAIL), 2026-11-20
Trang thai: DUNG theo luat prereg muc 11/13 va giao viec MASTER. KHONG merge, KHONG doc bat ky so M / PnL nao (reduced/ chua mo).
Nguyen nhan nam trong CODE GHIM (runner_kaggle.py), khong phai loi ky thuat wrapper/metadata -> agent khong duoc sua; can MASTER
quyet + addendum prereg truoc khi sua code va chay lai.

## 1. Tuan thu
- Prereg: docs/prereg/PREREG_GRIDV2_S1.md commit 4ecc655d, sha256 52aaeab7bebc50de9a0cf11a882ef2c8e2fbb77082e23dead39d4f280e8fb9e4.
- Code (research/gridv2_s1 == w3/gridv2/s1, khop EXPECTED_SHA; manifest 5 shard deu bang):
  klite.py 196f4584..., kref.py 6de0e412..., stats.py 975f3a42..., runner_kaggle.py 9ddb3cef...
- H1: sha256(EXPECTED_SHA.txt) = 4f764be8a1ab480b2a10af390dbf39b82979071d4d250d3f81fca2bf1831987b -> DAT.
- H2: manifest.inputs (lifecycle 1f21f7df..., funding-2021 51386684..., -2022 d1c4edcc..., -2023 5498ebd6..., -2024 93642c59...,
  -2025 ff69f933...) GIONG HET 5 shard -> DAT phan sha. V0 phan registry (metadata == REGISTRY_REAL) DAT 5/5, NHUNG
  V0 ok_read_eq_meta FAIL 5/5 (xem muc 2) -> V0 tong the KHONG PASS -> khong merge.
- Trial: TRIALS_GRID.csv ghi 2026-11-20,4ecc655d,GRIDV2_S1,64,72 TRUOC khi chay.
- Dataset mount (dung 7): chuyendinh/vz-kline1m-2021, -2022, -2023, -2024, -2025, chuyendinh/gridp-t1-funding, chuyendinh/gridp-lifecycle.
  Khong vz-funding, khong 2026; allowlist cua runner PASS (khong abort). is_private, khong GPU, khong internet.
- Kernel: chuyendinh/gridv2-s1-shard0..4 (version 1). Wrapper: base64 4 file ghim -> /kaggle/working, kiem sha256 (OK ca 5),
  chi dat GRIDV2_SHARD=i/5; khong bien cam. So lan chay lai: 0.
- Thoi gian runner (s): s0 1873, s1 1746, s2 1488, s3 1969, s4 2108 (~25-35 phut). Universe 630 sym; shard 128/118/120/123/141.

## 2. V0-V6 tung shard
| shard | V0 registry | V0 read=meta | V1 | V2 | V3 | V4 | V5 | V6 | all_pass |
|---|---|---|---|---|---|---|---|---|---|
| 0 | PASS | FAIL | PASS | PASS | PASS | FAIL | PASS (8/8) | PASS | False |
| 1 | PASS | FAIL | PASS | PASS | PASS | FAIL | PASS (8/8) | PASS | False |
| 2 | PASS | FAIL | PASS | PASS | PASS | FAIL | PASS (8/8) | PASS | False |
| 3 | PASS | FAIL | PASS | PASS | PASS | FAIL | PASS (8/8) | PASS | False |
| 4 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS (8/8) | PASS | False |

### Bang chung FAIL (khong co so M)
(a) V0 ok_read_eq_meta: CA 5 shard, chi nam 2021: rows_read_pass1 2021 = 48 408 602 vs metadata 60 001 411 (thieu 11 592 809);
    2022-2025 khop dung metadata. Nguyen nhan trong code: runner_kaggle.py:275 (pass1) bo qua thang < DATA_START - 31 ngay
    (DATA_START = 2021-05-01, dong 36) -> khong doc kline1m-2021-01..03, trong khi V0 so sanh voi metadata CA NAM (dong 937 dung
    ok_read_eq_meta). Tuc la V0 FAIL theo cau truc voi du lieu that (prereg muc 1 noi "Doc 2021-05-01.." va "so dong doc = metadata"
    -> hai yeu cau mau thuan cho nam 2021). Lake gia trong test co le khong co thang < 2021-04 nen test khong bat. (Gia thuyet
    11 592 809 = so dong 2021-01..03: chua kiem doc lap vi khong tai metadata tung thang.)
(b) V4: v4_check (runner_kaggle.py:655-713) chon 2 symbol DAU theo thu tu ten cua shard (n_i < V4_SYMS=2) va tc ngau nhien;
    ok = (n_checked > 0 and n_diff == 0). Voi coin niem yet muon, tc roi truoc ngay niem yet -> 0 don vi de kiem -> ok False:
    s0 0GUSDT tc_min 625306 n_checked 0; 1000PEPEUSDT 727385 / 0
    s1 1000000MOGUSDT 256603 / 0; 1000CATUSDT 2277520 / 157934 n_diff 0 (ok)
    s2 1000RATSUSDT 781752 / 0; 1000XECUSDT 947662 / 277835 n_diff 0 (ok)
    s3 1000000BOBUSDT 1476419 / 0; 1000BONKUSDT 836324 / 0
    s4 1000BTTCUSDT 639670 / 24888 n_diff 0 (ok); 1000FLOKIUSDT 2142281 / 415086 n_diff 0 (ok)
    => V4 khong phat hien ro ri nao (n_diff = 0 o MOI check, tong 875 743 don vi kiem), FAIL do kiem RONG (vacuous), khong phai do lech.

### Cac V khac (khong co PnL)
- V1: ts_max = 1767225540000 (2025-12-31 23:59 UTC) < SEAL, 0 loi, ca 5 shard.
- V2: ti le dong active xau = 0,0 moi nam 2021-2025, ca 5 shard.
- V3: feat_mismatch_days 0; long_gaps 194/180/179/184/208; don vi loai do lo 16566/13437/15315/14833/15672; loai no_end 115/12/0/0/0;
  so (sym, thang) thieu > 1 % = 445/435/316/341/494.
- V5: 8/8 don vi kref trung moi shard.
- V6: median |rate| = 1e-4 (2021-2024), 5e-5 (2025); interval_h tu cot (khong suy), 100 % thuoc {1,2,4,8}.

## 3. Viec chua lam (cho MASTER)
B6 merge, result.json/diag.json, bang 32 o, rule L-A..L-D, MDE, chan doan: KHONG lam (luat dung). reduced/ 5 shard da tai ve
w3/gridv2/run1/d0..d4 nhung CHUA MO. Huong co the (MASTER quyet, can addendum prereg): (a) V0 so sanh rows_read voi metadata cac
thang thuc doc (>= 2021-04) hoac doc ca nam o pass1 chi de dem; (b) V4 chon symbol co don vi truoc tc (vd tc trong khoang song cua
symbol, hoac bo qua symbol niem yet sau tc). Mo phong khong phu thuoc V0/V4 nen output hien co co the van dung neu addendum cho
phep danh gia lai V0/V4 tu checkpoint - nhung agent khong tu ket luan; checkpoint agg_sym da bi xoa (GRIDV2_KEEP_SYM khong dat).

## 4. File
- Output: ~/claude_master/w3/gridv2/run1/d{0..4}/ (reduced/, validate.json, manifest.json, run.log, kaggle_kernel.log)
- Kernel + builder: ~/claude_master/w3/gridv2/run1/kernel_s{0..4}/, build_kernels.py, poll.sh, status.log
- Tien do: ~/claude_master/v12/GRIDV2_S1_RUN.progress
