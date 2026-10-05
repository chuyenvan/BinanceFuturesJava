# PREREG_EXIT_TIME_B0 — Cắt sớm lệnh CHƯA arm trên B0 (G2 + FLAT3): time-stop 72h vs cond-exit 72h × MFE<5 %

Ngày chốt: **2026-10-03** (GMT+7). Chốt **TRƯỚC** khi đẩy bất kỳ kernel nào. Không sửa thiết kế sau khi thấy số; mọi đổi = AMENDMENT commit trước khi xem số bị ảnh hưởng.
Nguồn: `docs/audit/AUDIT_LONG_LEVERS_20261002.md` (commit `9e645137`) §5.1 (nháp) + §2.6 + §3.3. Quy trình mẫu: vòng FLAT3_CRASHPEN (`6362bd18` / `d439a206`).

**Câu hỏi:** cắt sớm lệnh **chưa arm** (flat 72h, hoặc 72h có điều kiện MFE < 5 %) có tăng PnL của **cùng tập entry** B0 không?
**Cơ chế đã thấy (mô tả, hậu kiểm DEV):** 339 lệnh time-stop 168h ăn **−55,9k** (= 36 % lãi gộp lệnh thắng); giá trung vị trôi **đơn điệu** −5,5 % @24h → −9,9 % @72h → −13,6 % lúc cắt. Hai vòng cũ E1 (nền C2b, X72: ΣPnL +9,9 %) và F2 (cond-exit: +5,8/+7,6 %) bị chấm bằng `win%`/`TSloss%` — rate **lệch cơ học** (lệnh bị cắt mang nhãn `STOP_LOSS_DONE` theo định nghĩa) ⇒ NULL cũ không đáng tin; B_FOLLOWUP (T170, fixed-96) ngược dấu (eq −7 %). **Chưa từng chạy trên B0, chưa từng đo bằng thước tiền ghép cặp.**

## 1. Key & jar (bước 1 đã kiểm, 0 build, 0 sửa `.java`)
- Key đọc qua `Cfg` trong `Configs` (`Configs.java:912-914` ở `module`):
  - `SIM_LOSER_TIME_STOP_HOURS` → `Configs.LOSER_TIME_STOP_HOURS` (int; profile B0 đã có `=168`).
  - `SIM_COND_EXIT_HOURS` → `Configs.COND_EXIT_HOURS` (int, 0 = tắt = mặc định), `SIM_COND_EXIT_MIN_FAV` → `Configs.COND_EXIT_MIN_FAV` (float).
