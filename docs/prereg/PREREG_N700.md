# PREREG_N700 — Tăng số lệnh dưới luật owner MỚI (PnL ưu tiên, maxDD MTM ≤ 40 %, giữ gate quota)

Ngày chốt: **2026-10-03** (GMT+7). Chốt **TRƯỚC** khi đẩy bất kỳ kernel nào của vòng này. Không sửa thiết kế sau khi thấy số; mọi đổi = AMENDMENT commit trước khi xem số bị ảnh hưởng.

**Bối cảnh / quyết định owner 10-03:** tăng số lệnh dần (≈ 500 → 700/năm); **PnL ưu tiên**; T3 (win%, TSloss%) **chỉ thông tin**; chấp nhận **maxDD MTM ≤ 40 %**; **giữ gate quota** (rolling ratio-quantile). `docs/audit/AUDIT_CHAIN_AND_N_20261003.md` (`c733467c`): n = ρ × luồng ứng viên; K (`SELECTOR_RANK_TOPK`) và pct (`SIM_GATE_ROLLING_PCT`) là **cùng một lever** (độ rộng ống); quota ×2 ⇒ +31 % lệnh (cận trên thô).
**Không chọn theo kết quả cũ:** K24 (`de-p2`: n 3526, CAGR 37,1, maxDD MTM −22,2, Calmar 1,67, 2022 ΣPnL 2,4k vs 4,6k) chạy trên ảnh Kaggle CŨ (md5 B0 cùng đợt = `650c386f`, ≠ ảnh hiện tại `ff3ce513`) và chưa từng được chấm bằng thước MTM paired + luật mới; pct nới chưa từng chạy trên B0. Vòng này chấm lại cả hai bằng **một thước, một luật** khai dưới đây.

## 1. Nền (KHOÁ)
- **B0** = `~/kaggle_sim/out/selab-p0` — md5 printDone **`ff3ce513edf2316088a4b5ac464f76dc`**, n 2517, eq 131 908. Profile `r4_kg0_k16_f015_g155` + override `SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_DAYS=90`, `SIM_GATE_ROLLING_PCT=0.999950829`, `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`. Jar `sim-jar-gdv2` sha256 **`7368be46…`**, bundle `sim-x1-2021-bundle`, `sim_end_date=20251231`, xmx 22g.
- **G42** (nền GEOM-K16) = `~/kaggle_sim/out/geom-g42` — md5 `a4b36d7d…`, n 2502, eq 141 162. Đường sim = `research/analysis/s1_geom_sim.py submit` (template `label_firsthit_sim.template()`, bins GEOM seed 42 từ dataset Kaggle `geom-bins-g42`, `want_bins_sha` = `6171f2cc…` trong `~/claude_master/1003/geom/sim_sha256.json`), cùng profile + 6 override B0.
- **Kernel:** `tools/kaggle_sim.py` HEAD (`module`, NOWRITE242 + PREFLIGHT), md5 **`8b60b00afad39f2528aaa15092225c9b`** — assert trước khi submit. 0 build, 0 sửa `.java`, 0 Java sim trên Oracle, 0 chạm 242/shadow.

## 2. Arm (KHOÁ, k = 4) — mỗi arm đổi ĐÚNG 1 override so với nền của nó
| arm | tag Kaggle | nền | override thêm | lever |
|---|---|---|---|---|
| **A1** | `n700-a1` | B0 | `SELECTOR_RANK_TOPK=24` | K16 → K24 |
| **A2** | `n700-a2` | B0 | `SIM_GATE_ROLLING_PCT=0.99985` (K16) | quota pct: 1−pct 4,92e-5 → 1,5e-4 (×3,05) |
| **A3** | `n700-a3` | G42 | `SELECTOR_RANK_TOPK=24` | K24 trên model GEOM |
| **A4** | `n700-a4` | G42 | `SIM_GATE_ROLLING_PCT=0.99985` (K16) | pct trên model GEOM |
| B0REF | `n700-b0ref` | — | (không) = B0 nguyên văn, đường `ks.submit` | cổng parity ảnh Kaggle |

- A1 **chạy lại** (không tái dùng `de-p2`): `de-p2` thuộc ảnh cũ (md5 B0 cùng đợt `650c386f` ≠ `ff3ce513`). Bằng chứng bổ sung (thông tin): so từng ô printDone A1 vs `de-p2` theo giá trị float32.
- Không arm thứ 5, không quét K/pct khác, không chạy lại arm (trừ lỗi **hạ tầng** ⇒ chạy lại cùng tag 1 lần, ghi rõ).
- Thứ tự (≤ 2 kernel song song): {B0REF, A1} → {A2, A3} → {A4}.

