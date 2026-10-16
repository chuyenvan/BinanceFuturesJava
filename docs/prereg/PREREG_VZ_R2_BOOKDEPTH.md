# PRE-REG (khám phá) — R2 bookDepth tại tick vào đợt (MASTER 2026-10-16)

Nền: `docs/plan/VZ_NEXT_1016.md` §R2, `docs/result/BURST_RISK_1016.md`. Commit TRƯỚC khi tải dữ liệu / tính outcome. Đây là KHÁM PHÁ (không GO); ứng viên đi tiếp phải có pre-reg xác nhận riêng.

## Dữ liệu
- Chân: sim `gqsf-a1` printDone (K24+skipFull), giữ chân thuộc đợt có ≥ 6 chân cùng phút `start` (giờ GMT+7 ⇒ đổi UTC), năm **2024 (UTC)**. Một seed (A1) — ghi rõ.
- Outcome chân: `ret = pnl / margin` (hold-to-exit, đã gồm phí/funding theo sim). Outcome đợt: Σpnl / Σmargin.
- bookDepth Vision UM daily (`timestamp,percentage,depth,notional`, snapshot ~30 s, tích luỹ trong ±1..5 % quanh giá). Tải đúng symbol × ngày UTC của chân + ngày UTC trước đó.
- t_dec = start + 60 s (đóng nến quyết định). Snapshot dùng = snapshot cuối có timestamp ≤ t_dec (causal). Không có snapshot trong 5′ trước t_dec ⇒ feature NaN.

## Feature (cố định)
- F1 `bid1_rel` = notional(−1 %) tại snapshot / trung vị notional(−1 %) trong 24 h trước t_dec.
- F2 `imb1` = (notional(−1 %) − notional(+1 %)) / (notional(−1 %) + notional(+1 %)).
- F3 `bid5_rel` = như F1 với −5 %.

## Phép thử (4, ledger 50 → 54)
- T1–T3 (chọn trong đợt): với mỗi đợt, Spearman(F_k, ret) giữa các chân; thước = trung bình IC qua đợt (đợt có ≥ 6 chân có feature), CI95 bootstrap theo ngày UTC (block 5 ngày, NREP 2000, seed 20261016). Báo kèm: spread ret nửa trên − nửa dưới theo F_k trong đợt.
- T4 (veto đợt): Spearman(trung vị F1 của đợt, ret đợt) qua các đợt; CI bootstrap theo ngày.
- Ứng viên (để viết pre-reg xác nhận 2023 + 2025 rồi HO 2026) chỉ khi: CI95 không chứa 0 VÀ dấu có cơ chế (F1/F3: bid còn dày ⇒ ret tốt hơn, IC > 0; F2: bid lấn ask ⇒ IC > 0). Ngược dấu ⇒ ghi nhận, không theo đuổi.

## Kiểm dữ liệu (bắt buộc trước khi tính outcome)
- V1 causal: mọi snapshot dùng có timestamp ≤ t_dec.
- V2 khớp giá: mid suy ra = notional(±1 %)/depth(±1 %) bình quân hai phía, so close kline phút quyết định (lake `vz-kline1m-2024`) — |Δ|/close ≤ 1 % ở ≥ 95 % chân.
- V3 phủ: tỉ lệ chân có feature ≥ 80 %; báo symbol thiếu file.
