# LIQX_S0 — Bước 0: proxy thanh lý Vision vs thanh lý thật (Tardis ngày-01 + collector)

Prereg `docs/prereg/PREREG_LIQX_S0.md` (commit 28a66248, sha256 b8e4afbf…eadd8). Code `research/liqx_s0/`. Artefact `docs/result/liqx_s0/`. Agent liqx0, 2026-10-24.
Chỉ validate đo lường — không PnL, không đụng X14.

## VERDICT
- **Run 1 (đúng chữ prereg, OI = hàng create_time T): NO-GO** — không proxy nào đạt ở B (M1 B ≤ 0,075, M3 B ≤ 0,62, M4 đỉnh +5′).
- **ADDENDUM (sửa bug ngữ nghĩa create_time, xem §2): P2 ĐẠT mọi tiêu chí ở A và B** ⇒ ỨNG VIÊN sang Bước 1 (MASTER quyết vì sửa sau khi thấy kết quả). P1 trượt sát M3 ở B (0,794); P3 trượt M1/M3.
- Biên mỏng: P2 M3 = 0,817 | 0,813 (ngưỡng 0,80); M1 = 0,456 | 0,473 (ngưỡng 0,40).

## 1. Bảng chính (sau ADDENDUM; run 1 trong ngoặc cho B/F)
| proxy | mẫu | M1 | M3 (AUC/symbol, w=n_pos) | M3 gộp | M4 đỉnh | M6 | M6 trên tập M1 | Σproxy/ΣLIQ | M1 trong-symbol |
|---|---|---|---|---|---|---|---|---|---|
| P1 | A | 0,413 | 0,816 | 0,799 | 0′ | −0,468 | 0,181 | 320 | 0,295 |
| P1 | B | 0,403 (0,036) | **0,794** (0,598) | 0,772 | 0′ (+5′) | −0,497 | 0,247 | 157 | 0,274 |
| **P2** | A | **0,456** | **0,817** | 0,804 | 0′ | −0,493 | 0,128 | 228 | 0,360 |
| **P2** | B | **0,473** (0,075) | **0,813** (0,612) | 0,797 | 0′ (+5′) | −0,554 | 0,173 | 95 | 0,418 |
| P3 | A | 0,385 | 0,792 | 0,783 | 0′ | −0,567 | 0,016 | 61 | 0,273 |
| P3 | B | 0,342 (0,046) | 0,783 (0,612) | 0,771 | 0′ (+5′) | −0,618 | 0,036 | 32 | 0,251 |
| P2 | F (mô tả) | 0,437 (0,043) | 0,784 (0,605) | 0,759 | 0′ (+5′) | −0,498 | 0,072 | 32 | 0,383 |
| P1 | F | 0,271 | 0,777 | 0,738 | 0′ | −0,420 | 0,069 | 61 | 0,307 |
| P3 | F | 0,245 | 0,761 | 0,744 | 0′ | −0,554 | −0,098 | 13 | 0,194 |

n: A 675 608 bucket hợp lệ / 2 347 symbol-ngày, tập M1 4 983, dương M3 6 835 (214 symbol luật p99, 6 symbol luật 1 M USD); B 688 872 / 2 393, M1 9 663, dương 7 047 (439 p99); F 201 400 / 700, M1 1 923.
Baseline chẩn đoán trên tập M1 (không chấm): Spearman(OI USD mức, LIQ) A 0,391 | B 0,304 | F 0,219; Spearman(−r5, LIQ) A 0,272 | B 0,342 | F 0,255. ⇒ P2 vượt baseline "chỉ kích thước" và "chỉ giá" nhưng ở A chỉ hơn ~0,07.
M1 theo năm (sau fix): P2 2022 0,497 | 2023 0,413 | 2024 0,542 | 2025 0,470; P1 0,464 | 0,344 | 0,427 | 0,407.
M5 (OLS log1p theo tier, tập M2): b âm (−0,15…−0,28), R² 0,05–0,11 mọi proxy/tier — KHÔNG có nghĩa đàn hồi: tập "proxy>0 hoặc LIQ>0" là hợp của hai biến zero-inflated ⇒ tương quan âm cấu trúc (M2 ≈ 0 hoặc âm cũng vì vậy). M2/M5 và giá trị tuyệt đối M4/M6 (cùng tập hợp) không dùng để kết luận; argmax M4 vẫn đọc được. Chẩn đoán lag trên MỌI bucket (post-hoc, không chấm): P2 k=0 0,214 | 0,289 cao nhất, k=+5′ 0,154 | 0,188, k<0 ≈ 0.
V4 (đơn vị): P1 theo HỢP ĐỒNG M1 0,133 | 0,096, M3 0,722 | 0,702 ⇒ USD đúng, hợp đồng làm hỏng xếp hạng liên symbol (như audit LIQ_PROXY).
Run 1 đủ số: `scores.json`; sau fix: `scores_fix.json`.

