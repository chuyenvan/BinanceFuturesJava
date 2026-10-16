# VZ_NEXT_1016 — kế hoạch nghiên cứu sau E1 (MASTER 2026-10-16)

Tầng đo: QUYẾT ĐỊNH CỦA HỆ (đợt vào lệnh / chân của hệ), không phải sự kiện thô. Luật chung giữ nguyên (pre-reg trước khi đo, config commit trước, ledger, Kaggle ≤2 kernel, job nặng chạy `systemd-run --user --scope -p MemoryMax=3G`, không 242, Python logging).
Vai trò năm: 2021–2025 = DEV của hệ (đã tune gate/K) ⇒ mọi kết luận trên đó chỉ là khám phá. Xác nhận: HO 2026 (Vision, 2026-01→09) + backcast 2020 (niêm phong, Phase 1 đang nạp). 2024 = năm khám phá chính.

## R1 — circuit breaker trong ngày (ưu tiên 1, rủi ro, ít bậc tự do)
- Cơ chế: ngày sụp đổ hệ thống (LUNA 2022-05-05: 3 đợt trong 41′, −14,8 % equity) ⇒ đợt sau trong cùng cơn sập thường tiếp tục lỗ.
- Luật ứng viên (chốt TRƯỚC, tối đa 3 biến thể): sau một đợt ≥ N lệnh, chặn đợt mới trong T giờ, với (N, T) ∈ {(13, 2h), (13, 6h), (6, 6h)}.
- Đo: sim 8 seed DEV (CAGR22, maxDD MTM, Calmar, UW) + đếm đợt bị chặn. Cần key sim mới `ENTRY_BURST_COOLDOWN_N`/`_H` (mặc định tắt ⇒ byte-identical, test parity md5).
- GO DEV: maxDD MTM cải thiện ≥ 2 pp VÀ Calmar không giảm (CI 8 seed). Rồi xác nhận HO 2026 (chỉ báo cáo, n đợt nhỏ).

## R2 — bookDepth tại tick vào đợt (dữ liệu mới)
- Vision UM daily `bookDepth` có từ 2023-01-01. Chỉ tải symbol × ngày có trong tập đợt/ứng viên (gqsf-a1 printDone + `vz-cand-2024`), lưu `vz-bookdepth-burst` (Kaggle).
- Feature (as-of ≤ t_dec, causal): độ sâu bid −1 %/−2 % so với TB 24h trước, bất đối xứng bid/ask ±1 %, tốc độ rút depth 5′ trước.
- Câu hỏi: trong đợt ≥6 lệnh, chân có depth bid còn dày hơn có PnL hold-to-exit tốt hơn? (chọn trong đợt); đợt có depth toàn rổ cạn ⇒ PnL đợt tệ hơn? (veto).
- Khám phá 2024 (≤ 6 biến thể, ledger tiếp 50→), báo mono + spread + CI theo đợt (bootstrap theo ngày). Ứng viên ⇒ pre-reg xác nhận 2023 + 2025 (DEV, ghi rõ) rồi HO 2026.
- Kiểm trước: V-a causal; khớp giá mid bookDepth với close kline cùng phút (|Δ| ≤ 0,5 %).

## R3 — parity theo tick cho release v1 (song song)
- Sim `SIM_EXPORT_CANDIDATES` trên Vision daily 2026-10-15→10-22 (bundle exporter HO4) ⇒ so log c3b từng phút: p15, q_t, thr, top-K S1, n_pass. Pre-reg ngưỡng trong addendum PREREG_SHADOW2_PROMOTION trước khi so.

## Không làm
C (trần đợt) = trục K đã đo (K16 vs K24) ⇒ quyết định khẩu vị của owner. E2 trên sự kiện thô. C1-AGE.
