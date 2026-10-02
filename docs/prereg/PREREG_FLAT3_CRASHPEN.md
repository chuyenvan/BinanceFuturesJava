# PREREG_FLAT3_CRASHPEN — Kỳ vọng của B0 (G2 + FLAT3) khi PHẠT giá vào leg "sập"

Ngày chốt: **2026-10-02** (GMT+7). Chốt **TRƯỚC** khi đẩy bất kỳ kernel nào. Không sửa thiết kế sau khi thấy số; mọi đổi = AMENDMENT commit trước khi xem số bị ảnh hưởng.
Nguồn câu hỏi: `docs/audit/AUDIT_G2FLAT3_20261002.md` F3 + §3 mục 4; `docs/audit/AUDIT_LONG_LEVERS_20261002.md` điểm 6 (42 % ΣPnL B0 đến từ lệnh đóng TRONG GIỜ VÀO ⇒ độ thật của giá khớp ở phút sập quyết định kỳ vọng). Tiền lệ: `docs/result/RESULT_CRASH_PENALTY.md` (E2, R4/G2, commit `93846e05`).

**Bản chất:** stress **kỳ vọng**, KHÔNG phải lever. Không chọn/tune tham số nào từ vòng này. Mục tiêu = con số kỳ vọng hạ (CAGR/Calmar/ΣPnL của B0 dưới giá khớp thật hơn) + cờ cảnh báo khai trước.

## 1. Jar — phương án (A) do MASTER chọn
- Dùng **jar E2** dataset Kaggle `sim-jar-crashpen`, sha256 **`d944bea5f90a3c2cc4fa5bd45ee488b168459a9782719e909f5eb11f3c95ce89`** cho **cả 3 arm** (kể cả P0) ⇒ mọi khác biệt giữa arm chỉ do key phạt.
- Lý do: jar B0 (`7368be46…` = `sim-jar-gdv2`) KHÔNG có key `SIM_CRASH_ENTRY_PENALTY`; jar E2 khác jar B0 **đúng 2 class** `research/SimulatorMarketLevelTicker1MStopLoss.class` và `tradecore/Configs.class`, có đủ key phạt + 3 key FLAT3 (`TS_GIVEBACK_RATIO`, `SIM_TS_MAX_GAP`, `SIM_TS_MAX_GAP_WEAK`). KHÔNG build, KHÔNG sửa `.java`.
- Rủi ro chấp nhận: jar E2 chưa từng chạy FLAT3 ⇒ cổng parity P0 (§3) là điều kiện cần.

## 2. Cấu hình — B0 nguyên văn (từ `~/kaggle_sim/out/de-p1/result.json`)
- Profile `r4_kg0_k16_f015_g155` + overrides: `SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_DAYS=90`, `SIM_GATE_ROLLING_PCT=0.999950829` (**KHÔNG** dùng `0.99995083` của E2), `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`.
- Bundle `sim-x1-2021-bundle` + ticker `wfo-ticker-2021…2025h2`; `sim_end_date=20251231`; `xmx=22g`; `timeout_s=5400`; `jar_ds=sim-jar-crashpen`; `TICKER_SOURCE=file`. Gửi qua `tools/kaggle_sim.submit` (overrides ghi đè bản copy profile).
- DEV ≤ 2025-12-31; 2026 = HOLDOUT, không dùng.

## 3. Arm (KHOÁ, 3 kernel)
| arm | tag Kaggle | `SIM_CRASH_ENTRY_PENALTY` | vai trò |
|---|---|---|---|
| **P0** | `flat3-cp-p0` | **vắng** | cổng parity |
| **P1** | `flat3-cp-p1` | `0.0069` | điểm ước lượng (+0,69 %/chân, `RESULT_LATENCY_FILL`) |
| **P2** | `flat3-cp-p2` | `0.0138` | 2× điểm |

"Leg sập" (định nghĩa E2, không đổi): leg vào khi nến **quyết định** có `bar_ret=(close−open)/open ≤ −1 %`; phạt cộng vào **giá vào**; số leg bị phạt/năm từ log `[CRASH-PENALTY] SUMMARY … byYear`.
**Cổng parity P0 (bắt buộc):** `md5(printDone.csv) = 650c386f0d0dfea334af9d55ca2f21d4`, **n = 2517**, **equity = 131908**. Lệch bất kỳ ⇒ **VOID toàn vòng**, DỪNG, không đẩy P1/P2, báo. Trình tự: đẩy P0 trước; P0 PASS mới đẩy P1, P2. Kernel `ok` = `equity_final != None` và `n_trades > 0` (`java_rc=1` là bình thường); mapper ≥ 800; `jar_sha256` trong `result.json` phải = `d944bea5…` cả 3 arm.

## 4. Thước đo (KHOÁ) — so mọi arm với **B0 = P0** (byte-identical `de-p1` nếu parity PASS)
Cham AS-IS: phí base 0,1116 %/vòng + phạt đã nằm trong artifact (qua giá vào), không hiệu chỉnh thêm. Driver Python offline mới `research/analysis/flat3_crashpen_driver.py`, tái dùng `reset_rule_score` (load_legs/load_daily/core_metrics/ci_pair/run_mtm), cửa sổ 2022+ theo `feat_add_v1_score` (MTM reset 2022-01-01 UTC, CAGR từ equity 2021-12-31), ghép cặp theo `long_levers_paired_ruler.py`, episode theo `audit_g2flat3_20261002_stats.episodes`. `k = 2` arm so B0 ⇒ **inflate = √(2 ln 2) = 1,1774**.

