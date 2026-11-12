# EQUIV — Pha 0: test tương đương live r4u3 (SUB) và sim B0, trước pilot D

Ngày 2026-11-10. Agent Opus R1. Chỉ thiết kế; không chạy kernel, không ghi 242.
[K] = đã kiểm trong code hoặc dữ liệu; [SĐ] = suy đoán.

## 1. Đề xuất: 3 tầng, không dựng replay toàn phần của jar live
Replay toàn phần DetectEntrySignal2TradeNormal qua nhiều tháng **không khả thi trước D**. Lý do: luồng live đọc Aerospike-242 (kline_1m_opt, OI), ONNX, sổ c3, exchangeInfo, đồng hồ thật. Harness parity hiện có chỉ dựng lại **đầu vào quyết định theo ngày** (OFF-BT/OFF-NEW2), không dựng vòng đời lệnh [K: `research/parity_v12`]. Vì vậy:

- **T1 — "B0 như live" bằng sim (đo tác động PnL/DD):** B0' = arm **A3 S1FULL** của R1 cộng các luật live có khả năng bind. So từng leg giữa A0 và B0' (cùng seed): coin, phút vào, size, số leg DCA, lý do và giờ thoát. Đo ΔCAGR22/ΔmaxDD theo tiêu chí C-LIVE (prereg R1 §6).
- **T2 — tương đương logic từng khối (code live vs code sim, cùng input, không tính PnL):**
  - (a) Exit: `ExitReplayDevMain` (test-classes jar r4u3) chạy song song đường thật `ExitParityEngine` và `ShadowBookC3` trên **toàn bộ leg DEV của 1 seed X14** ⇒ % quyết định arm/SL/time-stop/X14 trùng.
  - (b) Đầu vào và gate: harness parity_v12 OFF-NEW2 vs OFF-BT (+ `day_bigdown` ADD19) trên khoảng 10 ngày DEV có sập (vd. 2022-05-12, 2022-06-13, 2022-11-09, 2024-08-05, 2025-02-03, 2025-04-07, 2025-10-10).
  - (c) JUnit thuộc tính trên trạng thái ngẫu nhiên: size leg c3 (`C3LiveEntry`: managerBudget, `LiveGridSizing.legBudget`, cap, minBudget, tier) bằng size leg sim (`createOrder`); DCA due (`dcaDue`) bằng sim `getDCA`.
- **T3 — forward:** watcher parity hằng ngày (đã có) cộng lượt so leg dry r4u3 với sim replay cùng ngày (P2/P3/S1-I/GV/bigdown). Micro sau đó đo fill/phí thật.

## 2. Dữ liệu, compute, thời gian
| Tầng | Dữ liệu | Oracle | Kaggle | Thời gian |
|---|---|---|---|---|
| T1 | feat_v2_x1 (có), cand_dev_x1 (có), 16 fold S1 dựng lại, net015 raw (Kaggle `predwf-g015x26-gate`), feature HO 2026 tới 10-2026 | 3–5 h CPU qua lock [SĐ], đĩa ~3 GB | A3: 4 seed ≈ 10 h kernel (1 slot) ⇒ 8 seed ≈ 19 h | khoảng 2–3 ngày |
| T2a | printDone X14 1 seed + kline1m DEV (`~/vz_e1/raw`) | khoảng 1–2 h CPU [SĐ] | 0 | 0,5 ngày |
| T2b | Vision 1m khoảng 10 ngày (tải trên Oracle) | khoảng 10–30 phút/ngày [SĐ] | 0 | 1 ngày |
| T2c | — | phút | 0 | 0,5 ngày |
RAM Oracle 23 GB (khả dụng 19 GB), 4 lõi, đĩa trống 22 GB: đủ.

## 3. Lệch đã biết, cách đo, hướng đề xuất
| # | Lệch | Trạng thái | Đo | Hướng |
|---|---|---|---|---|
| D1 | Sim chỉ chấm S1 ở tick gate cũ mở; live chấm mọi tick | [K] còn mở | T1 (A3 vs A0) | **Giữ live, chạy B0'** |
| D2 | Thứ tự coin BIG_DOWN | đã sửa r4u | T2b `day_bigdown` | sửa live (xong) |
| D3 | BIG_DOWN qua gate p15 ≥ 0,008 trên live | đã sửa r4u | unit | sửa live (xong) |
| D4 | Live loại coin LEGACY | đã sửa r4u2/3 (SUB: false) | unit + log `[C3-LEGACY]` | sửa live (xong) |
| D5 | Live cap 4,5 % equity/leg; sim không có | [K] leg0 ≈ 2,25 % equity khi throttle 1 ⇒ khó bind | đếm leg B0 có margin/equity > 4,5 % (printDone) | giữ live |
| D6 | Sim CONC_CAP_PERCOIN 15 %; live c3 không có | [K] B0 `[CONC-PC] SUMMARY blocked=0` | đã đo (seed A1); kiểm 8 seed | vô hại; giữ |
| D7 | Live loại A1 (TradFi/INDEX/PREMARKET); sim không loại | [K] sim không có filter | đếm leg/PnL B0 trên symbol A1-loại (`UniverseA1Classifier`) | **Giữ live, thêm A1 vào B0'** (bỏ symbol khỏi bins) |
| D8 | Guard vận hành chỉ live: minute-incomplete, kill-switch 50 %, A40/C6, seed-block, p15 NaN | [K] | tần suất từ log dry r4t/r4u3 | giữ live; không đưa vào B0' |
| D9 | minBudget 5 USDT, minNotional/stepSize (micro 1000 USDT: leg ≈ 22,5 USDT [SĐ]) | — | dry log Outcome BUDGET_SMALL/SIZING; mô phỏng SymbolRules trên leg B0 với vốn 1k/10k | giữ live |
| D10 | Giá vào: market + giá realtime so với close + mô hình phí/slip sim | — | micro: fill vs close; so ECMEAS | giữ live; nếu chênh lớn thì B0' cost |
| D11 | Exit: STOP_MARKET trên sàn so với sim high/low 1m | — | T2a | sửa phía nào sai |
| D12 | Equity sizing: C3MainEquity (vốn + PnL c3) so với equity sim | [SĐ] tương đương | T2c | giữ live |
| D13 | DCA due live (`dcaDue` sổ c3, `DcaUtils.shouldDcaGrid`) so với sim `getDCA` | [K] cùng hàm grid | T2c + T2a | — |

## 4. Luật quyết định
- T1 C-LIVE "TƯƠNG ĐƯƠNG" và T2 không có lệch chưa giải thích ⇒ đủ điều kiện cho D.
- C-LIVE "XẤU HƠN" ⇒ MASTER xem xét lùi D, hoặc đưa thứ tự sim (S1 chỉ ở pool cũ) vào live. Không khuyến nghị cách thứ hai vì pool cũ dùng nhãn tương lai.
- T2 có lệch mới ⇒ ghi vào bảng, chọn "sửa live" hay "B0' như live" trước khi đóng.
