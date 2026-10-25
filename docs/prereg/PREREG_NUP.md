# PREREG_NUP — TĂNG SỐ LỆNH cho gói go-live X14 (MASTER thiết kế 2026-10-26)

Trạng thái: **CHỐT trước mọi kernel**. File này chép nguyên văn §1, §3, §4 của brief MASTER
(`# TASK NUP — TĂNG SỐ LỆNH cho gói go-live X14`, 2026-10-26), cộng chi tiết kỹ thuật để thi hành.
Không đổi arm/ngưỡng/seed/kỳ sau khi thấy số. Phát hiện bug sau khi thấy số ⇒ sửa bug, viết ADDENDUM,
báo cả số trước/sau.

Baseline B0 = crash-buy K24 + skipFull + TS_MKT_EXT X14, jar sha256
`cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe`.
DEV: `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}`. HO:
`~/kaggle_sim/out/tsx-ho-x14-s{42,7,13,21,99,123,777,2024}`. Số đã xác minh: DEV 2022–25 median
2 878 cụm, ΣPnL 113 410 USD, CAGR22 39,0 %, maxDD MTM −22,83 %; HO 2026 9 tháng 441 cụm,
ΣPnL 18 106, maxDD −5,62 % (`docs/result/GOLIVE_QUARTERLY.md`, commit 61ac2b87).

## §1. Các arm, CHỐT: đúng 7 arm, không thêm/bớt, không đổi giá trị

Mọi arm = B0 (copy y nguyên `prof_run.properties` của `tsx-x14-<seed>`), chỉ đổi các key ghi dưới đây.
Cùng jar cc0f9d11, cùng pred, cùng `SIM_LOSER_TS_EXT_DAYS`.

| Arm | Đổi so với B0 | Ý nghĩa |
|---|---|---|
| A1 | `SIM_GATE_ROLLING_PCT=0.99990` | nới gate ~×2 đuôi |
| A2 | `SIM_GATE_ROLLING_PCT=0.99985` | nới gate ~×3 |
| A3 | `SELECTOR_RANK_TOPK=32` | trần mã/đợt 32 |
| A4 | `SELECTOR_RANK_TOPK=32` + `SIM_GATE_ROLLING_PCT=0.99990` | kết hợp |
| A5 | `SIM_GATE_DYN_SCALE=1.30` | nới ngưỡng động theo sp (mã hạng thấp dễ qua hơn) |
| A6 | A4 + size mỗi leg ×0,67 (xem §1.1) | nhiều lệnh nhỏ hơn, phơi nhiễm gần như cũ |
| A7 | TIER2 (code mới, §1.2) | thêm lệnh CHỈ khi sổ trống và nến quyết định không sập |

### §1.1 A6: size ×0,67

- Tìm key quyết định notional leg (ứng viên: `SIM_F_BASE`, `CAPITAL_START`/`NUMBER_ORDER_BUDGET`,
  `DCA_GRID_SCALE`). ĐỌC CODE Java để xác định, ghi file:dòng vào prereg.
- Chọn cách đổi sao cho notional leg0 = 0,67× B0, còn U_MAX/throttle và mọi thứ khác giữ nguyên.
- Validate sau khi chạy: median notional leg0 A6/A4 ∈ [0,64; 0,70]. Sai ⇒ dừng, báo.

### §1.2 A7: TIER2, phải code

- Tạo branch riêng từ đúng commit của jar cc0f9d11, tên `research/nup-tier2` (tìm commit bằng sha jar;
  không tìm được ⇒ DỪNG, báo MASTER).
- Key mới, mặc định TẮT:
  - `GATE_TIER2_ENABLED`
  - `GATE_TIER2_PCT=0.99985`
  - `GATE_TIER2_U_MAX=0.20` (tỷ lệ vốn đang dùng U lúc quyết định)
  - `GATE_TIER2_CRASH_RET=-0.01`
  - `GATE_TIER2_SIZE_MULT=0.5`
- Logic: một ứng viên TRƯỢT gate chính nhưng QUA ngưỡng TIER2_PCT (cùng buffer r, cùng q-tính, chỉ đổi
  phân vị) được vào lệnh khi ĐỦ cả 3 điều kiện:
  - U hiện tại < TIER2_U_MAX;
  - return nến 1m quyết định của symbol đó > TIER2_CRASH_RET (nến đã đóng, không nhìn tương lai);
  - còn slot K.
  Size = SIZE_MULT × size thường. Lệnh TIER2 KHÔNG được làm thay đổi buffer/quota của gate chính.