**(i) PRIMARY — ΔPnL ghép cặp theo lệnh vs B0** (size-neutral): khoá `sym|start|level`; lệnh khớp: `(profit_arm − profit_B0)/100 × notional_B0`; lệnh chỉ ở 1 phía: ± `profit/100 × notional` của chính nó. CI bootstrap block-72h theo giờ vào (neo 2021-07-01), NREP 2000, seed 20260905; báo CI raw và CI inflate (nửa-độ-rộng × 1,1774 quanh điểm). Báo kèm n_common / n_only_B0 / n_only_arm, ΔPnL theo năm vào (2021H2…2025) và tách theo nhóm giữ của B0 (`time_order = 0` vs `> 0`).
**(ii) Equity / MTM:** n, equity cuối, ΣPnL (Σ`pnl` printDone), CAGR (equity ngày b+unP), maxDD MTM phút, UW MTM (ngày), **Calmar_MTM = CAGR / |maxDD MTM phút|** ở **2 cửa sổ: toàn kỳ** (2021-07-01→2025-12-30) **và 2022+** (2022-01-01→2025-12-30); ROI/năm, maxDD MTM/năm, qmin; **top-5 episode share** (cụm ngày đóng lệnh, khoảng trống ≤ 2 ngày, top-5 theo ΣPnL / ΣPnL toàn kỳ); số leg phạt/năm.
**(iii) Lệnh "đóng trong giờ vào"** (`time_order = 0` trong printDone, cùng định nghĩa bucket "0h" của AUDIT_LONG_LEVERS): n, ΣPnL và **% ΣPnL** mỗi arm (trước phạt = B0, sau phạt = P1/P2); cùng số cho phần còn lại.
**§9 T1–T4 vs B0** (báo, KHÔNG phải luật GO vì không chọn gì): T1 maxDD MTM phút/năm ≥ −40 %, UW ≤ 250 ngày, qmin ≥ −20 %, 0 năm âm, conc ≤ 15 %; T2 q* ≥ 15 %, top-1 % ≤ 25 %; T3 Δwin% ≥ −2 pp, ΔTSloss% ≤ +2,5 pp, mP|SM & mP|SL không xấu có ý nghĩa (`ci_pair`, inflate 1,1774); T4 Calmar_MTM ≥ 0,90 × B0 (cả 2 cửa sổ) và conc ≤ B0.

## 5. Kỳ vọng ghi TRƯỚC (suy từ E2 G2, chưa đo trên FLAT3) — [SUY LUẬN]
Tham chiếu B0 đã công bố: n 2517, eq 131 908, ΣPnL ≈ 96,9k, CAGR 34,31 / dd MTM −17,68 / Calmar **1,940** toàn kỳ; 2022+ CAGR 33,56 / **1,898** / UW 87; top-5 episode 36,6 %; 0h = 521 lệnh, +41,0k (42,3 %).
E2 G2: phạt 0,69 % ⇒ eq −10,0 %, Calmar −9,3 %; 1,50 % ⇒ eq −19,7 %, Calmar −20,8 %. Ngoại suy cho B0: **P1** eq ≈ 117–120k, ΣPnL ≈ 82–86k (≈ −12…−15 %), Calmar_MTM ≈ 1,70–1,78; **P2** eq ≈ 104–108k, ΣPnL ≈ 69–73k, Calmar ≈ 1,50–1,60. FLAT3 có 42 % ΣPnL ở lệnh 0h (bắt nhịp hồi trong cú sập) ⇒ có thể **nhạy hơn** G2; nếu sụt lớn hơn ngoại suy thì đó là phát hiện, không phải lỗi.

## 6. Ngưỡng cảnh báo (KHAI TRƯỚC, cố định)
**CẢNH BÁO "B0 KHÔNG đủ bền với giá khớp thật"** ⇔ ở **P1**: Calmar_MTM(2022+) **< 1,2** HOẶC ΣPnL(P1) **< 60 % ΣPnL(B0)**. Ngược lại ⇒ "không kích cảnh báo" (KHÔNG có nghĩa là bền đã chứng minh). P2 chỉ báo cáo mô tả (độ dốc), không kích cảnh báo.

## 7. Cấm / giới hạn khai trước
- Không đổi arm/mức phạt/cấu hình sau khi thấy số; 1 lần chạy mỗi arm (kernel lỗi hạ tầng ⇒ chạy lại cùng tag, ghi rõ).
- 0 sim Java trên Oracle; không chạm 242/shadow; không sửa `.java`, không build.
- Phạt đều 1 mức cho mọi leg sập (không theo độ sâu bar_ret); `quantity = budget/entry` giảm khi vào đắt ⇒ hiệu ứng bậc 2, nằm trong artifact.
- Mức phạt có CI [−0,19; +1,50] trên n=27 (thiếu power) ⇒ đây là stress giả định quanh điểm, không đo lại chi phí thật.
- MTM phút dùng close 1m (cận dưới của DD thật); 1 quan sát lịch sử.
