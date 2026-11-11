# R3b — hiệu chỉnh pct (2022) + sàng quota 2023–25 (prereg PREREG_R3B_SMOOTH_ISO 3ea5df40) — 2026-11-11

Script `research/r3_gate/r3b_calib.py` (gate_offline, pred n4f-b0 8 seed, held printDone n4f-b0-*, chỉ đếm; cấm pnl/MTM). Raw `docs/result/r3b_iso.json` (commit 6ec1c25c).
T22 = Σ8 seed cell pass A0 năm 2022 = 4 345. Tìm nhị phân pct ∈ [0,99990; 0,999999], ép float32, dừng |N/T−1| ≤ 5 %.

| Arm | pct (float32) | vòng | N22 / T22 | quota 2023–25 (median 8 seed, arm/A0) [min; max] | Kết luận |
|---|---|---|---|---|---|
| B1 MEAN15 | 0.999961853 | 3 | 1,003 | 1,30 [1,155; 1,532] | **LOẠI** (ngoài [0,75; 1,25], luật §3) |
| B2 MEAN60 | 0.999968052 | 4 | 0,995 | 1,13 [0,969; 1,237] | **QUA** → Pha 1 |

Ghi chú: hiệu chỉnh trên 2022 không giữ được quota MEAN15 ở 2023–25 (đuôi không dừng, xem §6 prereg). Không chỉnh tham số.
Pha 1 B2: jar r3_wt 26581b54 (AS-FILE + key SIM_GATE_P15_SMOOTH=60:48), STUB sha256 d0a34afa…, sec-check ×2 OK, 280 test 0 fail; G0 (smooth TẮT) phải byte-identical n4f-b0-a1 trước khi chạy arm.
