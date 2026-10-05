# PREREG_SHADOW2_PROMOTION — tiêu chí đưa K24 + GATE_QUOTA_SKIP_WHEN_FULL từ shadow #2 lên 242

- **Ngày:** 2026-10-05. **Trạng thái:** ĐỀ XUẤT — **chờ MASTER duyệt**. Commit TRƯỚC khi shadow #2 chạy; không sửa ngưỡng sau khi thấy số forward.
- **Đối tượng:** shadow #2 (`~/shadow_c3b`, K24 + skipFull, paper) so với shadow #1 (`~/shadow_c3`, B0 K16, paper) — cùng jar-logic (skipFull OFF ≙ byte-identical), cùng env trừ 2 key (`docs/runbooks/SHADOW2_K24_SKIPFULL_PLAN.md` §3).
- **Nguyên tắc:** forward 4–12 tuần **không đủ power** cho PnL (sim K24 vs K16: ΔCAGR22 ≈ +4 pp/năm ⇒ ~0,3 pp/4 tuần, nhỏ hơn nhiều so với nhiễu tuần). ⇒ tiêu chí là **VẬN HÀNH + PARITY CƠ CHẾ**, không có ngưỡng PnL. PnL (MTM ngày, theo tuần) chỉ báo cáo.
- **Số sim tham chiếu:** `docs/prereg/shadow2_weekly_ratio.json` (script `research/analysis/shadow2_weekly_ratio.py`, 0 sim, chỉ đọc printDone Kaggle có sẵn). Cặp cùng seed model: `gqsf-{a1,s21,s7}` (K24 ON) vs `gqsf16-{a1,s21,s7}` (K16, = OFF byte-identical); kỳ 2022-01-03…2025-12-28, 208 tuần × 3 cặp. Tự kiểm: tổng A1 K24 2944 lệnh = 736/năm, K16 2083 = 521/năm — khớp bảng C2/C0 `GATE_SKIPFULL_DETAIL_20261005.md` §4.

## Cửa sổ đánh giá

Bắt đầu khi #2 qua kiểm 60' **và** buffer gate armed ở cả hai shadow. Tối thiểu **4 tuần (28 ngày)**. Nếu tới 4 tuần mà shadow #1 có < 10 leg0 PREDICT trong cửa sổ ⇒ gia hạn từng khối 4 tuần, tối đa 12 tuần (sim: 41/156 khối 4 tuần có K16 < 10 leg0; 28/156 khối = 0 lệnh; trung vị tuần = 0 lệnh, 389/624 tuần K16 không có leg0). Quá 12 tuần vẫn < 10 ⇒ (ii) = KHÔNG KẾT LUẬN ⇒ báo MASTER, không promote.

## Tiêu chí (tất cả phải ĐẠT)

**(i) Vận hành.** Suốt cửa sổ: 0 crash (systemd `NRestarts` không tăng do lỗi; restart có chủ đích phải ghi log vận hành), 0 `OutOfMemoryError`, RSS java ≤ 4,3G; 0 ghi Aerospike 242 (banner `[NO-WRITE-242] … BI TAT` mỗi lần khởi động, và không có dòng ghi 242 nào ngoài thông báo "bo qua ghi"); shadow #1 không bị ảnh hưởng (không file chung, NRestarts #1 không tăng do #2); `[GATE] topk=24` có mặt ≥ 95% số phút #2 chạy.

