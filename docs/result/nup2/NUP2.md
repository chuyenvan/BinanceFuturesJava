# NUP2 — Pha 1b/2b, A7 rerun (2026-10-27)

**Trạng thái: DỪNG theo điều kiện A7 của MASTER.** Không chạy iso-DD, không chạy Pha 3 (HO).
Số liệu Pha 1b: xem `P1B_REPORT.md` (commit 59b47359). Tài liệu này chốt Pha 2b + A7 4 seed + frontier.

## 0. Kết luận risk-first

1. **Không ô factorial nào GO.** Cả 4 ô `xy, xb1, yb1, xyb1` đều trượt **G2** (ΣPnL và stress), dù `xy`/`xyb1` qua G1 rất mạnh (×3,27 cụm/năm).
2. **A7 nay đo được** bằng jar `ce4bcc17` (3 201 s, rc=1, jar khớp) và trở thành lever **"hữu ích" biên**:
   ×B0 PnL = **0,807** (ngưỡng 0,80), E = **0,198**, **hạng 2 trong nhóm hữu ích** sau A2 (0,294) và trên A3 (0,099).
   → **Điều kiện DỪNG của MASTER được kích hoạt.** Không tự đổi Y; Y vẫn là A3 như plan đã duyệt.
3. **A2 đơn lẻ** (X) qua G1–G3 trên DEV 4 seed nhưng đã trượt **G4 HO** ở NUP ⇒ vẫn không phải ứng viên GO.
4. **Chất lượng lệnh giảm khi nhân lên:** `xy` ×3,27 cụm nhưng N_eff chỉ 172 → 500 đợt (2,9×), tương quan PnL ngày với B0 rơi còn 0,60, và ΣPnL/đợt giảm mạnh. Đây là "nhiều lệnh" chứ không phải "nhiều cơ hội độc lập" tương ứng.

## 1. Kernel đã chạy (17/17 COMPLETE)

| tag | java_rc | ok | giây | n_trades |
|---|---|---|---|---|
| nup-a7r-s21 | 1 | True | 3201 | 4694 |
| nup2-c-xy-a1 | 1 | True | 2040 | 11016 |
| nup2-c-xy-s7 | 1 | True | 1879 | 11110 |
| nup2-c-xy-s21 | 1 | True | 2155 | 11103 |
| nup2-c-xy-s99 | 1 | True | 2020 | 11033 |
| nup2-c-xb1-a1 | 1 | True | 2012 | 8727 |
| nup2-c-xb1-s7 | 1 | True | 2728 | 8797 |
| nup2-c-xb1-s21 | 1 | True | 2180 | 8751 |
| nup2-c-xb1-s99 | 1 | True | 2162 | 8758 |
| nup2-c-yb1-a1 | 1 | True | 2625 | 4579 |
| nup2-c-yb1-s7 | 1 | True | 1909 | 4563 |
| nup2-c-yb1-s21 | 1 | True | 2144 | 4528 |
| nup2-c-yb1-s99 | 1 | True | 2294 | 4701 |
| nup2-c-xyb1-a1 | 1 | True | 2522 | 11087 |
| nup2-c-xyb1-s7 | 1 | True | 2418 | 11166 |
| nup2-c-xyb1-s21 | 1 | True | 2049 | 11200 |
| nup2-c-xyb1-s99 | 1 | True | 2317 | 11095 |

- Tất cả jar `cc0f9d11…`; riêng `nup-a7r-s21` dùng `ce4bcc17…` (xác nhận trong `result.json` và `A7_JAR_VERIFY.md`).
- `nup2-c-yb1-s99` phải push lại 1 lần: lần đầu Kaggle trả 404 `No runs found` sau 2 phút (kernel chưa đăng ký version). Đã sửa `poll()` chỉ coi 404 là FAILED sau 20 phút; lần 2 COMPLETE.

## 2. Factorial 2³ (X = A2, Y = A3, cùng B1) — 4 seed

