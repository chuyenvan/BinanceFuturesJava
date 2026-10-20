# T_OOS — kiểm ngoài mẫu bộ lọc T (BTC sleeve) trên 2018–2019 (kết quả)

Ngày 2026-10-20. Pre-reg `docs/prereg/PREREG_T_OOS.md` commit **27d33a1e** (cùng mã `docs/result/t_oos/{t_oos.py, t_oos_data.py}`, commit trước khi tải dữ liệu 2018–2019; không đổi tham số/tiêu chí sau đó).
Script `docs/result/t_oos/{t_oos_data.py, t_oos.py, t_oos_tab.py}`, JSON `t_oos_res.json`, `data_report.json`, bảng đầy đủ `t_oos_tab.md`, log `t_oos_run.log`, dữ liệu sạch `btcusdt_1d_clean.csv`.
0 Binance REST (chỉ file tĩnh Vision), 0 dữ liệu 2020, 0 đụng 242, 0 push.

## 0. Verdict theo prereg: **PASS (không bị bác bỏ)** — yếu, không phải bằng chứng

| tiêu chí | ngưỡng | đo | kết |
|---|---|---|---|
| C1 | \|DD_T\| ≤ 0,6 × \|DD_B&H\| | 35,3 % vs 81,2 % → tỷ lệ 0,435 | ĐẠT |
| C2 | LN_T ≥ LN_B&H | +75,4 % vs −47,6 % | ĐẠT |
| C3 | \|DD_T\| ≤ 40 % | 35,3 % (biên 4,7pp) | ĐẠT |
| Phụ (lưới) | ≥ 19/27 ô đạt C1∧C2 | **21/27** (biên 2 ô) | ĐẠT |

Hạn chế đã ghi trước và vẫn đúng: n sự kiện nhỏ. Kết quả phụ thuộc gần như hoàn toàn vào **một** đợt ON (2019-04-01→2019-09-24, +104,3 %) cộng với việc đứng ngoài gần hết 2018.
Mô tả (hậu kiểm, không tham gia verdict): 17 đợt ON còn lại nhân lại ≈ 1,754/2,043 = 0,858 (−14,2 %); DEV tương tự (đợt lớn nhất +381 %, 19 đợt còn lại ≈ −26,7 %). 15/18 đợt OOS kéo dài ≤ 2 ngày.

## 1. Bảng chính (cửa sổ 2018-01-01→2019-12-31, mốc t0 = close 2017-12-31, phí 0,15 %/chiều, OFF giữ USDT lãi 0)

| | tổng LN | CAGR | maxDD | đỉnh → đáy (close ngày) | số lần đổi | ngày OFF |
|---|---|---|---|---|---|---|
| T | +75,4 % | +32,4 % | −35,3 % | 2019-06-26 → 2019-10-25 | 35 | 523 / 731 |
| B&H | −47,6 % | −27,6 % | −81,2 % | 2018-01-06 → 2018-12-15 | – | – |

Đợt ON (net phí): 18 đợt, 6 thắng; min −9,4 %, median −0,6 %, max +104,3 %.

| # | vào | ra | LN | # | vào | ra | LN |
|---|---|---|---|---|---|---|---|
| 1 | 2017-12-31 | 2018-01-11 | −3,8 % | 10 | 2018-09-04 | 2018-09-05 | −9,2 % |
| 2 | 2018-03-03 | 2018-03-04 | +0,1 % | 11 | 2018-10-16 | 2018-10-17 | −0,6 % |
| 3 | 2018-04-21 | 2018-04-22 | −1,7 % | 12 | 2019-02-10 | 2019-02-11 | −1,6 % |
| 4 | 2018-04-23 | 2018-04-24 | +7,4 % | 13 | 2019-02-18 | 2019-02-19 | −0,1 % |
| 5 | 2018-05-03 | 2018-05-04 | −0,7 % | 14 | 2019-02-20 | 2019-02-21 | −1,1 % |
| 6 | 2018-05-05 | 2018-05-06 | −2,4 % | 15 | 2019-02-23 | 2019-02-24 | −9,4 % |
| 7 | 2018-07-17 | 2018-07-18 | +0,6 % | 16 | 2019-03-29 | 2019-03-30 | −0,2 % |
| 8 | 2018-07-19 | 2018-07-20 | −2,0 % | 17 | 2019-04-01 | 2019-09-24 | **+104,3 %** |
| 9 | 2018-07-23 | 2018-07-25 | +5,6 % | 18 | 2019-10-25 | 2019-10-30 | +5,5 % |