- Gắn nhãn `tier=2` vào printDone (cột mới hoặc log riêng) để tách PnL.
- Bắt buộc:
  - Unit test cho từng điều kiện.
  - Khi TẮT, sim BYTE-IDENTICAL với cc0f9d11: chạy B0 seed a1 bằng jar mới cờ tắt, md5 printDone phải
    trùng run gốc.
  - KHÔNG sửa đường live/shadow. Nếu code dùng chung với live thì cờ mặc định tắt và ghi rõ.
- Không làm được byte-identical ⇒ bỏ A7, ghi lý do, vẫn chạy A1–A6.

## §3. Thước đo (mỗi run; DEV = 2022-01-01 → 2025-12-31 theo giờ +07 đóng lệnh, giống GOLIVE_QUARTERLY)

- Số cụm/năm và số leg/năm, theo từng năm 2022/23/24/25; số đợt; số ngày có lệnh mới.
- ΣPnL USD, CAGR22, maxDD MTM (pipeline golive_quarterly, missing = 0), Calmar, ROI theo năm và quý.
- PnL/cụm. Tách lệnh "chung với B0" và lệnh "mới" và lệnh "B0 bị mất":
  - khớp theo (symbol, giờ vào ±1′);
  - ΣPnL từng nhóm, ROI/lệnh từng nhóm. Đây là thước chi phí cơ hội của N_DEEP.
- Stress: trừ thêm 20 bps khứ hồi trên notional mọi leg ⇒ ΣPnL_stress.
- Phơi nhiễm: U trung bình/max, số vị thế đồng thời max.
- A7: tách riêng ΣPnL/cụm của tier=2.

## §4. Luật chọn, CHỐT (median qua seed, ghép cặp với B0 cùng seed)

- **G1 lệnh:** cụm/năm ≥ 1,30× B0, VÀ mỗi năm 2022, 2023, 2024, 2025 ≥ 1,15× B0 (thêm lệnh đều,
  không dồn 1 đợt).
- **G2 PnL:** ΣPnL ≥ 0,90× B0, VÀ ≥ 3/4 seed (Pha 1) hoặc ≥ 6/8 (Pha 2) có ΣPnL ≥ 0,85× B0 cùng seed,
  VÀ ΣPnL_stress ≥ 0,85× B0_stress.
- **G3 DD:** maxDD MTM median ≥ −32 %, seed tệ nhất ≥ −36 %. Lý do: kill-switch live A40/C6 ở −40 %,
  cần đệm cho trượt giá thật.
- **G4 HO 2026 (chỉ Pha 2, để xác nhận, KHÔNG dùng chọn):** ΣPnL HO median ≥ 0,80× B0 HO, VÀ maxDD HO ≥ −12 %.
- **Kết luận:**
  - GO = qua G1–G4 ở Pha 2.
  - Nhiều arm GO ⇒ chọn cụm/năm cao nhất; hoà ±5 % ⇒ ΣPnL cao hơn.
  - Không arm nào GO ⇒ NO-GO, kèm bảng frontier (cụm/năm × ΣPnL × maxDD) để owner tự cân.
- Trial ledger họ NUP = 7 arm. Ghi rõ trong result. DEV đã bị nhìn nhiều lần, X14 là in-sample.
- **CẤM:** đổi ngưỡng, thêm arm, đổi seed, đổi kỳ sau khi thấy số. Phát hiện bug sau khi thấy số ⇒
  sửa bug, viết ADDENDUM, báo cả số trước/sau.

---

# Chi tiết kỹ thuật (bổ sung để thi hành, KHÔNG đổi luật)

## T0. Nguồn code / jar / commit

| mục | giá trị |
|---|---|
| Source repo | `/home/ubuntu/src_wt_bcd` (worktree của BinanceFuturesJava) |
| Commit khớp jar | `a8690d468cb76d774bfe6b452a51aaf80e0445aa` — branch `feat/ts-mkt-ext`; `sha256(target/binance-java-sdk-1.2.4.jar)` = `cc0f9d11…1b1dfe` (đã kiểm 2026-10-26) |
| Branch code A7 | `research/nup-tier2`, tạo từ đúng `a8690d46` (git worktree riêng `/home/ubuntu/src_nup`) |
| Profile | `r4_kg0_k16_f015_g155` (trong bundle `sim-x1-2021-bundle` / dataset `sim-jar-tsx`) |
| Pred | nguyên như cơ chế `gate_skipfull_driver.pred_of(seed)`: A1 = pred gốc bundle; S7 = `gate-abl-seed7`; các seed khác = `gate-sb-<seed>` |
| X14 | `SIM_LOSER_TS_EXT_HOURS=336` + `SIM_LOSER_TS_EXT_DAYS` = 42 khoảng DEV (`tsx/flags.json`, sha256 `c79ef302…`), HO = 4 khoảng (`tsx/ho/ho_flags.json`, sha256 `ecaced06…`) |
| Jar dùng cho A1–A6 và cổng B0 | `sim-jar-tsx` (cc0f9d11), không build lại |
| Jar dùng cho A7 | dataset private mới `chuyendinh/sim-jar-nup-tier2`, chứa `sim.jar` build từ `research/nup-tier2` |

