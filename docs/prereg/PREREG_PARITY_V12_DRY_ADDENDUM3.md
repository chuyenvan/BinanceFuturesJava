# PREREG_PARITY_V12_DRY — ADDENDUM 3: seed cuối = A (sim) + C (đuôi live sạch) (2026-10-31, viết TRƯỚC khi tính)

Gốc: PREREG_PARITY_V12_DRY (3c7dae05) + ADD1 (7788cce9) + ADD2 (bb9571fb, kết quả 5f3de773). Chưa chạy kernel nào, chưa có số A/C.

## 1. Thành phần
- **A (sim):** run `nt-x14-s42` (cfg y hệt: profile r4_kg0_k16_f015_g155 + overrides result.json, universe A1 noTF/INDEX, K24+skipFull, X14), jar = nhánh `research/gate-seed-dump` (a8690d46 + key mới, STUB). Key: `SIM_GATE_DUMP_FILE`, `SIM_GATE_DUMP_AT = T_cut`; `SIM_GATE_TRACE_FILE`, `SIM_GATE_TRACE_FROM = 2026-10-17 00:00 +07`, `SIM_GATE_TRACE_TO = T_cut`. Dump = mọi record ts ∈ [T_cut − 90d, T_cut).
- **T_cut** = 00:00 +07 ngày đầu tháng kế tiếp tháng cuối có Vision **monthly** klines VÀ fundingRate (exporter chỉ đọc funding monthly: `FURL .../monthly/fundingRate`). Hiện tại tháng cuối = 2026-09 ⇒ phải chờ bản monthly 2026-10 (dự kiến 11-01..11-03) ⇒ T_cut = 2026-11-01 00:00 +07. KHÔNG thay funding bằng REST/daily nếu không có addendum mới.
- **C (đuôi live):** `gate_ratio_live.bin` của jar đang chạy, ghép `sel_dump` theo (ts, r float32), bỏ TRADFI/INDEX (exchangeInfo mới nhất trước deploy) và coin giữ trong sổ giấy; chỉ lấy ngày ghép 100 % (sel_dump đủ top-24). Ngày không đạt ⇒ bỏ cả ngày, ghi số.
- **Seed = A ∪ C** (C từ T_cut tới lúc dựng), sort ts, GRR1. Khe T_cut → giờ deploy: dựng lại seed sát giờ deploy bằng 1 lệnh `bash ~/claude_master/gst1030/seed/build_seed.sh` (đọc A cố định + kéo C mới nhất từ 242, chỉ đọc 242); không có lệnh nào ghi 242.

## 2. V-OVL (giữ nguyên ADD2, không nới)
- Ngày chồng lấn: 2026-10-17..10-24 và 10-28..(T_cut−1); loại 10-25..10-27 (feat_dump tắt) và ngày ghép < 100 %.
- Ghép ô A↔C′: (ts, sp) của trace ↔ (ts, gateValue) của sel_dump, so sánh float32 bằng nhau (sp duy nhất mỗi symbol mỗi phút ⇒ tương đương (ts, symbol)).
- Cổng: (i) |ô chung| / |ô hợp| ≥ 99 %; (ii) ≥ 99 % cặp |Δr|/r ≤ 1e-9; (iii) q từng giờ của buffer A so với buffer "A trước 10-17 + C′ từ 10-17": |Δq| ≤ 1e-9 ở ≥ 99 % giờ.
- **Dự báo ghi trước:** (i) có thể TRƯỢT vì sổ sim ≠ sổ giấy live (tập coin giữ khác) và live r4f bỏ LEGACY trước khi xếp hạng (top-24 lệch). Báo phân rã nguồn lệch (giữ chỉ ở A / chỉ ở live / ngoài top-24 / universe) — chỉ để giải thích, không đổi cổng.
- TRƯỢT bất kỳ ⇒ DỪNG, seed A không được nạp, báo MASTER.

## 3. Kaggle (chuẩn bị, chạy khi Vision 2026-10 monthly có)
x26-q4 (S = [10-01, T_cut), months 2026-09..10, fund_months 2026-08..10, A1 exclude như nt-x26) → tk26 bổ sung → chain-y26 tới T_cut (OI metrics daily) → sim `nt-x14-s42` có key §1. Chỉ tải về Oracle: file dump (~10 MB) + trace (≤ 100 MB) + log/printDone.