Ngày đổi trạng thái kèm giá (close UTC, spot BTCUSDT): xem `t_oos_tab.md` (36 dòng). Các mốc chính: BUY 2017-12-31 @13716,36 · SELL 2018-01-11 @13238,78 · BUY 2019-04-01 @4144,56 · SELL 2019-09-24 @8493,14 · BUY 2019-10-25 @8655,02 · SELL 2019-10-30 @9154,72.
Cơ chế whipsaw: khi giá còn ≤ 70 % đỉnh 180d, mỗi lần close vượt max 30 ngày kích ON rồi ngày sau lại OFF (cặp BUY/SELL liền nhau, chi phí 0,3 %/vòng + trượt giá ngày).

## 2. Lưới 27 ô (ô: LN T / DD T · C1C2C3 · số lần đổi; B&H −47,6 % / −81,2 %)

21/27 ô đạt C1∧C2 (C1 21, C2 27, C3 15 — C3 theo ô chỉ báo cáo). Ô không đạt đều ở thr 0,65 hoặc P = 120.

thr 0,65 | R=20 | R=30 | R=40
---|---|---|---
P=120 | −19,3 / −65,7 · xĐx · 31 | −26,1 / −67,3 · xĐx · 27 | −9,1 / −64,2 · xĐx · 17
P=180 | +13,4 / −54,4 · xĐx · 45 | +8,9 / −56,1 · xĐx · 35 | +38,7 / −45,5 · ĐĐx · 17
P=240 | +41,7 / −43,0 · ĐĐx · 47 | +37,2 / −44,7 · ĐĐx · 35 | +66,8 / −36,3 · ĐĐĐ · 17

thr 0,70 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +31,8 / −47,8 · ĐĐx · 31 | +20,7 / −50,2 · xĐx · 27 | +38,4 / −45,6 · ĐĐx · 17
P=180 | +83,0 / −35,3 · ĐĐĐ · 45 | **+75,4 / −35,3 · ĐĐĐ · 35** (T) | +97,2 / −35,2 · ĐĐĐ · 17
P=240 | +56,5 / −35,3 · ĐĐĐ · 57 | +51,6 / −35,3 · ĐĐĐ · 45 | +70,5 / −35,2 · ĐĐĐ · 27

thr 0,75 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +40,9 / −40,0 · ĐĐĐ · 45 | +50,0 / −41,8 · ĐĐx · 35 | +71,6 / −33,3 · ĐĐĐ · 17
P=180 | +60,9 / −36,3 · ĐĐĐ · 59 | +75,8 / −28,1 · ĐĐĐ · 45 | +103,6 / −28,0 · ĐĐĐ · 25
P=240 | +50,2 / −36,3 · ĐĐĐ · 63 | +64,0 / −28,1 · ĐĐĐ · 49 | +90,0 / −28,0 · ĐĐĐ · 29

(Đ = đạt, x = trượt.) Lưới không dùng để chọn tham số. Nhận xét: P = 120 (đỉnh ngắn) làm T tệ rõ → độ nhạy theo P; R lớn hơn (40) cho ít whipsaw hơn ở mọi hàng, nhưng không được chọn lại.

## 3. Báo cáo phụ (không tham gia verdict; cùng chiều verdict)

| | T | B&H | C1/C2/C3 |
|---|---|---|---|
| (a) từ 2018-02-14 (rebase từ đường primary tại close 2018-02-13; T đang OFF) | +82,2 % · CAGR +37,6 % · DD −35,3 % | −15,7 % · CAGR −8,7 % · DD −72,1 % | ĐẠT / ĐẠT / ĐẠT |
| (b) warm-start liên tục từ 2017-08-17 (3 lần đổi trước t0, tại t0 trạng thái OFF) | +82,2 % · CAGR +35,0 % · DD −35,3 % · 34 đổi · 534 ngày OFF | −47,6 % / −81,2 % | ĐẠT / ĐẠT / ĐẠT |

Khác biệt primary vs warm-start chỉ là đợt #1 (BUY 2017-12-31 → SELL 2018-01-11, −3,8 %): cold-start ON tại t0 sát đỉnh 12/2017 là artefact của quy ước "khởi tạo ON" (giữ đúng gốc bb_core).

## 4. Nhất quán với DEV (sleeve BTC đứng riêng, 2021-06-30→2025-12-30, giá USDT-M perp từ `px_btceth.npz`, cùng phí 0,15 %/chiều)

| | tổng LN | CAGR | maxDD | đỉnh → đáy | số lần đổi | ngày OFF | đợt ON thắng |
|---|---|---|---|---|---|---|---|
| T DEV | +252,8 % | +32,3 % | −33,9 % | 2021-09-06 → 2023-01-11 | 41 | 475 / 1645 | 7/20 (median −0,4 %, max +381 %) |
| B&H DEV | +152,1 % | +22,8 % | −76,7 % | 2021-11-08 → 2022-11-21 | – | – | – |
| T OOS | +75,4 % | +32,4 % | −35,3 % | 2019-06-26 → 2019-10-25 | 35 | 523 / 731 | 6/18 (median −0,6 %, max +104 %) |
| B&H OOS | −47,6 % | −27,6 % | −81,2 % | 2018-01-06 → 2018-12-15 | – | – | – |