Overrides B0 (đúng như run `tsx-x14-*`): `OV_BASE` = `SIM_GATE_ROLLING_MODE=ratio`,
`SIM_GATE_ROLLING_DAYS=90`, `SIM_GATE_ROLLING_PCT=0.999950829`, `TS_GIVEBACK_RATIO=1.0`,
`SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`, `SELECTOR_RANK_TOPK=24`,
`GATE_QUOTA_SKIP_WHEN_FULL=true`, `SIM_LOSER_TS_EXT_HOURS=336`, `SIM_LOSER_TS_EXT_DAYS=<ranges>`.

## T1. A6 — key quyết định notional (đọc code)

- `budget = balanceBasic × SIM_F_BASE × throttle / dcaGridTotalWeight()`:
  `src/main/java/com/binance/chuyennd/tradecore/TradeUtils.java:130-142` (`managerBudget`).
- `throttle = clamp(1 − U/U_MAX, 0, 1)`, `U = marginRunning/equity`:
  `TradeUtils.java:136-141`; `U_MAX` đọc từ `SIM_U_MAX`, mặc định 0.60 (`Configs.java:168`, `Configs.java:915`).
- `SIM_F_BASE` đọc tại `Configs.java:914`; mặc định `F_BASE=0.03` (`Configs.java:155`).
- Leg0 nhân thêm `gridLegWeightRatio(0) = w0 × DCA_GRID_SCALE` (FIX_B2):
  `DcaUtils.java:47-65`, `SimulatorMarketLevelTicker1MStopLoss.java:1488`.
- Kết luận: `SIM_F_BASE` là key duy nhất tuyến tính với notional leg0; `CAPITAL_START`/`NUMBER_ORDER_BUDGET`
  chỉ dùng cho `BASE_BUDGET` cũ (không đi vào `managerBudget` hiện tại); `DCA_GRID_SCALE` đổi cả ladder.
- **A6 dùng `SIM_F_BASE=0.01005`** (= 0.015 × 0.67). Giữ nguyên `SIM_U_MAX`, `DCA_GRID_SCALE`,
  `DCA_GRID_WEIGHTS`, tier multiplier. Hệ quả phụ: khi U thấp hơn, throttle `1−U/U_MAX` tăng nhẹ
  ⇒ notional A6/A4 kỳ vọng 0.67–0.70; cổng validate median ∈ [0.64; 0.70] (§1.1) sẽ quyết định.

## T2. A7 — thiết kế code (chốt trước khi viết)

File sửa (chỉ 3 file main + 2 file test):
1. `src/main/java/com/binance/chuyennd/tradecore/Configs.java`
   - thêm field mặc định: `GATE_TIER2_ENABLED=false`, `GATE_TIER2_U_MAX=0.20f`,
     `GATE_TIER2_CRASH_RET=-0.01f`, `GATE_TIER2_SIZE_MULT=0.5f` (cạnh `U_MAX`, ~dòng 168);
   - đọc key trong static loader (cạnh `SIM_U_MAX`, ~dòng 915). `GATE_TIER2_PCT` đọc trong
     `GateRollingRatio.init()` (cùng chỗ `SIM_GATE_ROLLING_PCT`).
2. `src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/GateRollingRatio.java`
   - thêm `tier2On`, `tier2Pct` (mặc định false / 0.99985f), đọc key trong `init()`;
   - thêm `public static boolean tier2Pass(long ts, float p15, float sp)`: tính `r` **đúng công thức
     hiện tại** (`factor = max(DYN_MIN, sp/SCORE_BASE*DYN_MULT)`, `gs = GATE_DYN_SCALE`), lấy phân vị
     `tier2Pct` trên **cùng buffer**, **cửa sổ**, **cùng giờ** với gate chính, và **loại mẫu hiện tại**
     (mẫu vừa được `threshold()` nạp) để q2 tính trên đúng trạng thái trước-add như q1;
   - `tier2Pass` KHÔNG gọi `add`, KHÔNG `notePass`, KHÔNG đổi `predictSeen/predictPass/skipFull`.