| arm | n_seed | n_cl_year | n_cl_ratio | pnl | pnl_ratio | stress_ratio | cagr | dd_median | dd_worst | calmar | neff | G1 | G2 | G3 | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a2 | 4 | 1855.6 | 2.564 | 110786.1 | 0.927 | 0.863 | 38.3 | -27.8 | -28.0 | 1.375 | nan | ✓ | ✓ | ✓ | ✓ |
| a3 | 4 | 924.2 | 1.280 | 118158.3 | 1.023 | 1.016 | 40.3 | -25.3 | -26.2 | 1.571 | nan | ✗ | ✓ | ✓ | ✗ |
| b1 | 4 | 724.1 | 1.004 | 48349.3 | 0.430 | 0.431 | 22.3 | -15.5 | -17.6 | 1.437 | 172.0 | ✗ | ✗ | ✓ | ✗ |
| xy | 4 | 2363.9 | 3.266 | 98178.7 | 0.823 | 0.739 | 34.2 | -28.5 | -28.7 | 1.206 | 500.0 | ✓ | ✗ | ✓ | ✗ |
| xb1 | 4 | 1858.4 | 2.571 | 56594.0 | 0.485 | 0.457 | 25.5 | -22.1 | -22.3 | 1.153 | 463.0 | ✓ | ✗ | ✓ | ✗ |
| yb1 | 4 | 926.0 | 1.282 | 55385.6 | 0.488 | 0.487 | 24.6 | -18.7 | -20.2 | 1.309 | 179.0 | ✗ | ✗ | ✓ | ✗ |
| xyb1 | 4 | 2369.1 | 3.275 | 55229.1 | 0.486 | 0.447 | 24.4 | -23.9 | -24.1 | 1.022 | 498.5 | ✓ | ✗ | ✓ | ✗ |

- `a2/a3/b1` là các arm đơn cùng 4 seed, để so trực tiếp với ô.
- **G2 là nút thắt:** `xy` PnL 0,823× và stress 0,739×; `xb1` 0,485/0,457; `yb1` 0,488/0,487; `xyb1` 0,486/0,447. Không ô nào đạt 0,90 / 0,85.
- `xy` và `xyb1` qua G1 (×3,27; từng năm 2,52 / 3,07 / 3,59 / 3,64) nhưng PnL/đợt giảm và DD sâu hơn.

## 3. Tương tác (Δ so với tổng cộng tuyến tính, median 4 seed)

| name | Δcụm/năm | ΔΣPnL | ΔmaxDD pp |
|---|---|---|---|
| A2 | 1126.2 | -8777.9 | -5.321 |
| A3 | 204.2 | 2547.0 | -2.635 |
| B1 | 2.625 | -64437.4 | 7.036 |
| A2+A3 (do) | 1632.1 | -19797.6 | -5.925 |
| A2+A3 (cong) | 1330.2 | -6241.0 | -8.135 |
| A2+A3 TUONG TAC | 301.9 | -13556.6 | 2.209 |
| A2+B1 (do) | 1130.4 | -57874.4 | 0.414 |
| A2+B1 (cong) | 1128.9 | -72776.1 | 1.706 |
| A2+B1 TUONG TAC | 1.500 | 14901.7 | -1.292 |
| A3+B1 (do) | 205.8 | -57512.7 | 4.260 |
| A3+B1 (cong) | 207.9 | -61441.0 | 4.891 |
| A3+B1 TUONG TAC | -2.125 | 3928.3 | -0.631 |
| A2+A3+B1 (do) | 1638.9 | -57814.5 | -1.339 |
| A2+A3+B1 (cong) | 1332.9 | -70229.0 | -0.929 |
| A2+A3+B1 TUONG TAC | 306.0 | 12414.5 | -0.410 |