Cùng một hồ sơ: DD ≈ −34/−35 % cho T (vs −77/−81 % B&H), tỷ lệ DD ≈ 0,44 trên cả hai; CAGR T ≈ 32 % cả hai; ~1/3 đợt ON thắng, lợi nhuận tập trung ở 1 đợt dài; whipsaw 1–2 ngày rất nhiều.
Lưu ý: DEV dùng perp, OOS dùng spot; số DEV này là sleeve đứng riêng nên khác số BTC_BASE (sleeve TWR phút, phí 0,09 %: DD −32,9 %). Cả hai kỳ đều có đúng **một** thị trường gấu lớn và **một** pha hồi phục — OOS bổ sung được 1 bear độc lập (2018) nhưng vẫn chỉ 2 bear/1 tài sản.

## 5. Kiểm vệ sinh

| kiểm | đo | kết |
|---|---|---|
| V1 tái tạo T trên DEV (`bb_core.load_px('D')` + `t_states`) | 475 ngày OFF, 41 lần đổi = đúng BTC_BASE (1645 ngày quyết định 2021-06-30→2025-12-30; lịch sử close ngày từ 2021-01-01) | PASS, 0 sai lệch |
| V2 không dùng 2020 | dữ liệu OOS max 2019-12-31 (assert < 2020-01-01, chỉ tải tháng ≤ 2019-12); DEV `px_btceth.npz` bắt đầu 2021-01-01 | PASS |
| V3 không look-ahead | cắt dữ liệu sau mốc và thay giá sau mốc bằng random walk: state + equity ≤ mốc không đổi; OOS 3 mốc (2018-04-30, 2018-12-31, 2019-06-30), DEV 2 mốc | 5/5 PASS (cả hai kiểu) |
| Dữ liệu | 29 file tháng 2017-08→2019-12, sha256 khớp `.CHECKSUM` 29/29; 867/867 ngày, 0 trùng, 0 thiếu (không phải ffill); open_time đều 00:00 UTC; sha256 CSV sạch `b08921d3…e85f7a` | PASS |
| Ô trung tâm lưới = primary | assert trùng (LN, DD) | PASS |

Quy ước khớp (giống gốc): quyết định + khớp tại close ngày UTC (gốc: close phút 23:59 futures; ở đây close nến 1d spot — cùng mốc thời gian, khác instrument). Đỉnh P gồm ngày hiện tại, max vào lại không gồm.

## 6. Bất thường / lưu ý

1. PASS biên hẹp ở hai chỗ: C3 (35,3 % vs 40 %) và lưới (21 vs ngưỡng 19). DD của T gần như là "giá sàn cơ học" của luật 70 % (cắt −30 % + phí/trượt): đợt 2019-06-26→09-24 giữ ON qua −35 %.
2. Lợi nhuận tập trung vào 1 đợt (+104 %); nếu đợt đó vắng, T OOS ≈ −14 % (mô tả hậu kiểm). B&H −47,6 % làm C2 dễ đạt (đứng ngoài là đủ) — C1/C2 chủ yếu kiểm "né bear", ít kiểm "không bị whipsaw giết trong sideway".
3. Whipsaw cấu trúc: khi giá còn dưới 0,7×đỉnh, mọi close mới > max 30 ngày kích ON rồi OFF ngay hôm sau (cặp 1 ngày) — 15/18 đợt OOS kéo dài ≤ 2 ngày; 12/18 đợt OOS và 13/20 đợt DEV có LN ≤ 0. Tác động nhỏ trong sleeve đứng riêng (phí 0,15 %/chiều) nhưng là rủi ro vận hành/chi phí nếu phí cao hơn hoặc trượt giá lớn hơn tại close.
4. Độ nhạy tham số: vùng yếu là P = 120 (C1 trượt 4/9 ô) và thr 0,65 (C1 trượt 5/9 ô) — luật nhạy với cửa sổ đỉnh ngắn và ngưỡng cắt sâu; ô trung tâm không phải cực trị (thr 0,75 / R 40 cho +103,6 % / −28,0 %), không dùng để chọn lại.
5. Cold-start ON tại t0 sát đỉnh 12/2017 tạo đợt #1 −3,8 % không có trong warm-start; không ảnh hưởng verdict.
6. Chưa kiểm: tương tác với crash-buy (không có sim 2018–2019), khớp lệnh tại close ngày (không có trượt giá thực), thuế/chênh lệch spot-perp. Verdict PASS ⇒ T **không bị bác bỏ** tới đây, KHÔNG phải đủ điều kiện nội tại để tin; quyết định đưa vào v1.1 vẫn là của owner.