3. `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java`
   - trong `createOrder` (sau `filterResult`, ~dòng 1373): nếu `decision==REJECT` và
     `Configs.GATE_TIER2_ENABLED` và `levelChange==PREDICT_SYMBOL_TRADE` và `symbolPred!=null` và
     `selRank!=null` (slot K: ứng viên nằm trong top-K của tick) và `!bookFull` và
     `U < GATE_TIER2_U_MAX` và `ticker.priceClose/ticker.priceOpen−1 > GATE_TIER2_CRASH_RET` và
     `GateRollingRatio.tier2Pass(ts,p15,sp)` ⇒ đặt `tier2=true`, đi tiếp; ngược lại `return` như cũ;
   - sau `managerBudget` (~dòng 1448) nhân `budget *= GATE_TIER2_SIZE_MULT` khi `tier2`;
   - ghi nhãn riêng `storage/tier2.csv` (`sym,start,margin`) khi mở leg tier2; KHÔNG thêm cột vào
     `printDone.csv` (giữ định dạng cho mọi scorer hiện có).
   - Cờ TẮT: không nhánh nào chạy, không đọc/ghi file, `tier2Pass` trả false ngay.
4. Test: `src/test/java/com/binance/chuyennd/ai_ml/onnx/entry/NupTier2GateTest.java`,
   `src/test/java/com/binance/chuyennd/research/NupTier2CondTest.java` — mỗi điều kiện 1 test
   (U, crash-return, size mult, q2 pass khi q1 fail, và q2 không đổi buffer/counter).

"còn slot K" được hiểu là ứng viên đã nằm trong top-K của tick (điều kiện duy nhất mà sim hiện có
tương ứng K = `SELECTOR_RANK_TOPK`; không có trần số vị thế đồng thời = K trong code). Cổng này được
kiểm bằng `selRank != null` và ghi rõ trong result.

## T3. Launcher / seed / tag

- DEV: `python3 research/nup/run.py push-dev <arm> <seed...>` dùng `tsx_driver.B.push` (jar
  `sim-jar-tsx`, bundle `sim-x1-2021-bundle`, end `20251231`, CPU). A7 dùng
  `B.JAR_DS="sim-jar-nup-tier2"`.
- HO: `python3 research/nup/run.py push-ho <arm> <seed...>` dùng `ho4p1_queue.push` (bundle 2026,
  unseal, end `20261001`), y hệt `tsx-ho-x14-*`.
- Tag: `nup-<arm>-<seed>` (DEV), `nup-ho-<arm>-s<seed>` (HO), `nup-b0chk-s7` (cổng tái lập).
  Tên arm viết thường (`a1`…`a7`, `b0chk`).
- Seed Pha 1 DEV: `a1,s7,s21,s99`. Pha 2 DEV thêm: `s13,s123,s777,s2024`; HO:
  `42,7,13,21,99,123,777,2024`.
- Kết quả kéo về `~/kaggle_sim/out/<tag>/`; trung gian `~/claude_master/nup_wk/`.

## T4. Chấm

- MTM: `research/golive_quarterly/mtm_dev.py` (DEV) và `mtm_ho.py` (HO), `missing=0` assert; scorer
  `research/nup/score.py` dùng lại `quarterly.build/metrics` (cùng quy ước: quý theo giờ +07, trục MTM
  UTC = +07−7h, cụm theo giờ đóng, đợt theo t0).
- Baseline lấy từ 8 run `tsx-x14-*` / `tsx-ho-x14-s*` đã có, ghép cặp cùng seed.
- Stress: trừ 20 bps × notional mọi leg (khứ hồi) khỏi ΣPnL; báo `ΣPnL_stress`.
- Khớp lệnh chung/mới/mất: `(sym, start ±1 phút)`; báo ΣPnL và ROI/lệnh từng nhóm.
- V4: script độc lập `research/nup/independent_check.py`, chỉ `csv`/`datetime`, không import pipeline;
  tính lại cụm/năm + ΣPnL của 1 arm × 1 seed, lệch phải = 0.

## T5. Cổng trước khi đo

1. Prereg này commit TRƯỚC khi push kernel.
2. Cổng tái lập B0: `nup-b0chk-s7` (jar cc0f9d11, đúng launcher cũ, không đổi key) — md5 printDone
   phải = `622b03e2…` (run `tsx-x14-s7`) hoặc so từng dòng = 0 lệch.
3. A7: unit test PASS; chạy B0 a1 bằng jar mới cờ tắt (`nup-a7off-a1`) — md5 phải = `dc62609b…`
   (`tsx-x14-a1`). Không đạt ⇒ bỏ A7, chạy A1–A6.

## T6. Trial ledger

Họ NUP = **7 arm**. Phase 1 = A1–A6 (+A7 nếu qua cổng code) × 4 seed DEV. Phase 2 = tối đa 2 arm
qua G1–G3 × 4 seed DEV còn lại + 8 seed HO. DEV là in-sample (X14 đã được chọn trên 2021–25).