- **A2 × A3:** cụm tăng **thêm +1 208 cụm/4 năm (+302/năm, +22,7%)** so với cộng tuyến tính — tức hai lever *bổ trợ* về số lệnh. Nhưng PnL **xấu hơn cộng tuyến tính 13 557 USD**, và DD **bớt xấu hơn 2,21 pp** (nhờ size/leg nhỏ hơn khi có TOPK 32).
- **Với B1:** tương tác cụm gần 0 (`A2+B1` +6; `A3+B1` −8,5), tương tác PnL dương cơ học do B1 giảm size (A2+B1 +14 902; A3+B1 +3 928), DD gần như cộng tuyến tính.
- **Bộ ba:** +1 224 cụm/4 năm so với cộng tuyến tính (TOPK cộng thêm khi size nhỏ), PnL +12 415, DD −0,41 pp.

## 4. A7 — chạy lại đúng jar, chấm 4 seed

Tag mới `nup-a7r-s21` (giữ nguyên artefact cũ `nup-a7-s21`). Xác nhận jar: xem `A7_JAR_VERIFY.md`
(version dataset 3 = `ce4bcc17`, `totalBytes` khớp số học; sau chạy `result.json.jar_sha256 = ce4bcc17…`).

| seed | tag | cụm | ×B0 | ΣPnL | ×B0 | maxDD |
|---|---|---|---|---|---|---|
| a1 | nup-a7-a1 | 4109 | 1.431 | 91716 | 0.792 | -24.25 |
| s7 | nup-a7-s7 | 4014 | 1.388 | 89529 | 0.822 | -23.88 |
| s21 | nup-a7r-s21 | 3962 | 1.377 | 94747 | 0.868 | -24.62 |
| s99 | nup-a7-s99 | 4054 | 1.359 | 87440 | 0.709 | -24.57 |

**Median 4 seed:** 1 008,5 cụm/năm (×1,383), ΣPnL 90 623 (×**0,807**), maxDD −24,41 % (Δ −1,93 pp), **E = 0,198**.
Tier2: ~1 262 leg/4 năm, PnL tier2 ~7 812 USD (~6 USD/leg) — vẫn là lệnh biên.

**Xếp hạng E trong nhóm hữu ích (trừ B1):** A2 0,294 → **A7 0,198 (hạng 2)** → A3 0,099.
**ĐIỀU KIỆN DỪNG = TRUE** (`a7_rescore.json`): A7 hữu ích, E hạng 2, key `GATE_TIER2*` khác key A2.
→ Báo MASTER, **không đổi Y**, không chạy iso-DD/Pha 3.

*Cảnh báo:* A7 chỉ vừa qua ngưỡng hữu ích (0,807 so với 0,80); 1/4 seed (s99) có PnL 0,709×. Nếu MASTER muốn dùng A7 làm Y thì cần quyết định riêng và chạy lại factorial với A7.

## 5. Frontier đầy đủ (mọi ô NUP + NUP2, 4 seed)

