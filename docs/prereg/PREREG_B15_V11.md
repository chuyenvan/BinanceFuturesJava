# PREREG_B15_V11 — size ×1,5 trên gói v1.1 (K24+skipFull + TS_MKT_EXT X14): DEV 8 seed + HO 2026 W9 8 seed

Ngày 2026-10-21. Viết và commit TRƯỚC khi chạy/đo bất kỳ run S15 nào. Sau commit: không đổi tham số, cửa sổ, luật, kịch bản stress.
2020 niêm phong (không dùng). Không đụng 242 / shadow / Binance REST.

## 0. Bối cảnh
- ISO_RISK (`docs/result/ISO_RISK.md` e65c456a; prereg 5caf3c7f + add 1 a4a10881): arm B15 = OFF (K24+skipFull) với
  `SIM_F_BASE=0.0225` (profile `r4_kg0_k16_f015_g155` mặc định `SIM_F_BASE=0.015` ⇒ ×1,5): CAGR22 37,0→45,1, DD22 −22,5→−24,7,
  Calmar 1,65→1,83, 8/8 — DEV in-sample, chưa kiểm ngoài mẫu, chưa trừ impact theo size.
- Gói v1.1 đang shadow = K24+skipFull + X14 (`docs/result/TS_MKT_EXT.md` c1ab8eda, `TS_MKT_EXT_HO.md` 46ebc1ee).
- Cơ chế size (Java `TradeUtils.managerBudget`): budget/leg = equity × F_BASE × clamp(1 − U/U_MAX) / ladder × tier × w_i.
  Trần gross: U = margin mở / equity ≥ U_MAX (0,60) ⇒ chặn lệnh mới (không log đếm). Trần per-coin `CONC_CAP_PERCOIN_PCT=0.15`
  ⇒ chặn leg (log `[CONC-PC] SUMMARY blocked=`). Size ×1,5 KHÔNG đổi U_MAX/per-coin ⇒ trần chạm sớm hơn (đây là điều cần đo).

## 1. Arm (chỉ 2, không biến thể khác)
| arm | định nghĩa | DEV tag | HO tag |
|---|---|---|---|
| P | X14 nguyên bản (run có sẵn) | `tsx-x14-<seed>` | `tsx-ho-x14-s<seed>` |
| S15 | X14 + `SIM_F_BASE=0.0225` (đúng cờ ISO_RISK B15) | `b15-x14-<seed>` | `b15-ho-x14-s<seed>` |

- Jar `sim-jar-tsx` sha256 cc0f9d11… (không build lại). DEV: hạ tầng `tsx_driver.py`/`burst_cooldown_driver.push` (sim_end 20251231),
  seed A1 S7 S13 S21 S99 S123 S777 S2024. HO: `ho4p1_queue.push` (end 20261001, unseal) như `tsx_ho.py`, seed 42 7 13 21 99 123 777 2024,
  cờ X14 HO = `ho_flags.json` của TS_MKT_EXT HO (không tính lại).
- Kiểm cờ size (V3, trước S15): `b15-f015-a1` (DEV, X14 + `SIM_F_BASE=0.015` tường minh) và `b15-ho-f015-s42` (HO).

## 2. Kiểm hợp lệ (fail bất kỳ ⇒ dừng mục đó, báo, không chấm)
- V1 P DEV tái lập TS_MKT_EXT: mean CAGR22 = 39,49 ± 0,1; mean DD22 MTM = −22,55 ± 0,1 (cùng `n700_driver.arm_metrics` + `gvz_mtm`, missing=0).
- V2 P HO tái lập: mean ROI W9 = 12,49 ± 0,1 (= 10,19 + 2,30) bằng hàm `ho4_score_a` như `ecm_mtm_h.py` (giá close 1m Vision).
- V3 size=1,0 qua cờ: md5 printDone `b15-f015-a1` == `tsx-x14-a1` VÀ `b15-ho-f015-s42` == `tsx-ho-x14-s42` (bit-exact). S15 DEV chỉ push sau
  V3-DEV PASS; S15 HO chỉ push sau V3-HO PASS.
- V4 parity mỗi run S15: jar sha, ok, override ghi nhận đủ (TOPK 24, skipFull, B0OV, X14 keys, `SIM_F_BASE=0.0225`), dòng `[TSX] extHours=336`;
  HO thêm `ho4p1_queue.check` PASS.
- V5 MTM: DEV `missing=0` mọi key; HO `eqcheck.final_ok` mọi run.
- V6 stress: equity "legacy" của key stress == key gốc (lệch tương đối ≤ 1e-9); CAGR22 tự tính với cost=0 == arm_metrics (≤ 1e-9).

