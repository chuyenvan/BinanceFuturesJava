# PREREG NUP2 — ADDENDUM KỸ THUẬT (2026-10-26)

Trạng thái: viết **trước khi push bất kỳ kernel đo lường nào của NUP2**. Không sửa
`docs/prereg/PREREG_NUP2.md` (sha256 `10bb4ba7…`, commit `439fe15a`). File này chỉ ghi
chi tiết kỹ thuật cần để thi hành đúng §2–§5: key, file:dòng, cách hiệu chuẩn, seed, launcher,
định nghĩa validate. Không thêm lever/mức/seed/kỳ.

## 1. Baseline và nguồn số

- B0 = crash-buy K24 + skipFull + X14, jar
  `cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe`.
- Đã kiểm 8/8 run DEV `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}`:
  `storage/printDone.csv` tồn tại, `jar_sha256` đúng, `ok=true`, `java_rc=1`
  (n_trades 3 449–3 646; secs 1 612–2 622).
- Số NUP Pha 1 (A1–A6) **tái dùng nguyên** từ `docs/result/nup/runs.csv` (commit
  `1ed971a9`, không chạy lại). A5 là NO-OP; A2 đã trượt G4 ⇒ không đưa A2 đơn lẻ vào Pha 3
  (chỉ dùng A2 như X/Y trong factorial nếu được xếp).
- Code Java đọc tại worktree `~/src_wt_bcd` = branch `feat/ts-mkt-ext` @ `a8690d46`
  (đúng commit của jar cc0f9d11).

## 2. Key của từng arm NUP2 (Pha 1b)

Mọi arm = copy nguyên `prof_run.properties` của `tsx-x14-<seed>` + đúng các override dưới.
Cùng jar cc0f9d11, cùng pred, cùng `SIM_LOSER_TS_EXT_*`.

| Arm | Override | Cơ chế (file:dòng) |
|---|---|---|
| B1 | `SIM_F_BASE=0.006305` | `Configs.java:923` đọc key; `TradeUtils.java:139-142` `budget = equity × F_BASE × (1−U/U_MAX) / ladder`; `DcaUtils.java:62` `ratio = w × DCA_GRID_SCALE`. F_BASE là bội số tuyến tính chung của notional mọi leg; U_MAX/K/gate/ladder/SCALE giữ nguyên. |
| B2 | `DCA_GRID_LEVELS=-0.335,-0.5025,-0.603` | `Configs.java:208-209` (mặc định `-0.50,-0.75,-0.90`); `DcaUtils.java:33-41` so `lastPrice/firstEntryPrice-1 <= level`. Khoảng cách mỗi bậc ×0,67 (25pp→16,75pp; 15pp→10,05pp). `DCA_GRID_WEIGHTS=1,1,1,1` và `DCA_GRID_SCALE=6` **giữ nguyên** ⇒ tổng ngân sách/cụm không đổi. |
| B3 | `DCA_GRID_LEVELS=-0.50,-0.60,-0.70,-0.80,-0.90` + `DCA_GRID_WEIGHTS=1,1,1,1,1,1` | `Configs.java:219-220` (weights), `Configs.java:253` số leg = độ dài mảng khi `DCA_GRID_SCALAR=false`, `Configs.java:325-331` tổng trọng số. 6 leg/cụm (1 entry + 5 DCA), trọng số đều, cùng dải −50…−90. Ladder = 6; `managerBudget` chia 6; `SCALE=6` ⇒ mỗi leg = 1×budget (B0: 6/4×budget), tổng 6 leg = 6×budget = đúng tổng B0 (4 leg × 1,5×budget). |
| B4 | `SIM_U_MAX=0.75` | `Configs.java:168` default 0,60; `Configs.java:915` đọc key; `TradeUtils.java:137` chặn `u ≥ U_MAX`. |
| B5 | `SIM_MIN_MOMENTUM_15M=0.005` | `Configs.java:834` đọc key; `EntryGate.java:203` `threshold(MIN_MOMENTUM_15M, …)`. |