| cell | n_cl_year | n_cl_ratio | pnl | pnl_ratio | stress_ratio | cagr | dd_median | dd_worst | calmar | neff | G1 | G2 | G3 | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 721.1 | 1.000 | 112466.8 | 1.000 | 1.000 | 38.6 | -22.5 | -24.7 | nan | nan | – | – | – | – |
| A1 | 1330.8 | 1.839 | 89413.3 | 0.789 | 0.748 | 34.7 | -25.9 | -26.8 | 1.334 | 336.0 | ✓ | ✗ | ✓ | ✗ |
| A2 | 1855.6 | 2.564 | 110786.1 | 0.927 | 0.863 | 38.3 | -27.8 | -28.0 | 1.375 | 463.5 | ✓ | ✓ | ✓ | ✓ |
| A3 | 924.2 | 1.280 | 118158.3 | 1.023 | 1.016 | 40.3 | -25.3 | -26.2 | 1.571 | 182.0 | ✗ | ✓ | ✓ | ✗ |
| A4 | 1717.8 | 2.370 | 99246.8 | 0.886 | 0.838 | 37.0 | -27.0 | -27.2 | 1.369 | 355.5 | ✓ | ✗ | ✓ | ✗ |
| A5 | 721.1 | 1.000 | 112466.8 | 1.000 | 1.000 | 38.6 | -22.5 | -24.7 | 1.716 | 172.0 | ✗ | ✓ | ✓ | ✗ |
| A6 | 1720.1 | 2.378 | 63036.7 | 0.557 | 0.532 | 27.8 | -23.1 | -23.3 | 1.204 | 358.0 | ✓ | ✗ | ✓ | ✗ |
| B1 | 724.1 | 1.004 | 48349.3 | 0.430 | 0.431 | 22.3 | -15.5 | -17.6 | 1.437 | 172.0 | ✗ | ✗ | ✓ | ✗ |
| B2 | 722.8 | 1.001 | 118963.5 | 1.062 | 1.063 | 39.7 | -24.8 | -26.3 | 1.602 | 172.5 | ✗ | ✓ | ✓ | ✗ |
| B3 | 723.9 | 1.001 | 82288.2 | 0.726 | 0.728 | 31.9 | -19.9 | -22.5 | 1.598 | 171.5 | ✗ | ✗ | ✓ | ✗ |
| B4 | 721.2 | 1.000 | 139238.1 | 1.239 | 1.240 | 43.6 | -25.9 | -28.6 | 1.687 | 172.0 | ✗ | ✓ | ✓ | ✗ |
| B5 | 721.1 | 1.000 | 112466.8 | 1.000 | 1.000 | 38.6 | -22.5 | -24.7 | 1.716 | 172.0 | ✗ | ✓ | ✓ | ✗ |
| A7 | 1008.5 | 1.383 | 90622.7 | 0.807 | 0.791 | 34.7 | -24.4 | -24.6 | 1.443 | 274.0 | ✓ | ✗ | ✓ | ✗ |
| C:xy | 2363.9 | 3.266 | 98178.7 | 0.823 | 0.739 | 34.2 | -28.5 | -28.7 | 1.206 | 500.0 | ✓ | ✗ | ✓ | ✗ |
| C:xb1 | 1858.4 | 2.571 | 56594.0 | 0.485 | 0.457 | 25.5 | -22.1 | -22.3 | 1.153 | 463.0 | ✓ | ✗ | ✓ | ✗ |
| C:yb1 | 926.0 | 1.282 | 55385.6 | 0.488 | 0.487 | 24.6 | -18.7 | -20.2 | 1.309 | 179.0 | ✗ | ✗ | ✓ | ✗ |
| C:xyb1 | 2369.1 | 3.275 | 55229.1 | 0.486 | 0.447 | 24.4 | -23.9 | -24.1 | 1.022 | 498.5 | ✓ | ✗ | ✓ | ✗ |

- `B5` là NO-OP (trùng B0) — giữ làm dữ liệu, không xếp hạng.
- Cột `iso_*` trong CSV là **ước lượng tuyến tính §4**, **chưa kiểm bằng run** (theo lệnh DỪNG).
- `A2` là ô duy nhất qua G1–G3 trên DEV nhưng đã trượt G4 HO ở NUP.

## 6. N_eff (§5 PREREG)

| ô | cụm/năm | N_eff (đợt/4 năm) | ngày có lệnh mới | corr PnL ngày vs B0 | top-10 ngày |
|---|---|---|---|---|---|
| B0 | 721,1 | 172 | 142 | 1,000 | 0,43 |
| A2 (X) | 1 855,6 | 463,5 | 358,5 | 0,659 | 0,42 |
| A3 (Y) | 924,3 | 182 | 151 | 0,979 | 0,43 |
| xy | 2 363,9 | 500 | 380 | 0,602 | 0,45 |
| xb1 | 1 858,4 | 463 | 359,5 | 0,711 | 0,38 |
| yb1 | 926,0 | 179 | 149 | 0,981 | 0,40 |
| xyb1 | 2 369,1 | 498,5 | 381 | 0,677 | 0,42 |
| A7 | 1 008,5 | 274 | 221,5 | 0,912 | 0,40 |