## 2. ADDENDUM — create_time của Vision metrics ĐỔI NGỮ NGHĨA ngày 2024-03-04
- Prereg kiểm ngữ nghĩa trên 1 ngày (BTC 2024-01-01: OI hàng T = snapshot tại ~T). Sau run 1, M4 đỉnh +5′ ở B/F ⇒ chạy V5 (đã khai trong prereg) trên thêm ngày.
- Bằng chứng 1 (Tardis derivative_ticker OI, BTC+ETH/SOL, `v5_posthoc.json`, `v5b_switch.json`): 2022-07…2024-03-01: lệch tốt nhất 0…+30 s. 2024-04-01, -05, -06, -07, 2025-01, -08, -12, 2026-10-01 (BTC, zip Vision daily thô): lệch tốt nhất **+300 s** (sai số 1e-5 vs 3–6e-4 ở L=0). SOL 2026-10-01 UNCLEAR.
- Bằng chứng 2 (độc lập Tardis, `posthoc2.json`): giá ngầm oi_value/oi so close kline tại T vs T+5′, BTC mỗi ngày 2024-02…04 + mọi ngày-01: "T" đến **2024-03-03**, "T+5m" từ **2024-03-04** liên tục tới 2025-12.
- Kết luận: từ 2024-03-04, hàng create_time T chứa OI (và oi_value = OI × giá) tại **T+5′** (create_time = đầu kỳ). Sửa: ts hiệu lực = create_time + 5′ cho ngày ≥ 2024-04-01 trong mẫu (2024-03-01 trước switch nên giữ) và cho F. Sau sửa Spearman(ΔOIval%, r5) đỉnh tại k=0 ở cả A (0,750) và B (0,870) — trước sửa B đỉnh tại +5′ (0,767).
- Sửa không dùng thanh lý để chọn (chỉ OI vs Tardis OI/giá kline); proxy, tiêu chí, mẫu không đổi. Run 1 giữ nguyên trong artefact.
- **RỦI RO HỆ THỐNG**: mọi nghiên cứu dùng `~/vz/out/metrics5m` từ 2024-03-04 mà đọc hàng T tại thời điểm T có **look-ahead 5′** (OI và giá). Cần kiểm lại các task đã dùng metrics5m (LIQ_PROXY lag OI 10′ nên ảnh hưởng nhỏ hơn; các task khác chưa rõ). Live: nếu dùng REST openInterestHist cần kiểm cùng ngữ nghĩa.

## 3. Validation
- V1: ts int64 assert mọi bảng; kline 1440 bar/symbol-ngày; metrics không trùng. 4 800 symbol-ngày, 4 694 đủ 288; 106 thiếu: chủ yếu **lỗ dữ liệu kline pack 2022-04-01/02 (~35 symbol F…Z không có bar tới 04-03 00:00)** và 2022-03-01 (34 symbol thiếu ~18 bucket); còn lại symbol mới list/delist (metrics 1–2 hàng). F: 10-20 loại 200 bucket (khoảng trống collector 308 s từ 08:59:07); 10-22 bản run 1 thiếu bucket 24:00 (không có metrics 10-23) — bản fix đủ.
- V2: tái lập độc lập M1(P1, A) — xem `v2.json` (§5).
- V3: 5 bucket LIQ_long lớn nhất (A∪B) đọc thẳng file thô: 5/5 khớp (OI, close, taker Δ≤1e-9; LIQ Δ≤1e-6) — `v3_manual.json`. Cả 5 đều 2025 (SOL 08-01 00:55 3,76 M; BTC 08-01 13:55 3,18 M; SOL 08-01 00:15 3,06 M; ETH 12-01 00:55 2,74 M; BTC 12-01 00:30 2,60 M) và 4/5 có **OI USD TĂNG** trong 5′ dù thanh lý long 2,6–3,8 M ⇒ OI ròng không bắt được cascade khi bên mua là lệnh mở mới.
- V4: §1. V5: §2.
- Đối chiếu F: close Vision 1m = close collector kline 100 % (98–144 k cặp/ngày).