## 3. Cổng
- **Cổng 0 — parity ảnh (B0REF):** n = 2517, round(eq) = 131 908, jar `7368be46…`, mapper ≥ 800 **và** printDone B0REF **giống `selab-p0` từng ô theo giá trị float32** (`selector_ablation_driver.printdone_valeq`, 0 ô lệch, cùng số dòng). md5 = `ff3ce513` ghi lại (bằng chứng bổ sung, không bắt buộc). FAIL ⇒ arm cùng đợt so với B0REF/ nền cùng đợt không hợp lệ ⇒ **VOID**, dừng, báo.
- **Cổng 1 — key có hiệu lực:** mỗi arm: `profile_hash` ≠ nền (A1/A2) và md5 printDone ≠ nền; `prof_run.properties` chứa đúng override; A3/A4: `sel.bins_ok = true` và `bins_sha256 = 6171f2cc…`. Lệch ⇒ arm đó VOID.
- jar ≠ `7368be46…` hoặc mapper < 800 ở bất kỳ arm ⇒ DỪNG.

## 4. Thước đo (KHOÁ) — driver `research/analysis/n700_driver.py`
Python offline, tái dùng `reset_rule_score` (load_legs/load_daily/core_metrics/run_mtm), `feat_add_v1_score` (cửa sổ 2022+ của MTM), `selector_ablation_driver.daily_boot/ci_of/overlap`, `flat3_crashpen_driver.hour0`. Chấm AS-IS (phí base trong artifact, `R.MTM_COSTS = legacy`). DEV ≤ 2025-12-30; 2026 = HOLDOUT, không dùng.
**Cửa sổ chính = 2022-01-01 … 2025-12-30** (equity ngày rebase tại 2021-12-31, giống `RESULT_S1_FEAT_GEOM`); toàn kỳ 2021-07-01… báo kèm.
**Đa so sánh:** k = 4 arm ⇒ **inflate = √(2 ln 4) = 1,6651** (nửa-độ-rộng CI quanh điểm × 1,6651).

**(i) PRIMARY — ΔCAGR paired trên lợi suất ngày MTM (b+unP cuối ngày từ sim.out):** moving-block bootstrap **PAIRED** (cùng chỉ số khối cho mọi chuỗi), **block 10 ngày, NREP 2000, seed 20260905** (`SAD.daily_boot`), trên 7 chuỗi cùng lúc (B0, G42, A1–A4, B0REF). Báo ΔCAGR, ΔmaxDD (MTM ngày), ΔCalmar, ΔSharpe; CI raw + CI inflate.
**(ii) ΔPnL paired (thay thế cho (i) theo đúng chữ owner "ΔCAGR hoặc ΔPnL"):** ΔPnL ngày = ΣPnL các lệnh **đóng** trong ngày (arm) − (nền); bootstrap block-10d cùng NREP/seed, tổng trên cửa sổ chính; CI raw + inflate.
**(iii) Rủi ro MTM phút:** maxDD MTM phút (`run_mtm`, giá đóng nến 1m ⇒ cận dưới DD) **toàn kỳ** và **2022+**, UW MTM (ngày), **Calmar_MTM = CAGR / |maxDD MTM phút|** (toàn kỳ và 2022+), maxDD MTM/năm.
**(iv) Mô tả:** n tổng, **n/năm = số lệnh ĐÓNG trong 2022–2025 / 4** (theo năm đóng như bảng owner 2a), ΣPnL, equity cuối, win% / SL% (`STOP_LOSS_DONE`) / ROI/lệnh (**thông tin**), exposure (Σmargin mở / equity, time-weighted theo giờ: TB, p95, max), **số lệnh đồng thời p95/max** (time-weighted theo giờ), % ngày có lệnh mở, overlap lệnh với nền (`sym|start`), **crash-sensitivity ước = phần ΣPnL từ lệnh 0h** (`time_order ≤ 0`, đóng trong giờ vào; `F3.hour0`) — n0, ΣPnL 0h, % ΣPnL.
**(v) Theo năm 2022…2025:** n, ΣPnL, ROI% năm (equity compound, `core_metrics.yr`), win%, SL%, maxDD MTM phút năm; ΔROI năm vs nền.

**Contrast chính (quyết GO):** A1−B0, A2−B0, A3−G42, A4−G42. **Chéo (thông tin, không quyết):** G42−B0, A3−B0, A4−B0, A1−A2 (K vs pct ở cùng nền), A3−A1, A4−A2 (hiệu ứng model ở n cao).