### 2.1 Hiệu chuẩn B1 (không dùng PnL)

Giống ADDENDUM A, nhưng U lấy từ **B0** (a1, s7) vì B1 = B0 × size:

- `U(t0) = Σ margin các leg đang mở tại t0 / equity(t0)` (equity phút dựng bằng
  `mtm_parquet.py`, cùng nguồn giá Vision như ADDENDUM B).
- `f(rF,U) = rF × (1 − rF·U/U_MAX) / (1 − U/U_MAX)`, `U_MAX=0.60`.
- Giải bisection `median_U f(rF,U) = 0.50` ⇒ `rF=0.42033709`, `SIM_F_BASE = 0.015 × rF
  = 0.006305` (6 chữ số).
- Dữ liệu: 6 951 cụm leg0 (B0 a1: 3 468; s7: 3 483), `median U = 0.14789`,
  `median f = 0.5000`. File `research/nup2/b1_fbase.json`.
- Band validate §2 NUP2: median notional leg0 B1/B0 ∈ [0,47; 0,53]. Ngoài band ⇒ **dừng B1**,
  báo, không tự đổi F lần hai. (A6 từng về 0,6444 khi target 0,67 — lệch −3,9 % do FLOOR
  quantity; nếu B1 lặp lại tỷ lệ này sẽ về ~0,48, vẫn trong band.)

### 2.2 Diễn giải "bậc" của B3 (chốt trước khi đo)

B0 có `DCA_GRID_WEIGHTS=1,1,1,1` = **4 leg/cụm** (1 entry + 3 DCA). NUP2 §2 ghi "4 → 6 bậc".
Được chốt là **6 leg/cụm** (1 entry + 5 DCA), trọng số đều, cùng dải giá −50 %…−90 %
(`-0.50,-0.60,-0.70,-0.80,-0.90`). Tổng notional/cụm khi chạm đáy giữ nguyên 6×budget.

## 3. A7 (TIER2) — chạy lại 4 seed

- Code: branch `research/nup-tier2` @ `a221bf80` (nền `39c98525` + cache q2/giờ).
- Jar: **`ce4bcc17b824862d5f2b828d244dc7bb51dc6434420697d608b2196ea1012329`**
  (dataset private `chuyendinh/sim-jar-nup-tier2`).
- Sự cố nhỏ: `kaggle datasets download` trả 404 cho dataset này, nhưng kernel Kaggle **mount
  bình thường**. Đã lấy lại đúng file bằng kernel private `nup2-jar-fetch`
  (copy `/kaggle/input/.../sim.jar` ra output), sha256 khớp `ce4bcc17…`. Đây là kernel hạ tầng,
  không đo lường.
- Override đúng PREREG_NUP §1.2:
  `GATE_TIER2_ENABLED=true, GATE_TIER2_PCT=0.99985, GATE_TIER2_U_MAX=0.20,
  GATE_TIER2_CRASH_RET=-0.01, GATE_TIER2_SIZE_MULT=0.5`.
- Nhãn tier=2: `storage/tier2.csv` (`SimulatorMarketLevelTicker1MStopLoss.java:1367`, ghi
  `sym,start` của leg tier2).
- Off-parity đã có từ NUP: `nup-a7off2-a1` (cùng jar ce4bcc17) md5 printDone = `dc62609b…`
  = B0 a1. Không chạy lại off-parity trừ khi kernel A7-on lỗi.
- Nếu A7-on vẫn >7 200 s ⇒ ghi "A7 không đo được", loại khỏi tập ứng viên, không tối ưu thêm.

## 4. Launcher, tag, seed

- Driver mới `research/nup2/run.py` (bản sao `research/nup/run.py`, đổi W=`~/claude_master/nup2_wk`,
  thêm ARMS B1–B5; DEV dùng `tsx_driver.B.push`, bundle `sim-x1-2021-bundle`, pred theo seed,
  `sim_end_date=20251231`, xmx 22g, timeout 7 200 s, CPU, private, 5 slot song song).