corr của A2/A3 tính trực tiếp từ printDone bằng đúng công thức `extras.py` (median 4 seed), vì `extras_nup.csv` không có cột này; các dòng còn lại lấy từ `extras.csv`.
Đọc: `xy` tăng cụm ×3,27 nhưng N_eff chỉ ×2,9 và tương quan ngày 0,60 ⇒ phần lớn là lệnh trong cùng đợt/cùng ngày, không phải cơ hội độc lập mới.

## 7. Validate

- **V1 PASS (có 1 ngoại lệ hạ tầng):** 40/40 run `java_rc=1`, `ok=true`, `jar_sha256` đúng; `prof_run.properties` chỉ khác B0 đúng tập key của ô.
  Ngoại lệ: `nup2-c-yb1-s99` có thêm `WFO_FUNDING_PRED_DIR=/kaggle/input/sim-x1-2021-bundle` thay vì
  `/kaggle/input/datasets/chuyendinh/sim-x1-2021-bundle` — **chỉ khác tiền tố mount**, cùng dataset;
  `result.json.pred_md5_used = 5ef90e92…` đúng md5 kỳ vọng của seed s99 và log ghi `md5 verified`.
- **V2 PASS:** tổng 16 quý 2022–25 = `DEV_2022_25` cho cả 17 tag mới; lệch PnL max 1,5e-11 USD; n_cl khớp tuyệt đối.
- **V3 PASS:** MTM missing = 0 cho 17 tag mới (`mtm_merge.json`), tổng 40 tag trong `eq_parquet.npz`;
  B0 4-seed maxDD median −22,474 trùng `quarterly_x14_by_seed.csv`.
- **V4 PASS:** `independent_check.py nup2-c-xy-s7 s7` (csv/datetime độc lập): n_cl 9 496, n_leg 9 621, n_entry 2 097, PnL 88 672,41; diff = 0 / 0 / 0 / 0,0.
- **V5 (từ Pha 1b):** B3 đạt ngân sách/cụm (0,549×), **B2 vi phạm (1,481× > 1,02×)**; B4 skipFull 0 (từ 80,5); B1 leg0 0,469× (sát biên dưới).

## 8. Lệch thiết kế / sự cố

1. **A7 rerun** theo chỉ đạo mới: tag `nup-a7r-s21`, artefact cũ giữ nguyên; dataset version 3 (`ce4bcc17`) được xác nhận 3 lớp. Không đổi prereg.
2. **A7 trở thành hữu ích** sau khi có đủ 4 seed ⇒ kích hoạt điều kiện DỪNG. Y không đổi (A3), các ô `yb1/xyb1` vẫn dùng A3.
3. **Slot contention ngoài task:** từ 05:27–06:23 có 4 kernel `sim-nup3b-*` của một orchestrator NUP3b khác chiếm slot account, nên 17 run mất thêm ~50 phút. Không can thiệp (không kill tiến trình/dữ liệu của task khác).
4. **404 sau push** với `yb1-s99`: đã sửa logic poll (chờ 20 phút) và push lại; không ảnh hưởng số.
5. **A2 dùng 4 seed** (không dùng 8 seed Pha 2 NUP) để nhất quán factorial theo MASTER_FIX §2.
6. **B2** vẫn vi phạm validate ngân sách/cụm từ Pha 1b; không dùng trong factorial.
7. `nup-a7-s21` (bản cũ) vẫn FAILED/timeout do jar cũ — **không** dùng để chấm; đã thay bằng `nup-a7r-s21`.

## 9. Artifact

- `arms_p2b.csv`, `frontier_p2b.csv`, `match_p2b.csv`, `score_p2b.json`
- `interact_p2b.csv`, `frontier_all.csv`
- `a7_rescore.json`, `A7_JAR_VERIFY.md`
- `runs.csv` (40 tag NUP2 + NUP), `extras.csv` (40 tag), `validate_v1.csv`
- MTM: `~/claude_master/nup2_wk/eq_parquet.npz` (40 tag, missing 0)
- Trial ledger: NUP 7 + NUP2 5 + factorial 4 + A7-rerun 1 = 17 cấu hình (đúng §7).
