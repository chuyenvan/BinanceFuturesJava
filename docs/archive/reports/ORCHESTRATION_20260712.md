# ORCHESTRATION — Điều phối campaign (2026-07-12)

> Mô hình: Claude = master. Mỗi CỤC có **check-in** (điều kiện vào + input) và **check-out** (acceptance đo bằng SỐ).
> Master launch khi check-in đủ, **monitor liên tục** (tự bắt OOM/drift/done), tự sửa lệch, CHỈ hỏi Uni ở
> **cổng quyết định verdict** (không hỏi vặt, không chờ push). Job nền: pid + log + monitor (luật CORE/run-226).

## Trạng thái tài nguyên (điều phối theo RAM/CPU)
- **Oracle** 4-core / 23GB: đang bận WFO compare (2 worker Xmx8g ~16GB). KHÔNG chồng job nặng khác lên.
- **226**: Aerospike raw (đọc được từ dev qua client). Rảnh CPU.
- **Kaggle**: 5 kernel, 4-core/31GB mỗi kernel, độc lập. RẢNH — dùng cho job nặng song song (leak retrain, optimize HPO).
- **dev (Windows)**: build jar + unit-test. KHÔNG chạy validate/WFO data.

## DAG (song song hoá)
```
P0 WFO-COMPARE (đang chạy, monitored) ──┐
P1 LEAK-AUDIT (B1/B2/B4 trên 2 ds)  ────┤→ P3 DECISION-GATE (B6: maxFav3 vs ret2) → Uni chốt
P2 WARN-TRIAGE (D1/D2/C2)          ─────┘        │ ĐẠT
                                                  ▼
                                    P4 OPTIMIZE (HPO Kaggle distributed) → P5 WFO lại → verdict cuối
```
P1, P2 chạy SONG SONG với P0 (không đụng Oracle-RAM: P1 leak-check nhẹ/Kaggle, P2 phân tích read-only).

---

## CỤC (chunk)

### P0 — WFO COMPARE 2 chiến lược [ĐANG CHẠY, monitored]
- **check-in:** 2 dataset apples-to-apples (pred.bin md5 SAME, chỉ funding khác) ✅; gate 2021-2022 vá ✅.
- **steps:** reset→2 worker maxfav3→report→reset→2 worker ret2→report (Oracle).
- **check-out:** 2 file `wfo_report_{maxfav3_4h,ret2_4h}.md` có VERDICT + %OOS-dương + WFE median + maxDD, TÍNH TRÊN CỬA SỔ CÓ DATA (2022→2025).
- **monitor:** taskId bvrfjap37 (poll 150s, bắt OOM/done). **Sơ bộ: maxFav3@4h = 11.8% OOS+ (2/17) — thấp, chờ ret2 + đọc cửa sổ phủ.**

### P1 — LEAK AUDIT 2 dataset [song song P0, CHẠY ĐƯỢC NGAY - nhẹ/Kaggle]
- **check-in:** 2 dataset đã build ✅.
- **steps:** B1 (OOS≥cutoff+embargo) + B4 (no future coin) trên mỗi predDir; B2 shuffle-test (Kaggle retrain nhãn-xáo). Đặc biệt: xác minh ret2 `predict_wf_20260101.bin` (nghi 1-cutoff leaky) có ảnh hưởng cửa sổ ≤2025 không.
- **check-out:** bảng B1/B2/B4 PASS/FAIL mỗi dataset; kết luận "so sánh có công bằng (không dataset nào leak trong vùng phủ)".

### P2 — WARN TRIAGE [song song, read-only]
- **check-in:** report validate FULL ✅.
- **steps:** D1 (37k funding giờ lẻ — tz thật hay bug?), D2 (94 ngày gap — coin nào/ảnh hưởng majors?), C2 (134 nến nhảy — bad-tick hay crash 2025-10-11 thật?).
- **check-out:** mỗi WARN → phán "vô hại / cần sửa"; nếu cần sửa → task fix riêng.

### P3 — DECISION GATE B6 [Uni chốt — cổng người]
- **check-in:** P0 + P1 xong (verdict 2 chiến lược + xác nhận không leak).
- **check-out (Uni quyết):** maxFav3@4h có ĐẠT ngưỡng (WFE≥0.5/%OOS+≥70%/maxDD≤50% trên cửa sổ phủ) VÀ hơn ret2? → ĐẠT: sang P4. KHÔNG: §6 SOLUTION_FRAMEWORK (đổi nhánh/dừng). Cũng chốt: horizon (4h/12h?), risk4H=0 có cần sửa.

### P4 — OPTIMIZE MODEL [chỉ khi P3 ĐẠT — Kaggle distributed]
- **check-in:** Uni chốt ĐẠT + hướng tối ưu.
- **steps:** jobstore@226 (shared) + upload dataset Kaggle + ≤5 kernel WfoWorker/HPO song song (RunHpoMaster_Distributed). Đây là chỗ Kaggle master-worker bung tốc.
- **check-out:** edge cải thiện đo trên WFO leak-free + provenance E1-E3.

### P5 — WFO LẠI sau optimize
- **check-in:** P4 có model tối ưu (artifact mới → trigger re-validate stamp).
- **check-out:** preflight PASS + WFO verdict mới, so baseline. Uni chốt bật tiền thật.

---

## LUẬT AUTO (không chờ push)
1. Job nền LUÔN: pid `~/claudedata/.run/<job>.pid` + log + **1 monitor** (bắt done/OOM/Exception/process-chết — run-226 §21).
2. Master poll qua monitor; **lệch (OOM/stale/job-fail) → tự xử**: kill đúng pid + requeue/giảm worker + relaunch; ghi lại.
3. Song song theo RAM: KHÔNG 2 job nặng cùng Oracle; đẩy job nặng thứ 2 sang Kaggle/226.
4. CHỈ escalate Uni ở **P3** (verdict) + blocker thật (mất access/data hỏng không tự sửa được). Còn lại tự quyết reversible + ghi log.