- Tag: `nup-<arm>-<seed>` DEV, `nup-ho-<arm>-s<seed>` HO, `nup-b0chk-s7` cổng tái lập.
- Seed Pha 1b: `a1, s7, s21, s99`. Pha 3 thêm `s13, s123, s777, s2024` + 8 HO
  `{42,7,13,21,99,123,777,2024}` (launcher `ho4p1_queue`, flags `tsx/ho/ho_flags.json`).
- Cổng tái lập: `nup-b0chk-s7` phải trùng md5 `storage/printDone.csv` của `tsx-x14-s7`
  = `622b03e264fdd0b59a1673e144f4148f` (đã kiểm lại run NUP `nup-b0chk-s7` = đúng md5 này).
  Không trùng ⇒ dừng.

## 5. Chấm điểm

- DEV: `mtm_parquet.py` (Vision 1m close, công thức legacy + PnL leg đóng 00:00 UTC) →
  `research/nup/score.py` + `quarterly.py` (`fix_off=None`). Kế thừa nguyên §3 PREREG_NUP.
- HO: dùng `ecm_mtm_h` + cache `ecm_px` như NUP; **G4 dùng ΣPnL realized + maxDD realized**
  (không MTM) theo yêu cầu MASTER, vì cache 2026 thiếu và luật cấm tải kline 2026.
- Chỉ số bổ sung §5 NUP2: N_eff (số đợt cách nhau <6h/năm; số ngày có lệnh mới/năm;
  corr PnL ngày với B0; top-10 ngày % ΣPnL), tách PnL leg đầu / leg DCA.
- Factorial: `{X, Y, B1}`, bỏ ô đã có, 4 ô mới × 4 seed; X,Y xếp theo E (median 4 seed),
  B1 luôn "hữu ích".
- iso-DD: s* = −30 / DD_median (xấp xỉ tuyến tính), chạy 1 run thật ở ô tốt nhất cụm/năm,
  seed s7, s* làm tròn 0,05; lệch DD >3pp ⇒ bỏ cột iso-DD.
- Pha 3: tối đa 3 ô qua G1–G3 ở 4 seed (gộp NUP+NUP2+factorial), không gồm A2 đơn lẻ.

## 6. Validate (định nghĩa chốt trước khi đo)

- **V1:** mỗi run `java_rc=1`, `ok=true`, `jar_sha256` đúng; diff `prof_run.properties` với
  B0 đúng tập key của arm (in diff). A7 dùng jar ce4bcc17.
- **V2:** ΣPnL theo quý = Σ giai đoạn (≤1 USD); B0 8 seed tái tạo n_cl median = 2 878.
- **V3:** MTM missing = 0 mọi run; B0 maxDD median = −22,83 %.
- **V4:** script độc lập (chỉ CSV + datetime, không import pipeline) tính lại cụm/leg/entry/ΣPnL
  của 1 arm × 1 seed; lệch = 0.
- **V5:** B1 median notional leg0 ratio ∈ [0,47; 0,53]; B2/B3 số leg DCA/cụm tăng và
  **max tổng notional/cụm ≤ 1,02× B0**; B4 số `skipFull=` trong log giảm và U max tăng;
  B5 số ứng viên qua lọc tăng (log gate pass); A7 tier2 > 0 (nếu đo được).
- Không chạy lại A1–A6; V5 của A6 (0,6444) giữ nguyên từ NUP.

## 7. Trial ledger

Tổng họ NUP + NUP2 ≤ 7 (A1–A7) + 5 (B1–B5) + 4 ô factorial + 1 iso-DD = **17 cấu hình**.
A7 nằm trong 7 arm NUP. Không thêm arm/mức/seed sau khi thấy số.

## 8. Trung gian / đĩa

`~/claude_master/nup2_wk/` (state, eq npz, log, jar A7 95 MB) — xoá sau khi chốt result;
giữ source `research/nup2/`, branch `research/nup-tier2`. Không ghi >3 GB; kiểm `df -h /`
trước khi ghi >500 MB.