## 4. Dữ liệu, đếm thiếu, ngày-01 có biến động
- Tardis `PERPETUALS` ngày-01 2022-01…2025-12: 48 file, **29 MB**, giữ ở `~/claude_master/liqx_wk/tardis/`. Snapshot ≤1 lệnh/symbol/giây xác nhận (max 1/symbol-giây) ⇒ LIQ thật là cận dưới, thiếu nặng nhất đúng lúc cascade (Σproxy/ΣLIQ 30–320× một phần do đó, phần lớn do OI đóng tự nguyện).
- Tardis `price` = "as provided by exchange" — không rõ `p` hay `ap`; notional sai ±~1 % (không ảnh hưởng xếp hạng).
- Ngày-01 đáng kể (BTC ngày | min r5 BTC | LIQ_long top-100): 2022-06-01 −6,5 % | −1,34 % | 16,4 M; 2022-07-01 −3,3 % | −1,48 % | 7,1 M; 2023-05-01 −4,1 % | −1,60 % | 7,3 M; 2024-04-01 −2,4 % | 19,4 M; 2024-05-01 −3,9 % | −1,50 % | 15,1 M; 2024-09-01 −2,9 % | 12,6 M; 2024-10-01 −4,1 % | 31,0 M (SOL 1,55 M/5′); 2025-02-01 −1,75 % | 28,6 M; 2025-07-01 −1,4 % | 42,2 M; 2025-08-01 −2,1 % | **134,7 M** (SOL 3,76 M/5′); 2025-09-01 +0,9 % | 85,3 M; 2025-12-01 −4,6 % | **101,0 M**. KHÔNG có ngày-01 nào là cascade lớn kiểu 2022-05-12 / 2024-08-05 / 2025-10-10 (BTC min r5 > −1,6 %) ⇒ M3 "thanh lý lớn" là p99 per symbol của ngày thường, chưa phải cascade thật. Bảng đủ: `crash_days_AB.csv`, `crash_days_F.csv`.

## 5. V2
- Run 1 của V2: TRƯỢT (n 4 979 vs 4 983, Δ 1,4e-4) — lỗi nằm ở CHÍNH script V2: cửa sổ universe [D−30 ngày, D) với D = 2022-03-01 bắt đầu 2022-01-30 nhưng V2 chỉ đọc tháng trước + tháng hiện tại ⇒ universe khác 4 bucket (chỉ 2022-03-01 lệch; pipeline dùng daily_qv đủ tháng). Kiểm: 4 bucket thừa đều thoả điều kiện hợp lệ của V2 (`probe/dbg2`). Lưu `v2_run1.json`.
- Run 2 của V2 (đọc 3 tháng, groupby pyarrow, rank tự cài): **M1(P1, A) = 0,4125905151925842 vs pipeline 0,41259051519258433, |Δ| = 1,1e-16, n 4 983 = 4 983 ⇒ ĐẠT** (`v2.json`). A không bị ảnh hưởng bởi ADDENDUM (trước switch).

## 6. Lệch thiết kế (đã khai trong prereg) + bổ sung
- Cửa sổ [T−5′, T); F dùng Vision daily klines 1m + metrics daily (collector kline thiếu taker); universe F = top-100 quote volume 2026-09 (Vision monthly 1d); F = 10-16…10-22, loại khoảng trống >180 s.
- M3 per-symbol trọng số n_pos; M6 trên tập proxy>0 ∨ LIQ_short>0.
- Bổ sung sau khi thấy kết quả: ADDENDUM §2 (sửa bug ngữ nghĩa, khai đủ trước/sau); chẩn đoán post-hoc (lag mọi bucket, M1 theo năm, switch date) — không đổi verdict logic.
- Tải thêm (nhỏ): Tardis derivative_ticker BTC/ETH/SOL 13 ngày (~40 MB, đã xoá), Vision fwd ~60 MB (đã xoá).

## 7. Rủi ro / nghi ngờ của agent
1. Verdict ĐẠT phụ thuộc ADDENDUM sau khi thấy kết quả — bằng chứng sửa độc lập với thanh lý (2 phương pháp), nhưng MASTER nên xác nhận.
2. Biên M3 mỏng (0,813–0,817); P1 chỉ trượt 0,006 ⇒ P2 > P1 không chắc chắn về thống kê (chưa bootstrap).
3. Pseudo-replication: bucket cùng symbol-ngày tương quan; n hiệu dụng nhỏ hơn nhiều; 48 ngày, không có cascade cực đoan.
4. Proxy bắn quá rộng: P2 > 0 ở ~35 % mọi bucket; chỉ có nghĩa khi kèm điều kiện giá rơi.
5. M2/M5 vô nghĩa do tập hợp zero-inflated (lỗi thiết kế tập con — M4/M6 tập con là do agent chọn trong prereg).
6. Lỗ dữ liệu kline pack 2022-04-01/02 và 2022-03-01 — ảnh hưởng mọi task dùng `~/vz_e1/raw` (CHƯA GIẢI THÍCH nguồn gốc).