## 3. Chỉ số (mỗi seed, P và S15)
DEV: CAGR22, DD22 MTM phút, DD MTM toàn kỳ (seed tệ nhất + median), Calmar22 = CAGR22/|DD22|, UW22 (ngày), ΣPnL & ΔPnL, theo năm
2022–2025 (ΣPnL, DD MTM năm, Calmar năm = ROI năm/|DD năm|), gross_max & conc_coin_max (`gross_conc`), `[CONC-PC] blocked` (S15−P),
Δ số lệnh, số lệnh vào khi U_hat ≥ 0,54 (= 0,9·U_MAX; U_hat dựng lại = Σ margin mở / equity ngày — xấp xỉ, mô tả), ΣPnL/Σnotional.
HO W9 (2026-01-01→2026-10-01 +07): ROI, maxDD MTM phút, Calmar_W9 = cagr_ann/|maxDD|, ΣPnL, n, Q1/Q2/Q3 (ROI, DD, ΣPnL) mô tả, cùng nhóm phơi nhiễm.

## 4. Stress impact (mô hình EDGE_ATTR 4852f57e, áp cho CẢ P và S15)
- c = Y · σ_d · √(N_leg · sc / L24), N_leg = cột `margin` printDone (= notional), σ_d, L24 tính như `edge_attr_build.leg_features`
  (cửa sổ [M−1439, M] kline1m Vision). Chi phí leg = 2·c·N_leg (vào + ra), ghi toàn bộ vào phút đóng lệnh (hậu kiểm bậc 1, không tính lại sizing).
- sc: DEV = vốn/35 000 (như EDGE_ATTR); HO = vốn/eq0_W9 của chính run đó (pilot bắt đầu 2026-01 với đúng vốn đó). HO chỉ áp leg đóng trong/sau
  cửa sổ (e ≥ 0); leg đóng sau cửa sổ ghi ở phút cuối.
- Leg thiếu đặc trưng (L24 ≤ 0, σ_d không hữu hạn, hoặc nbar < 60) ⇒ c = phân vị 99 của c các leg hợp lệ cùng run & kịch bản.
- Kịch bản: I10 = Y=1, vốn 10k (pilot); **I20 = Y=1, vốn 20k (2× vốn) = kịch bản CHÍNH cho luật**; I20Y2 = Y=2, vốn 20k (mô tả).
- Đo dưới stress: CAGR22 (equity ngày − chi phí luỹ kế), DD MTM (cùng `run_mtm`, cột chi phí), Calmar; HO: ROI/maxDD/Calmar W9.

## 5. Luật
**GO DEV** (tất cả): D1 ΔCAGR22 > 0 ở 8/8 seed; D2 |DD MTM toàn kỳ| seed tệ nhất của S15 ≤ 40 %; D3 ΔCalmar22 ≥ 0 ở ≥ 6/8;
D4 D1–D3 vẫn đúng khi cả hai arm chịu I20.
**CONFIRM HO W9** (tất cả, đây là phần ngoài mẫu thật của B15): H1 ΔROI_W9 > 0 ở ≥ 6/8; H2 |maxDD_W9| seed tệ nhất của S15 ≤ 40 %;
H3 ΔCalmar_W9 ≥ 0 ở ≥ 5/8; H4 H1–H3 vẫn đúng dưới I20. Q1/Q2/Q3 chỉ mô tả.
- DEV và HO chạy song song (HO không phụ thuộc kết quả DEV); nếu DEV NO-GO thì HO chỉ mang tính mô tả. Kết luận "đạt" chỉ khi GO + CONFIRM.
- Thiếu seed (run lỗi sau 1 lần chạy lại) ⇒ luật tính trên 8 với seed thiếu = không đạt.

## 6. Ghi trước
- Size là tham số triển khai. Nếu GO + CONFIRM: quyết định áp dụng (đổi shadow ⇒ reset cửa sổ promotion, hay áp lúc go-live) là của OWNER.
  Agent không đề xuất thay đổi 242, không chạm shadow.
- Giới hạn: impact √ chưa hiệu chuẩn cho alt; chân SL trong phút sập có thể trượt hơn; trần gross không có log đếm (chỉ U_hat xấp xỉ);
  S15 tăng notional ⇒ impact tăng ~√1,5 trên mỗi USD.
- Output: `docs/result/B15_V11.md` + `docs/result/b15_v11/` (script, JSON nhỏ). Không push.