- Cơ chế (`SimulatorMarketLevelTicker1MStopLoss.startUpdateOldOrderTrading`, TRƯỚC cổng profit-arm, mỗi nến 1'):
  - LOSER: `priceSL == null` (chưa arm) **và** `time − anchor > H×3600 s` (anchor = leg đầu cụm) ⇒ `STOP_LOSS_DONE`, giá thoát `min(open, close)` của nến 1'.
  - COND: `priceSL == null` **và** `time − anchor > H×3600 s` **và** `(maePeak − priceEntry)/priceEntry < MIN_FAV` (maePeak = đỉnh thật của cụm sim đã theo dõi) ⇒ `STOP_LOSS_DONE`, `min(open, close)`. Đúng định nghĩa `PREREG_F2.md` §3 (F2_a: 72 / 0.05).
- Kiểm jar (`unzip` + `grep -a`): chuỗi `SIM_LOSER_TIME_STOP_HOURS`, `SIM_COND_EXIT_HOURS`, `SIM_COND_EXIT_MIN_FAV` có trong `tradecore/Configs.class`; `LOSER_TIME_STOP`/`COND_EXIT` có trong `research/SimulatorMarketLevelTicker1MStopLoss.class` — **ở CẢ HAI** jar B0 `7368be46…` (`sim-jar-gdv2`) và E2 `d944bea5…` (`sim-jar-crashpen`).
- **Jar dùng cho cả 3 arm: jar B0** Kaggle dataset `sim-jar-gdv2`, sha256 **`7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`** (đúng jar sinh `de-p1`). Không cần key phạt ⇒ không dùng E2. `jar_sha256` trong `result.json` phải = `7368be46…` cả 3 arm, lệch ⇒ DỪNG.
- **Kernel:** `tools/kaggle_sim.py` bản có guard **NOWRITE242 + PREFLIGHT** (branch `fix/no-write-242`, commit `302bc211`; **CHƯA merge** vào `module` lúc chốt) — lấy nguyên văn `git show fix/no-write-242:tools/kaggle_sim.py`; submit script assert `NOWRITE_HOST` và `SYMBOL_MAPPER_PREFLIGHT_FAIL` có trong `KERNEL_TEMPLATE`.

## 2. Cấu hình — B0 nguyên văn (`~/kaggle_sim/out/de-p1/result.json`)
- Profile `r4_kg0_k16_f015_g155` + overrides: `SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_DAYS=90`, `SIM_GATE_ROLLING_PCT=0.999950829`, `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`.
- Bundle `sim-x1-2021-bundle` + ticker `wfo-ticker-2021…2025h2`; `sim_end_date=20251231`; `xmx=22g`; `timeout_s=5400`; `jar_ds=sim-jar-gdv2`; `TICKER_SOURCE=file`. Overrides ghi đè **bản copy profile** (không qua env). DEV ≤ 2025-12-31; 2026 = HOLDOUT, không dùng.

## 3. Arm (KHOÁ, k = 2 + parity)
| arm | tag Kaggle | override THÊM vào B0 | vai trò |
|---|---|---|---|
| **P0** | `exit-time-p0` | (không) — LOSER 168 từ profile, COND tắt | cổng parity |
| **A1** | `exit-time-a1` | `SIM_LOSER_TIME_STOP_HOURS=72` | time-stop phẳng 72h cho lệnh chưa arm |
| **A2** | `exit-time-a2` | `SIM_COND_EXIT_HOURS=72`, `SIM_COND_EXIT_MIN_FAV=0.05` (LOSER giữ 168) | cond-exit 72h × MFE < 5 % |

Không arm thứ 3, không quét H/MIN_FAV, không chạy lại arm (trừ lỗi **hạ tầng** — chạy lại cùng tag, ghi rõ).
**Cổng 0 — parity P0 (bắt buộc):** `md5(printDone.csv) = 650c386f0d0dfea334af9d55ca2f21d4`, **n = 2517**, **equity = 131908**, jar `7368be46…`, mapper ≥ 800. Lệch bất kỳ ⇒ **VOID toàn vòng**, DỪNG, không đẩy A1/A2. Trình tự: P0 trước; PASS mới đẩy A1, A2.
**Cổng 1 — key có hiệu lực:** `profile_hash` A1/A2 ≠ P0 **và** md5 printDone A1/A2 ≠ P0; A1 không còn lệnh `STOP_LOSS_DONE` với `time_order` > 73h. Fail ⇒ arm đó VOID (key không được đọc).

## 4. Thước đo (KHOÁ) — so mỗi arm với **B0 = P0**
Driver Python offline mới `research/analysis/exit_time_b0_driver.py` = `flat3_crashpen_driver.py` đổi arm/tag/jar + luật GO dưới; tái dùng `reset_rule_score` (load_legs/load_daily/core_metrics/ci_pair/run_mtm), cửa sổ 2022+ theo `feat_add_v1_score`. Chấm AS-IS (phí base trong artifact). `k = 2` ⇒ **inflate = √(2 ln 2) = 1,1774**.

**(i) PRIMARY — ΔPnL ghép cặp theo lệnh** (logic `research/analysis/long_levers_paired_ruler.py`): khoá `sym|start|level`; lệnh khớp `(profit_arm − profit_B0)/100 × notional_B0`; lệnh chỉ 1 phía ± `profit/100 × notional` của chính nó. CI bootstrap **block-72h** theo giờ vào (neo 2021-07-01), **NREP 2000, seed 20260905**; báo CI raw và CI inflate (nửa-độ-rộng × 1,1774 quanh điểm). **KHÔNG dùng ΔCalmar bootstrap** (vô lực, AUDIT §3.1).
**(ii) Equity / MTM:** n, equity cuối, ΣPnL, CAGR, maxDD MTM phút, UW MTM (ngày), **Calmar_MTM = CAGR/|maxDD MTM phút|**, ở **toàn kỳ** (2021-07-01→2025-12-30) **và 2022+**; ROI/năm, maxDD MTM/năm, qmin.
**(iii) Theo năm:** ΔPnL ghép cặp theo **năm vào** 2021H2…2025; ROI/năm từng arm.
**(iv) §9 T1–T4 vs B0** (định nghĩa như `flat3_crashpen_driver.py`): T1 maxDD MTM phút/năm ≥ −40 %, UW ≤ 250, qmin ≥ −20 %, 0 năm âm, conc ≤ 15 %; T2 q* ≥ 15 %, top-1 % ≤ 25 %; **T3 (CHỈ THÔNG TIN)** Δwin% ≥ −2 pp, ΔTSloss% ≤ +2,5 pp, mP|SM & mP|SL không xấu có ý nghĩa; T4 Calmar_MTM ≥ 0,90 × B0 (2 cửa sổ) và conc ≤ B0.
**Báo kèm (mô tả):** số lệnh bị cắt bởi luật mới (`STOP_LOSS_DONE` có `time_order` < 167h), mean profit nhóm đó vs chính các lệnh đó ở B0; số "thắng muộn bị cắt" (khớp, B0 = `STOP_MARKET_DONE`, arm = `STOP_LOSS_DONE`) và ΔPnL của nhóm này; ΔPnL tách nhóm lệnh khớp theo status B0; top-5 episode.

## 5. Luật GO-nghiên-cứu (KHOÁ, áp riêng từng arm)
GO ⇔ **cả 4**:
1. ΔPnL ghép cặp > 0 **và** cận dưới CI **raw** > 0 **và** cận dưới CI **inflate** > 0;
2. ΔPnL ghép cặp theo năm vào > 0 ở **≥ 3/4 năm 2022–2025**;
3. **Calmar_MTM(arm) ≥ Calmar_MTM(B0)** ở **cả toàn kỳ và 2022+** (không có nhân 0,90);
4. **T1 PASS**.
Cả hai GO ⇒ chọn arm có **cận dưới CI-inflate cao hơn**. Không arm nào GO ⇒ **NO-GO** (đóng lever thời gian sống trên DEV).
**T3 KHÔNG là điều kiện GO-nghiên-cứu** (lệch cơ học: lệnh bị cắt sớm đổi nhãn sang `STOP_LOSS_DONE`); báo đầy đủ; **owner quyết T3 ở bước apply**. T2/T4 báo cáo.
GO-nghiên-cứu ≠ apply: không đổi profile live/shadow trong vòng này.

## 6. Kỳ vọng ghi TRƯỚC — [SUY LUẬN từ AUDIT §2.6/§5, counterfactual tuyến tính close 1h]
- Tham chiếu B0: n 2517, eq 131 908, ΣPnL 96 909, CAGR 34,31 / maxDD MTM −17,68 / **Calmar 1,940**; 2022+ CAGR 33,56 / **1,898**; UW 87; win% 85,86; TSloss% 14,30; năm 2021H2 +6,5k · 2022 +4,6k · 2023 +24,9k · 2024 +30,8k · 2025 +30,1k.
- **A1:** ΔPnL **+1,5k … +11,3k** (cận dưới = cắt cả lệnh "arm bằng high" mơ hồ; cận trên = giữ chúng); CF theo năm (cận trên) 21/22/23/24/25 = +2,3/+2,2/+0,4/+1,8/+4,5k. **A2:** giữ lệnh đã chạm +5 % ⇒ kỳ vọng nằm phía cận trên của A1 hoặc cao hơn, nhưng cắt ít lệnh hơn.
- Nửa-độ-rộng CI dự kiến 5–8k ⇒ **MDE80 ≈ 8–13k** (inflate k=2), **power ≈ 15–45 %** ⇒ khả năng NO-GO cao **kể cả khi hiệu ứng thật dương**. Rủi ro dấu âm có thật (B_FOLLOWUP T170 fixed-96: eq −7 %).
- T3: `TSloss%` dự kiến **tăng** +2…+4 pp, `win%` giảm (cơ học, E1/F2).

## 7. Cấm / giới hạn khai trước
- Không đổi arm/H/MIN_FAV/luật sau khi thấy số; không dùng 2026; 1 lần/arm.
- 0 sim Java trên Oracle; không chạm 242/shadow; không sửa `.java`, không build; không push printDone.
- Lệnh bị cắt sớm giải phóng slot/vốn ⇒ có thể sinh lệnh **mới** (only_arm) — thước ghép cặp tính đủ (± chính nó); đây là một phần hiệu ứng thật của lever.
- MTM phút dùng close 1m (cận dưới DD thật); 1 quan sát lịch sử; mọi phân rã §2 AUDIT là hậu kiểm ⇒ vòng này là kiểm định duy nhất, không tune tiếp.