**(ii) Tần suất lệnh #2/#1 trong dải sim.** Tỉ lệ cộng dồn cả cửa sổ R = (số leg0 PREDICT_SYMBOL_TRADE #2) / (số leg0 PREDICT #1). Sim, khối 4 tuần không chồng có K16 ≥ 10 leg0 (n = 115, 3 cặp):
| phân vị | p5 | p10 | p50 | p90 | p95 | min/max (mọi khối K16>0) |
| --- | --- | --- | --- | --- | --- | --- |
| R leg0 | 1,307 | 1,335 | 1,500 | 1,608 | 1,667 | 1,0 / 2,0 |
| R mọi leg (tham khảo) | 1,279 | 1,311 | 1,450 | 1,561 | 1,623 | 1,0 / 2,0 |
Tổng 4 năm theo cặp (leg0): 1,465 / 1,467 / 1,480. Theo năm (p10–p90 khối 4 tuần, leg0, mọi khối K16>0): 2022 1,31–1,67; 2023 1,39–1,60; 2024 1,31–1,57; 2025 1,30–1,67.
- **ĐẠT:** R ∈ [1,31; 1,67] (p5–p95). **XÁM:** R ∈ [1,00; 1,31) ∪ (1,67; 2,00] ⇒ gia hạn 4 tuần + điều tra (buffer gate G1 kéo R xuống — plan §4; sổ giấy #2 phân kỳ U). **TRƯỢT:** R < 1,00 hoặc R > 2,00 (ngoài mọi khối sim) ⇒ dừng, điều tra code/config.
- Dải là dung sai khai trước từ một thước duy nhất (không chọn biến thể sau khi nhìn) ⇒ không nhân inflate √(2 ln k) (k = 1).

**(iii) Sizing đúng công thức (E2/E5 PASS) trên #2.** Theo `docs/audit/LIVE_SIZING_DCA_C3LIVE_20261003.md`: E2 — budget leg = `managerBudget(equity, U) × gridLegWeightRatio(legIdx)` (leg0 @ equity 35000, U=0: **787,5**, không phải 131,25); E5 — DCA leg 1–3 tại −50/−75/−90% giá leg0, `leg_idx` ghi đúng trong `legs.csv`. Đo bằng `live_vs_sim_check.py --probe` (probe L) + đối chiếu từng leg trong cửa sổ: **100% leg** sai lệch tương đối ≤ 1e-3 so với công thức tính lại từ equity/U tại thời điểm vào. Bất kỳ leg sai ⇒ TRƯỢT.

**(iv) skipFull nhất quán điều kiện U ≥ U_MAX.** Mọi sự kiện skipFull phải xảy ra khi U = margin/equity sổ giấy #2 ≥ 0,60 (`U_MAX`), và không có tick nào U ≥ 0,60 mà ứng viên PREDICT lại vào `threshold`/PASS. Sim: skipFull/run 4 năm = 0–942 (trung bình 214, 8 seed; S777 = 0, A1/S99 = 14), dồn ở 2022 (sổ đầy mùa giảm) ⇒ kỳ vọng **0 trong phần lớn cửa sổ 4 tuần**; tiêu chí là **nhất quán**, không phải số đếm. Đếm cần log: live hiện **không có log skipFull riêng** (plan §1b, C2) ⇒ hoặc MASTER cho thêm log Java (pre-reg byte-identical OFF) trước khi chạy, hoặc đo proxy: U theo phút từ ledger/state #2 vs dòng `[GATE]` (`n_rej = n_cand` khi U ≥ 0,60; có ≥1 PASS khi U ≥ 0,60 ⇒ TRƯỢT; proxy theo phút nên loại các phút |U − 0,60| < 0,01 do giá trôi trong phút). Nếu U < 0,60 suốt cửa sổ ⇒ (iv) = "chưa quan sát", **không chặn** (i)–(iii) nhưng ghi rõ: cơ chế skipFull chưa được kiểm forward.

**(v) Real-book adapter (CHẶN CỨNG).** Trên 242, `liveBookFull()` (`DetectEntrySignal2TradeNormal.java:920-933`) và sizing đi nhánh **BudgetManager** (tài khoản thật), không phải ShadowBookC3. Chưa được promote cho tới khi adapter sổ thật hoàn tất và có kiểm chứng riêng rằng `marginRunning/balanceBasic` của BudgetManager trên 242 cùng ngữ nghĩa (margin đang mở / equity MTM) với sổ giấy + sim, kèm test. Shadow #2 đạt (i)–(iv) **không** thay thế điều kiện này.

## PnL — chỉ báo cáo, không ngưỡng
Báo theo tuần + theo ngày (MTM ngày, ghép cặp #2 − #1): ΣPnL, equity MTM, maxDD, số lệnh, win%, SL%, U trung bình/max, số phút U ≥ 0,60. Tham chiếu sim K24+ON (8 seed): CAGR22 37,0 (35,6–39,3), Calmar 1,65, maxDD −22,6, UW 116, ~740 lệnh/năm; K16: 32,8 / 1,74 / −18,9 / 94 / ~520. Lệch xấu bao nhiêu cũng **không** tự thành TRƯỢT; MASTER/owner xem xét riêng (rủi ro theo `docs/RISK_APPETITE.md` §9: maxDD K24 sâu hơn ~3,7 pp, UW dài hơn ~22 ngày; owner duyệt K24+skipFull 10-05 trên cơ sở các số này).

## Quy trình ra quyết định
1. Hết cửa sổ: agent chạy đo (i)–(iv), ghi `docs/result/RESULT_SHADOW2_PROMOTION_<ngày>.md` + json, không đổi ngưỡng.
2. Tất cả ĐẠT + (v) xong ⇒ đề xuất MASTER/owner; triển khai 242 theo runbook riêng (không thuộc prereg này).
3. Bất kỳ TRƯỢT ⇒ dừng đường promote; XÁM ⇒ gia hạn đúng 1 lần/khối 4 tuần, tối đa 12 tuần.

**Chờ MASTER duyệt.**
