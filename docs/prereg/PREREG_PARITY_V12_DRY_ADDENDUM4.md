# PREREG_PARITY_V12_DRY — ADDENDUM 4: sửa thiết kế V-OVL (2026-10-31, TRƯỚC mọi số A/C)

Gốc: ADD2 (bb9571fb), ADD3 (299f00b0). Lý do (MASTER duyệt): cổng "≥99 % ô trùng" đo sự khác nhau của SỔ (sim vs sổ giấy live) và tập top-24 (r4f bỏ LEGACY trước xếp hạng; trước 10-16 chỉ top-16), không đo r. Chưa có số A nào (Kaggle chưa chạy, Vision 2026-10 monthly = 404 lúc 2026-10-30 18:45 UTC).

## 1. V-OVL mới (thay ADD2 §3 V-OVL và ADD3 §2 cổng (i)–(iii))
- Đoạn chồng lấn: ngày 2026-10-17..10-24 và 10-28..(T_cut−1) (+07), chỉ ngày C′ ghép 100 %; loại 10-25..10-27.
- C′ = record live đã làm sạch (bỏ TRADFI/INDEX, bỏ coin giữ sổ giấy) trên đoạn chồng lấn. A = trace sim (ts, sp, p15, r).
- **(i) r trên giao:** cặp (symbol, phút) có ở cả A và C′ (ghép (ts, sp_A) = (ts, gateValue_live), float32 bằng nhau); ĐẠT ⇔ ≥ 99 % cặp có |Δr|/r ≤ 1e-9.
- **(ii) q theo giờ:** với mỗi giờ h trong đoạn chồng lấn, q_A(h) = phân vị (pct 0,999950829, cửa sổ 90 ngày, k = floor(pct·(m−1))) trên record A ts ∈ [h−90d, h); q_mix(h) = cùng phép tính trên {A ts < 10-17} ∪ {C′ ts ∈ [10-17, h)} ∪ {A trên ngày bị loại}. ĐẠT ⇔ median |q_mix−q_A|/q_A ≤ 1 % VÀ max ≤ 5 %.
- **(iii) không giao — chỉ báo:** đếm và phân loại: giữ chỉ ở A / chỉ ở live (sổ khác); LEGACY bị bỏ ở r4f; top-16 trước 10-16; feat_dump tắt; universe; khác.
- Seed (A ∪ C) dùng được ⇔ (i) ĐẠT VÀ (ii) ĐẠT. TRƯỢT ⇒ DỪNG, không nới.

## 2. Hệ quả kỹ thuật (cố định trước)
- Key sim: `SIM_GATE_TRACE_FROM` = 2026-07-15 00:00 +07 (để tính q_A cho mọi giờ chồng lấn), `SIM_GATE_TRACE_TO` = T_cut; `SIM_GATE_DUMP_AT` = T_cut.
- Funding: CHỜ Vision monthly 2026-10 (không REST, không nguồn thay thế). T_cut = 2026-11-01 00:00 +07.