## 5. Luật GO §9 MỚI (KHOÁ, áp riêng từng arm vs NỀN của nó) — GO ⇔ **cả 5**
1. **Lợi nhuận:** ΔCAGR (i) > 0 **và** cận dưới CI **inflate 1,6651** > 0 — **HOẶC** ΔPnL (ii) > 0 **và** cận dưới CI inflate > 0. Báo rõ điều kiện nào đạt.
2. **Rủi ro:** maxDD MTM phút của arm ≥ −40 % ở **cả toàn kỳ và 2022+**.
3. **Calmar không giảm quá 20 %:** Calmar_MTM(arm) ≥ 0,80 × Calmar_MTM(nền) ở **cửa sổ 2022+** (toàn kỳ báo kèm, không quyết).
4. **Theo năm:** ΔROI năm (arm − nền) ≥ 0 ở **≥ 3/4 năm 2022–2025**.
5. **Số lệnh:** n/năm (định nghĩa (iv)) ≥ **700**.
T3 (win%, SL%) **không** là điều kiện. GO ≠ apply: không đổi profile live/shadow trong vòng này.
**Lever đề xuất lên shadow:** chỉ xét A1/A2 (model B0 là model deploy; GEOM = NO-GO ở `cf5c90e4`). Nếu cả A1, A2 GO ⇒ chọn arm có cận dưới CI-inflate ΔCAGR cao hơn. A3/A4 = **kiểm độ bền** lever trên model khác: cùng dấu ΔCAGR với arm B0 tương ứng ⇒ ghi "bền qua model"; ngược dấu ⇒ ghi cảnh báo (không đổi verdict A1/A2). Không arm B0 nào GO ⇒ **NO-GO lever n ở vòng này**.

## 6. Kỳ vọng ghi TRƯỚC (từ `~/claude_master/1003/owner_tables_geom_gate.md` bảng 2 + AUDIT_CHAIN_AND_N; [SUY LUẬN])
- **Tham chiếu B0:** n đóng 2022–25 = 423/526/600/534 = 2083 ⇒ **521/năm**; CAGR 2022–25 33,53 %; maxDD MTM phút toàn kỳ −17,68 %; Calmar_MTM toàn kỳ 1,94, 2022+ ≈ 1,90. **G42:** n 2022–25 2068 (517/năm), CAGR 2022–25 35,82, maxDD MTM −17,69.
- **A1 (K24):** từ `de-p2` (ảnh cũ, giá trị kỳ vọng ≈ giống): n 2022–25 = 592/756/839/742 = 2929 ⇒ **≈ 732/năm (đạt c5 sát)**; CAGR toàn kỳ 37,14 (+2,85 pp), maxDD MTM −22,2 (đạt c2), Calmar 1,67 = 0,86× B0 (đạt c3 nếu 2022+ tương tự); 2022 ΣPnL 2,4k vs 4,6k ⇒ ΔROI 2022 **âm**, 2023–25 dương ⇒ c4 = 3/4 (sát). **Điểm mấu chốt = c1:** nửa-độ-rộng CI ΔCAGR raw ước 2–3 pp (S1_GEOM: ±2,6 pp ở inflate 1,18 cho arm khác ít lệnh hơn nhiều) ⇒ inflate 1,665 ⇒ ±3,5–5 pp > hiệu ứng kỳ vọng ~+3 pp ⇒ **P(GO A1) ≈ 25–35 %**.
- **A2 (pct 0,99985, quota ×3,05):** AUDIT_CHAIN_AND_N: quota ×3 ⇒ lệnh +48 % (cận trên thô, khoá dùng sổ B0) ⇒ n ≈ 700–770/năm (c5 sát/không chắc); 85–89 % lệnh thêm rơi vào ngày B0 đã có lệnh ⇒ tăng tập trung theo ngày ⇒ maxDD MTM kỳ vọng xấu hơn K24; lệnh "chỉ-arm" ở các run nới cũ ROI/lệnh 1,5–3,4 % vs B0 4,48 %; lịch sử nới gate (G1 W30, D2) làm Calmar giảm ⇒ **P(GO A2) ≈ 10–20 %**.
- **A3/A4:** kỳ vọng ΔCAGR cùng dấu, cùng cỡ với A1/A2 (lever độc lập model); GEOM nhỉnh B0 ≈ +2 pp CAGR (không ý nghĩa).
- Rủi ro chung: mọi số là DEV đã nhìn nhiều lần (lần test ~28 trên cùng DEV); inflate k=4 không tính lịch sử chọn ⇒ GO ở đây vẫn cần shadow xác nhận.

## 7. Cấm / giới hạn khai trước
- Không sửa `.java`/build, không Java sim trên Oracle, không chạm 242/shadow, không push printDone/bins, không xoá dữ liệu, không secret.
- Không đổi luật/thước/cửa sổ/arm sau khi thấy số. Không thêm arm "cứu" (K20, pct trung gian…) trong vòng này — nếu cần ⇒ pre-reg mới.
- Kernel lỗi hạ tầng (ERROR/timeout không do cấu hình) ⇒ chạy lại cùng tag 1 lần; lỗi lần 2 ⇒ arm VOID, báo.
- Kết quả: `docs/result/RESULT_N700.md` + `docs/result/n700.json`; commit `result(N700): …`.
