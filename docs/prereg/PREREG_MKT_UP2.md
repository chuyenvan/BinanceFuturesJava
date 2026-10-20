# PREREG MKT_UP2 — Tầng A (offline): gate dự báo giỏ TOP-K (thanh khoản / selector S1), không phải cả thị trường — 2026-10-20

Bối cảnh: MKT_UP (label = cả rổ ALT_EW) FAIL (9c878b9c). Owner 10-20: selector chọn coin thanh khoản ⇒ label nên theo top-K thanh khoản hoặc top-K của S1 ("gate theo alpha của selector"). Viết TRƯỚC khi tính bất kỳ label/AUC mới nào. HO 2026 KHÔNG dùng (panel có 2026 ⇒ loại mọi dòng ≥ 2026-01-01).

## Dữ liệu (đóng băng)
- `~/claude_master/rex/panel.parquet` (ngày × sym, universe REX thanh khoản ≥ 20M; feature mom*/vol*/lqv30/br50/disp7/mfund/n_univ…; nhãn y3 = return 3 ngày tới). `~/claude_master/rex/pred_s1.parquet` (điểm S1 REX OOS theo ngày, từ 2022-01). Phải kiểm và ghi rõ: feature ngày t chỉ dùng dữ liệu ≤ close t; y3 = close t → close t+3.
- Lưu ý: S1 ở đây là selector REX theo ngày (S1 của K24 chỉ có điểm lúc gate mở nên không dùng được cho mọi ngày) — giả định của MASTER, ghi vào result.

## Giỏ (lập tại ngày t, trọng số đều)
- B1 LIQ30 = 30 coin lqv30 cao nhất trong universe ngày t.
- B2 S1TOP10 = 10 coin điểm S1 cao nhất ngày t.

## Label (3, cố định)
- L1 = mean y3(B1) > 0 · L2 = mean y3(B2) > 0 · L3 (alpha selector) = mean y3(B2) − mean y3(B1) > 0.

## Feature (cố định, 1 dòng/ngày)
18 feature thị trường như MKT_UP (EW/BTC từ `edge_attr/index.npz`, tính tại 00:00 UTC ngày t+1 = sau close t) + 9 feature giỏ: với B1 và B2: TB mom1, mom7, mom28, vol30 (8) + br50 (1). Không thêm/bớt.

## Model & walk-forward
Logistic L2 C=1 + StandardScaler (chính), LightGBM depth3/200/0,05 (mô tả). Refit đầu tháng, expanding, purge 3 ngày. OOS: L1 từ 2022-07; L2/L3 từ 2023-01 (S1 bắt đầu 2022-01). DEV-OOS tới 2024-12; VAL 2025 (1 lần).

## Đánh giá mỗi label
- E1: AUC DEV-OOS > 0,55, AUC > 0,5 ở ≥ 2/3 năm DEV-OOS (L1: 2022H2/2023/2024; L2/L3: 2023/2024 cả 2), VAL 2025 AUC > 0,5.
- E3 (lớp K5 long-only): mỗi ngày P > 0,55 mở 1 lô giữ 3 ngày (trọng số 1/3, tối đa 3 lô): L1 → mua B1; L2, L3 → mua B2. Phí 0,20 % khứ hồi mỗi lô. Đạt nếu Sharpe năm hoá DEV-OOS > 0,5 VÀ > "luôn mở lô" cùng giỏ cùng phí VÀ > cầm BTC VÀ VAL 2025 Sharpe > 0.
- E2 (chỉnh size crash-buy, chỉ L1, L2): như MKT_UP (×0,5 khi P < 0,45; cụm `entry_confirm/ec_a_clusters.parquet`; ngày = ngày UTC của M trừ 1, tức P dự báo từ close hôm trước). Đạt nếu TB > +5 000/seed, ≥ 6/8 seed, ≥ 2/3 năm, VAL dương.
- Label qua tầng A nếu E1 VÀ (E2 hoặc E3). Do thử 3 label, label qua phải có thêm AUC VAL ≥ 0,53. Không label nào qua ⇒ ĐÓNG họ "gate dự báo hướng giỏ".

## Validate
V1 không look-ahead (cắt dữ liệu sau t), V2 y3 đúng cửa sổ (kiểm 10 ngày từ kline), V3 purge, V4 giỏ B1/B2 đúng (in 3 ngày), V5 loại sạch 2026.

## Ước lượng trước (MASTER): P(≥1 label qua) ~15 %. Rủi ro: giỏ thanh khoản tương quan rất cao với ALT_EW (sẽ đo, mô tả); REX S2a (regime long top-20) đã NO-GO; B2 turnover cao.
