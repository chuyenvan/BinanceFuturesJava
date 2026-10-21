# T_OOS2 — kiểm độc lập lần 2 bộ lọc T: BTC Bitstamp 2014–2017 và ETH 2018–2019 / 2021H2–2025 (kết quả)

Ngày 2026-10-21. Pre-reg `docs/prereg/PREREG_T_OOS2.md` commit **acb6e84a** (cùng mã `docs/result/t_oos2/{t_oos2.py, t_oos2_data_btc.py, t_oos2_data_eth.py, t_oos2_synth.py}`, commit trước khi tải dữ liệu 3 kỳ mới; không đổi tham số/tiêu chí/mã logic sau đó — chỉ thêm `t_oos2_kaggle_dl.py` (tải file, không đọc nội dung) sau commit).
Mã dùng lại ĐÚNG `docs/result/t_oos/t_oos.py` (sha256 d36af813…, assert khi nạp). Script/JSON/log/bảng đầy đủ: `docs/result/t_oos2/` (`t_oos2_res.json`, `t_oos2_tab.md` = Phụ lục bên dưới, `t_oos2_run.log`, `btc_data_report.json`, `eth_data_report.json`, CSV close ngày sạch + QA).
0 Binance REST (chỉ file tĩnh Vision + Kaggle API), 0 dữ liệu 2020, 0 đụng 242, 0 push.

## 0. Verdict theo prereg

| kỳ | vai trò | C1 | C2 | C3 | lưới (≥19/27 C1∧C2) | **verdict** |
|---|---|---|---|---|---|---|
| **A** BTC Bitstamp 2014-01-01→2017-07-31 | phép thử chính BTC | ĐẠT (0,511) | ĐẠT (+397,5 % vs +289,6 %) | **TRƯỢT** (−41,6 % vs ngưỡng −40 %) | **12/27 TRƯỢT** | **FAIL** |
| **B1** ETHUSDT 2018-01-01→2019-12-31 | tổng quát hoá | ĐẠT (0,429) | ĐẠT (+63,5 % vs −82,4 %) | **TRƯỢT** (−40,3 %) | 26/27 ĐẠT | **FAIL** |
| **B2** ETHUSDT 2021-07-01→2025-12-31 | tổng quát hoá | TRƯỢT (0,666) | TRƯỢT (+29,5 % vs +30,4 %) | TRƯỢT (−52,8 %) | 0/27 TRƯỢT | **FAIL** |

- **(A) FAIL ⇒ T bị bác bỏ trên BTC 2014–2017**: không còn được mô tả là "không bị bác bỏ lần 2". Hai điều kiện trượt độc lập: C3 trượt 1,6pp; lưới trượt xa (12 vs ngưỡng 19). Không có tiêu chí cứu (prereg §4–5).
- **(B) ETH: FAIL cả 2 kỳ ⇒ "T không tổng quát sang ETH"** (đúng câu prereg §5). B1 chỉ trượt C3 với biên 0,3pp (40,3 % vs 40 %), các tiêu chí khác đạt (C1 0,429, C2, lưới 26/27); B2 trượt mọi tiêu chí. Verdict không đổi theo biên.
- Hệ quả cho T_OOS (PASS yếu 2018–2019 BTC): V1 tái lập đúng; T_OOS2 không xác nhận lần 2 — T đã qua 1 lần kiểm yếu (BTC 2018–19) và trượt cả 3 kỳ của T_OOS2 (1 BTC, 2 ETH). Quyết định đưa/không đưa T vào v1.1 thuộc MASTER/owner; prereg T_OOS đã ghi "FAIL ⇒ T không vào v1.1" cho kỳ 2018–2019 và T_OOS2 không có tiêu chí cứu.

## 1. Bảng chính từng kỳ (t0 = close ngày trước kỳ; phí 0,15 %/chiều; OFF = tiền mặt lãi 0)

| | tổng LN | CAGR | maxDD | đỉnh → đáy (close ngày) | số lần đổi | ngày OFF |
|---|---|---|---|---|---|---|
| **A** T | +397,5 % | +56,5 % | −41,6 % | 2017-06-11 → 2017-07-26 | 28 | 594 / 1309 |
| **A** B&H | +289,6 % | +46,2 % | −81,4 % | 2014-01-06 → 2015-01-14 | – | – |
| **B1** T | +63,5 % | +27,9 % | −40,3 % | 2018-01-13 → 2019-04-25 | 33 | 583 / 731 |
| **B1** B&H | −82,4 % | −58,1 % | −94,0 % | 2018-01-13 → 2018-12-15 | – | – |
| **B2** T | +29,5 % | +5,9 % | −52,8 % | 2021-09-05 → 2022-08-10 | 69 | 702 / 1646 |
| **B2** B&H | +30,4 % | +6,1 % | −79,3 % | 2021-11-08 → 2022-06-18 | – | – |

Đợt ON (net phí cả hai chiều; "còn lại nhân lại" = tích (1+LN_i) của mọi đợt trừ đợt LN lớn nhất, trừ 1):

| | số đợt | thắng | đợt lớn nhất | tỷ phần log-LN | LN các đợt còn lại nhân lại | median / min | đợt ≤ 2 ngày |
|---|---|---|---|---|---|---|---|
| A | 14 | 7 | +214,8 % (2015-10-06→2017-01-11) | 71 % | **+58,0 %** (13 đợt) | −0,0 % / −16,4 % | 10 |
| B1 | 17 | 10 | +36,7 % (2019-04-05→2019-07-14) | 64 % | **+19,6 %** (16 đợt) | +0,6 % / −16,5 % | 15 |
| B2 | 34 | 12 | +100,7 % (2023-01-10→2024-08-04) | 269 % (các đợt khác âm) | **−35,5 %** (33 đợt) | −1,7 % / −15,9 % | 27 |

Danh sách đợt ON, danh sách ngày đổi trạng thái kèm giá và bảng 27 ô từng kỳ: Phụ lục (cuối file, = `t_oos2_tab.md`).

## 2. Báo cáo phụ (không tham gia verdict; không đổi verdict)

| | warm-start liên tục từ đầu dữ liệu (C1/C2/C3) | độ nhạy phí 0,30 %/chiều (cả T và B&H) |
|---|---|---|
| A | T +397,5 % / DD −41,6 % / 27 đổi (1 đổi trước t0, tại t0 trạng thái OFF) = primary; Đ/Đ/x | T +377,8 % (CAGR +54,7 %) / DD −41,8 % vs B&H +289,0 % / −81,4 %; C1/C2/C3 = Đ/Đ/x; lưới 10/27 |
| B1 | T +63,5 % / DD −40,3 % / 33 đổi (2 đổi trước t0, tại t0 ON) = primary; Đ/Đ/x | T +55,3 % (+24,6 %) / DD −42,8 % vs B&H −82,5 % / −94,0 %; Đ/Đ/x; lưới 25/27 |
| B2 | T +29,5 % / DD −52,8 % / 68 đổi (1 đổi trước t0, tại t0 OFF) = primary; x/x/x | T +17,0 % (+3,5 %) / DD −54,8 % vs B&H +30,2 % / −79,3 %; x/x/x; lưới 0/27 |

Warm-start trùng primary ở cả 3 kỳ (quyết định tại t0 đã đúng trạng thái): cold-start ON không tạo artefact ở A và B2 (tại t0 quyết định đầu tiên là OFF ngay — đợt BUY khởi tạo không xảy ra); ở B1 đợt #1 (BUY t0 2017-12-31 → SELL 2018-02-02 +25,3 %) có mặt cả trong primary lẫn warm-start. Phí 0,30 %: không có kỳ nào đổi trạng thái PASS/FAIL của C1–C3; số ô lưới đạt giảm (A 12→10, B1 26→25).

## 3. Nhận xét (mô tả hậu kiểm, không tham gia verdict)

1. **DD của T ≈ sàn cơ học của luật 70 %**: A −41,6 %, B1 −40,3 %, B2 −52,8 % so với −35,3 % ở T_OOS BTC. Luật cắt khi close ≤ 70 % đỉnh 180 ngày, cộng gap qua ngưỡng, phí và mua lại trễ. Ở A, DD nằm sát cuối cửa sổ: bán 2017-07-15 @1970,51 (≤ 0,7×đỉnh 2954), mua lại 2017-07-20 @2875,03 (+46 %, close ngày +27 %), rồi giảm tới 2525 ngày 07-26 — một chuỗi whipsaw đúng luật (không tune).
2. **A**: T thắng B&H về LN (+397,5 % vs +289,6 %) và DD (tỷ lệ 0,511 đạt C1) nhưng lợi nhuận dồn vào 1 đợt (+214,8 %, 71 % log-LN) cộng đợt +90,2 % (2017-02-04→2017-07-15); 10/14 đợt ≤ 2 ngày (whipsaw 05–06/2014, 03/2015). Lưới 12/27: nhạy rõ theo thr (thr 0,65 và P = 120 kém cả C1 lẫn C2; thr 0,75 chủ yếu mất C2) — vùng trung tâm nằm ở cạnh vùng trượt C3 (DD −41,6 % ở ô trung tâm và 2 ô khác).
3. **B1**: bear 2018 của ETH sâu hơn BTC (B&H −94 %); T +63,5 % và C1 0,429 rất tốt, chỉ trượt C3 vì biên 0,3pp — cùng kiểu "sàn cơ học" cộng biến động ETH cao. 15/17 đợt ≤ 2 ngày.
4. **B2**: T không tạo giá trị: LN gần ngang B&H (−0,9pp, +29,5 % vs +30,4 %), DD −52,8 % (C1 0,666), 69 lần đổi (34 đợt ON, 27 đợt ≤ 2 ngày); chỉ 1 đợt (+100,7 %) có lãi lớn, 33 đợt còn lại nhân lại −35,5 %. 0/27 ô đạt C1∧C2: lưới không có ô nào cứu. B2 trùng khung thời gian với DEV của chính luật T (BTC_BASE) nên đây lẽ ra là kỳ thuận lợi nhất về mặt thời gian cho luật, vậy mà vẫn FAIL ở ETH.
5. Cả 3 kỳ mới lặp lại hồ sơ của T_OOS/DEV: lợi nhuận dồn vào 1 đợt dài, phần còn lại là chuỗi đợt 1–2 ngày xấp xỉ 0 hoặc âm (A +58 % còn lại, B1 +20 %, B2 −36 %, T_OOS −14 %, DEV −27 %).

## 4. Dữ liệu và kiểm vệ sinh

| nguồn | kiểm | kết |
|---|---|---|
| A: Kaggle `mczielinski/bitcoin-historical-data`, `btcusd_1-min_data.csv` (395 107 785 B, sha256 `81cb6c9d7ffd58b182892650d2e2130f657692bb3d473af35f293333e55e0b38`; Bitstamp BTCUSD 1 phút, tải 2026-10-21) | quét 7 786 222 dòng; **4 629 743 dòng ≥ 2018-01-01 bị bỏ khi quét (không xem/tính/ghi)**; 787 679 dòng < 2013-07-01 bỏ; giữ 2 368 800 dòng 2013-07-01→2017-12-31; 0 NaN Close, 0 trùng ts; 1492/1492 ngày 2013-07-01→2017-07-31, **0 ngày thiếu**; file gốc đã xóa khỏi Oracle (chỉ giữ sha256); bản trích phút (<2018) `btc_bitstamp_1m_2013-07_2017-12.csv.gz` sha256 `e6bcc05d…ed86e`; CSV ngày sạch sha256 `a14a8765…33721` | PASS |
| A: QA (chỉ báo cáo) | bản dataset hiện tại điền đủ 1440 phút/ngày (median 1440 bar/ngày, 0 ngày < 720 bar) ⇒ close ngày = close phút 23:59 UTC (khoảng cách tới 23:59 luôn 1 phút); close 66,34→2954,22; 2 ngày abs(ret) > 30 % (max 40,1 %, 2013-11-18) và 8 ngày > 20 % (11–12/2013, 2015-01-14/15, 2017-07-20; phù hợp các biến cố giá lớn đã biết), nằm trong dữ liệu sạch, không sửa | OK |
| A: xcheck vs Binance BTCUSDT 1d (2017-08-17→2017-12-31, 137 ngày; Bitstamp USD vs Binance USDT) | median \|Δ\| 0,46 % (ngưỡng DỪNG 1 %), p95 2,19 %, max 9,92 %, 4 ngày > 3 % (2017-09-04 +4,3 %, 2017-12-22..24 +5,1/+9,9/+4,9 %: premium Bitstamp USD cuối 2017); trung bình có dấu +0,43 % | PASS (không DỪNG) |
| B: ETHUSDT Vision 1d: 29 tháng 2017-08→2019-12 + 60 tháng 2021-01→2025-12 | sha256 `.CHECKSUM` khớp 89/89 file; open_time đều 00:00 UTC; B1 867/867 ngày (2017-08-17→2019-12-31), B2 1826/1826 ngày (2021-01-01→2025-12-31); 0 trùng, 0 thiếu (không ffill); CSV sạch sha256 seg1 `b2e86675f6f15178362164d2183f9677f112bb606e821abdd4be357be081e134`, seg2 `122f05d5d1e44c6e4d3f600edfa49be48666ac20ccb4d9b15c2d4adc7f7fa17c` | PASS |
| **V1** tái lập T_OOS BTC 2018–2019 (cùng mã, `btcusdt_1d_clean.csv` sha256 b08921d3…) | +75,4 % (0,75376), DD −35,3 %, 35 lần đổi, 523 ngày OFF, 21/27 ô, 18 đợt, 36 giao dịch: khớp từng số với `t_oos_res.json` (assert); `evaluate_cost` @0,15 % = `evaluate`; fee 0,30 % trên V1: T +66,2 % / DD −37,7 %, lưới 20/27 | PASS, 0 sai lệch |
| **V2** không dữ liệu 2020 | assert 0 ngày năm 2020 trong 3 CSV sạch (`load_clean2`) + trong script tải (tháng ETH 2020 bị cấm bằng assert); BTC max < 2018-01-01 (chấm ≤ 2017-07-31); ETH chỉ tháng ≤ 2019-12 và ≥ 2021-01 | PASS |
| **V3** không look-ahead (cắt + random-walk, state + equity ≤ mốc không đổi) | A 2015-06-30, 2016-06-30, 2017-03-31; B1 2018-04-30, 2018-12-31, 2019-06-30; B2 2022-06-30, 2023-12-31, 2025-03-31 — 9/9 mốc, cả hai kiểu | PASS |
| ô trung tâm lưới = primary; tích các đợt = tổng LN T | assert từng kỳ | PASS |

Tự kiểm trước commit prereg (không đụng dữ liệu kỳ mới): `--mode selftest` V1; parser BTC trên dữ liệu tổng hợp; parser ETH trên BTCUSDT 2025-10..11; pipeline `--mode run` trên random-walk. Không sửa mã sau commit prereg (chỉ thêm `t_oos2_kaggle_dl.py`).

## 5. Bất thường / lưu ý

1. Đơn vị/nền tảng khác nhau: A là Bitstamp BTCUSD (không phải USDT/Binance), thanh khoản 2014 mỏng nhưng bản dataset đã điền đủ 1440 phút/ngày (giá điền tiến khi không có giao dịch); close ngày = close phút 23:59 như quy ước của gốc. Phí 0,15 %/chiều giữ nguyên. xcheck 2017 cho thấy premium Bitstamp vs Binance tới +9,9 % ngày 2017-12-23 (ngoài cửa sổ chấm).
2. A FAIL không chỉ ở biên: lưới 12/27 cách ngưỡng 7 ô; C3 trượt 1,6pp. B1 FAIL chỉ do C3 (biên 0,3pp) — vẫn FAIL theo prereg, không có tiêu chí cứu.
3. B2 trùng thời gian với DEV của luật (không độc lập) và warmup ngắn (181 ngày): P = 240 dùng cửa sổ mở rộng đến ~2021-08-28 (ảnh hưởng ghi trước, không đổi kết luận vì 0/27 ô và primary đều FAIL rõ).
4. Kỳ A kết thúc 2017-07-31, ngay trước pha tăng mạnh cuối 2017: không kiểm được hành vi T sau mốc đó (nằm ngoài kỳ prereg; không đụng).
5. n sự kiện nhỏ: mỗi kỳ vài đợt ON quyết định kết quả (A: 2 đợt; B2: 1 đợt); số liệu "đóng góp đợt lớn nhất" ở trên.
6. Dữ liệu thô Kaggle chứa 2020+ đã nằm tạm trên Oracle trong lúc quét (parser nạp từng chunk vào bộ nhớ, bỏ các dòng ≥ 2018-01-01 mà không xem); file đã bị xóa sau khi lưu sha256 — không có cách để dùng lại phần 2020 ngoài tải lại từ Kaggle.

---
# Phụ lục — `t_oos2_tab.md` (bảng tự sinh: đợt ON, ngày đổi trạng thái kèm giá, lưới 27 ô, phụ)

### A_BTC_2014_2017 - BTC (Bitstamp USD), cua so cham 2013-12-31..2017-07-31 (1308 buoc; lich su close truoc t0 = 184 ngay)

| | tong LN | CAGR | maxDD | dinh -> day (close ngay) | so lan doi | ngay OFF |
|---|---|---|---|---|---|---|
| T | +397.5 % | +56.5 % | -41.6 % | 2017-06-11 -> 2017-07-26 | 28 | 594 / 1309 |
| B&H | +289.6 % | +46.2 % | -81.4 % | 2014-01-06 -> 2015-01-14 | - | - |

Tieu chi: C1 |DD_T|<=0,6x|DD_B&H| : 41.6 % vs 81.4 % -> ty le 0.511 -> DAT ; C2 LN_T>=LN_B&H : +397.5 % vs +289.6 % -> DAT ; C3 |DD_T|<=40 % : 41.6 % -> TRUOT ; luoi 12/27 (can >= 19) -> TRUOT ; **verdict FAIL**

Dot ON (net phi): 14 dot, 7 thang, median -0.0 %, min -16.4 %, max +214.8 % (2015-10-06 -> 2017-01-11); 10 dot keo dai <= 2 ngay; LN 13 dot con lai nhan lai +58.0 %; ty phan log-LN cua dot lon nhat 71 %

Dot ON:

| # | vao | ra | LN |
|---|---|---|---|
| 1 | 2014-05-22 | 2014-05-23 | -1.5 % |
| 2 | 2014-05-25 | 2014-05-26 | +1.1 % |
| 3 | 2014-05-30 | 2014-05-31 | +0.8 % |
| 4 | 2014-06-01 | 2014-06-02 | +4.5 % |
| 5 | 2014-06-03 | 2014-06-04 | -4.7 % |
| 6 | 2014-11-12 | 2014-11-13 | -1.6 % |
| 7 | 2015-03-01 | 2015-03-02 | +6.1 % |
| 8 | 2015-03-03 | 2015-03-04 | -3.9 % |
| 9 | 2015-03-09 | 2015-03-10 | +0.7 % |
| 10 | 2015-03-11 | 2015-03-12 | -0.7 % |
| 11 | 2015-06-16 | 2015-08-24 | -16.4 % |
| 12 | 2015-10-06 | 2017-01-11 | +214.8 % |
| 13 | 2017-02-04 | 2017-07-15 | +90.2 % |
| 14 | 2017-07-20 | (mo cuoi ky) | -0.8 % (MTM) |

Ngay doi trang thai (close UTC; dong dau = mua khoi tao tai t0):

| ngay | lenh | gia |
|---|---|---|
| 2014-05-22 | BUY | 529.99 |
| 2014-05-23 | SELL | 523.77 |
| 2014-05-25 | BUY | 573.90 |
| 2014-05-26 | SELL | 581.88 |
| 2014-05-30 | BUY | 621.00 |
| 2014-05-31 | SELL | 627.80 |
| 2014-06-01 | BUY | 630.99 |
| 2014-06-02 | SELL | 661.22 |
| 2014-06-03 | BUY | 670.14 |
| 2014-06-04 | SELL | 640.59 |
| 2014-11-12 | BUY | 426.63 |
| 2014-11-13 | SELL | 420.93 |
| 2015-03-01 | BUY | 258.34 |
| 2015-03-02 | SELL | 274.93 |
| 2015-03-03 | BUY | 281.00 |
| 2015-03-04 | SELL | 270.78 |
| 2015-03-09 | BUY | 287.12 |
| 2015-03-10 | SELL | 290.00 |
| 2015-03-11 | BUY | 296.54 |
| 2015-03-12 | SELL | 295.31 |
| 2015-06-16 | BUY | 250.09 |
| 2015-08-24 | SELL | 209.72 |
| 2015-10-06 | BUY | 246.57 |
| 2017-01-11 | SELL | 778.62 |
| 2017-02-04 | BUY | 1033.18 |
| 2017-07-15 | SELL | 1970.51 |
| 2017-07-20 | BUY | 2875.03 |

Luoi 27 o (LN T / DD T . C1C2C3 . so lan doi; B&H +289.6 % / -81.4 %):

thr 0.65 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +240.9 / -62.9 . xxx . 24 | +347.1 / -57.0 . xDx . 16 | +340.7 / -58.6 . xDx . 11
P=180 | +216.0 / -65.6 . xxx . 38 | +575.1 / -43.2 . DDx . 24 | +590.5 / -35.2 . DDD . 19
P=240 | +365.6 / -49.3 . xDx . 46 | +554.4 / -43.2 . DDx . 32 | +569.4 / -35.2 . DDD . 27

thr 0.70 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +218.3 / -54.8 . xxx . 30 | +246.5 / -50.0 . xxx . 22 | +246.9 / -50.1 . xxx . 17
P=180 | +315.3 / -41.6 . DDx . 42 | +397.5 / -41.6 . DDx . 28 | +398.2 / -38.7 . DDD . 23
P=240 | +293.7 / -44.1 . DDx . 50 | +359.3 / -41.6 . DDx . 36 | +359.9 / -38.7 . DDD . 31

thr 0.75 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +194.7 / -43.7 . Dxx . 38 | +225.5 / -37.6 . DxD . 28 | +195.2 / -38.9 . DxD . 23
P=180 | +237.8 / -35.4 . DxD . 50 | +300.0 / -37.6 . DDD . 34 | +262.7 / -38.9 . DxD . 29
P=240 | +254.4 / -34.7 . DxD . 58 | +319.6 / -37.6 . DDD . 42 | +280.5 / -38.9 . DxD . 37

Phu (khong tham gia verdict) - warm-start lien tuc tu dau du lieu (2013-07-01; 1 lan doi truoc t0; t0 trang thai OFF): T +397.5 % / DD -41.6 % / 27 doi / 594 ngay OFF ; C1/C2/C3 = D/D/x

Phu (mo ta) - do nhay phi 0,30 %/chieu (ca T va B&H): T +377.8 % / CAGR +54.7 % / DD -41.8 % ; B&H +289.0 % / DD -81.4 % ; C1/C2/C3 = D/D/x ; luoi 10/27 o dat C1&C2

### B1_ETH_2018_2019 - ETHUSDT spot, cua so cham 2017-12-31..2019-12-31 (730 buoc; lich su close truoc t0 = 137 ngay)

| | tong LN | CAGR | maxDD | dinh -> day (close ngay) | so lan doi | ngay OFF |
|---|---|---|---|---|---|---|
| T | +63.5 % | +27.9 % | -40.3 % | 2018-01-13 -> 2019-04-25 | 33 | 583 / 731 |
| B&H | -82.4 % | -58.1 % | -94.0 % | 2018-01-13 -> 2018-12-15 | - | - |

Tieu chi: C1 |DD_T|<=0,6x|DD_B&H| : 40.3 % vs 94.0 % -> ty le 0.429 -> DAT ; C2 LN_T>=LN_B&H : +63.5 % vs -82.4 % -> DAT ; C3 |DD_T|<=40 % : 40.3 % -> TRUOT ; luoi 26/27 (can >= 19) -> DAT ; **verdict FAIL**

Dot ON (net phi): 17 dot, 10 thang, median +0.6 %, min -16.5 %, max +36.7 % (2019-04-05 -> 2019-07-14); 15 dot keo dai <= 2 ngay; LN 16 dot con lai nhan lai +19.6 %; ty phan log-LN cua dot lon nhat 64 %

Dot ON:

| # | vao | ra | LN |
|---|---|---|---|
| 1 | 2017-12-31 | 2018-02-02 | +25.3 % |
| 2 | 2018-04-19 | 2018-04-20 | +8.3 % |
| 3 | 2018-04-22 | 2018-04-23 | +3.6 % |
| 4 | 2018-04-24 | 2018-04-25 | -12.2 % |
| 5 | 2018-05-03 | 2018-05-04 | +0.6 % |
| 6 | 2018-05-05 | 2018-05-06 | -3.4 % |
| 7 | 2018-12-23 | 2018-12-24 | +6.7 % |
| 8 | 2019-01-01 | 2019-01-02 | +9.0 % |
| 9 | 2019-01-05 | 2019-01-06 | +0.4 % |
| 10 | 2019-02-17 | 2019-02-18 | +8.6 % |
| 11 | 2019-02-20 | 2019-02-21 | -2.1 % |
| 12 | 2019-02-23 | 2019-02-24 | -16.5 % |
| 13 | 2019-03-29 | 2019-03-30 | -0.8 % |
| 14 | 2019-04-02 | 2019-04-03 | -2.3 % |
| 15 | 2019-04-05 | 2019-07-14 | +36.7 % |
| 16 | 2019-09-17 | 2019-09-18 | +0.8 % |
| 17 | 2019-09-19 | 2019-09-20 | -1.3 % |

Ngay doi trang thai (close UTC; dong dau = mua khoi tao tai t0):

| ngay | lenh | gia |
|---|---|---|
| 2017-12-31 | BUY | 733.98 |
| 2018-02-02 | SELL | 922.30 |
| 2018-04-19 | BUY | 568.14 |
| 2018-04-20 | SELL | 617.09 |
| 2018-04-22 | BUY | 620.92 |
| 2018-04-23 | SELL | 645.09 |
| 2018-04-24 | BUY | 701.58 |
| 2018-04-25 | SELL | 618.00 |
| 2018-05-03 | BUY | 779.00 |
| 2018-05-04 | SELL | 785.99 |
| 2018-05-05 | BUY | 819.50 |
| 2018-05-06 | SELL | 794.30 |
| 2018-12-23 | BUY | 129.03 |
| 2018-12-24 | SELL | 138.03 |
| 2019-01-01 | BUY | 139.10 |
| 2019-01-02 | SELL | 152.01 |
| 2019-01-05 | BUY | 152.83 |
| 2019-01-06 | SELL | 153.86 |
| 2019-02-17 | BUY | 133.75 |
| 2019-02-18 | SELL | 145.69 |
| 2019-02-20 | BUY | 148.44 |
| 2019-02-21 | SELL | 145.69 |
| 2019-02-23 | BUY | 157.79 |
| 2019-02-24 | SELL | 132.10 |
| 2019-03-29 | BUY | 143.25 |
| 2019-03-30 | SELL | 142.46 |
| 2019-04-02 | BUY | 163.31 |
| 2019-04-03 | SELL | 159.96 |
| 2019-04-05 | BUY | 164.77 |
| 2019-07-14 | SELL | 225.85 |
| 2019-09-17 | BUY | 207.84 |
| 2019-09-18 | SELL | 210.21 |
| 2019-09-19 | BUY | 220.24 |
| 2019-09-20 | SELL | 218.03 |

Luoi 27 o (LN T / DD T . C1C2C3 . so lan doi; B&H -82.4 % / -94.0 %):

thr 0.65 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +5.6 / -57.5 . xDx . 41 | +63.3 / -43.4 . DDx . 27 | +37.1 / -42.7 . DDx . 17
P=180 | +3.5 / -52.9 . DDx . 47 | +32.8 / -44.9 . DDx . 31 | +26.2 / -47.2 . DDx . 19
P=240 | -11.1 / -53.4 . DDx . 53 | +14.0 / -43.4 . DDx . 37 | +8.4 / -45.6 . DDx . 25

thr 0.70 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +68.5 / -45.6 . DDx . 43 | +94.2 / -36.6 . DDD . 29 | +60.5 / -40.9 . DDx . 19
P=180 | +36.9 / -48.9 . DDx . 49 | +63.5 / -40.3 . DDx . 33 | +55.4 / -42.8 . DDx . 21
P=240 | +21.5 / -45.6 . DDx . 53 | +45.0 / -36.6 . DDD . 37 | +37.9 / -39.1 . DDD . 25

thr 0.75 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +82.7 / -41.0 . DDx . 43 | +110.5 / -33.9 . DDD . 29 | +74.0 / -35.9 . DDD . 19
P=180 | +20.9 / -45.2 . DDx . 53 | +44.4 / -35.9 . DDD . 37 | +37.2 / -38.6 . DDD . 25
P=240 | +31.7 / -41.0 . DDx . 53 | +57.3 / -33.9 . DDD . 37 | +49.5 / -34.4 . DDD . 25

Phu (khong tham gia verdict) - warm-start lien tuc tu dau du lieu (2017-08-17; 2 lan doi truoc t0; t0 trang thai ON): T +63.5 % / DD -40.3 % / 33 doi / 583 ngay OFF ; C1/C2/C3 = D/D/x

Phu (mo ta) - do nhay phi 0,30 %/chieu (ca T va B&H): T +55.3 % / CAGR +24.6 % / DD -42.8 % ; B&H -82.5 % / DD -94.0 % ; C1/C2/C3 = D/D/x ; luoi 25/27 o dat C1&C2

### B2_ETH_2021_2025 - ETHUSDT spot, cua so cham 2021-06-30..2025-12-31 (1645 buoc; lich su close truoc t0 = 181 ngay)

| | tong LN | CAGR | maxDD | dinh -> day (close ngay) | so lan doi | ngay OFF |
|---|---|---|---|---|---|---|
| T | +29.5 % | +5.9 % | -52.8 % | 2021-09-05 -> 2022-08-10 | 69 | 702 / 1646 |
| B&H | +30.4 % | +6.1 % | -79.3 % | 2021-11-08 -> 2022-06-18 | - | - |

Tieu chi: C1 |DD_T|<=0,6x|DD_B&H| : 52.8 % vs 79.3 % -> ty le 0.666 -> TRUOT ; C2 LN_T>=LN_B&H : +29.5 % vs +30.4 % -> TRUOT ; C3 |DD_T|<=40 % : 52.8 % -> TRUOT ; luoi 0/27 (can >= 19) -> TRUOT ; **verdict FAIL**

Dot ON (net phi): 34 dot, 12 thang, median -1.7 %, min -15.9 %, max +100.7 % (2023-01-10 -> 2024-08-04); 27 dot keo dai <= 2 ngay; LN 33 dot con lai nhan lai -35.5 %; ty phan log-LN cua dot lon nhat 269 %

Dot ON:

| # | vao | ra | LN |
|---|---|---|---|
| 1 | 2021-07-29 | 2021-07-30 | +3.0 % |
| 2 | 2021-07-31 | 2021-08-01 | +0.7 % |
| 3 | 2021-08-02 | 2021-08-03 | -4.0 % |
| 4 | 2021-08-04 | 2021-08-05 | +3.4 % |
| 5 | 2021-08-06 | 2021-09-21 | -4.6 % |
| 6 | 2021-10-14 | 2022-01-07 | -15.9 % |
| 7 | 2022-03-23 | 2022-03-24 | +2.2 % |
| 8 | 2022-03-26 | 2022-03-27 | +4.5 % |
| 9 | 2022-03-28 | 2022-03-31 | -1.8 % |
| 10 | 2022-04-01 | 2022-04-06 | -8.6 % |
| 11 | 2022-07-16 | 2022-07-17 | -1.6 % |
| 12 | 2022-07-18 | 2022-07-19 | -2.7 % |
| 13 | 2022-07-24 | 2022-07-25 | -10.1 % |
| 14 | 2022-07-27 | 2022-07-28 | +5.1 % |
| 15 | 2022-08-05 | 2022-08-06 | -3.0 % |
| 16 | 2022-08-08 | 2022-08-09 | -4.5 % |
| 17 | 2022-08-10 | 2022-08-11 | +1.1 % |
| 18 | 2022-08-12 | 2022-08-13 | +1.0 % |
| 19 | 2022-10-23 | 2022-10-24 | -1.8 % |
| 20 | 2022-10-25 | 2022-10-26 | +7.0 % |
| 21 | 2022-10-29 | 2022-10-30 | -2.1 % |
| 22 | 2022-11-04 | 2022-11-05 | -1.4 % |
| 23 | 2022-12-13 | 2022-12-14 | -1.3 % |
| 24 | 2023-01-10 | 2024-08-04 | +100.7 % |
| 25 | 2024-09-27 | 2024-09-28 | -1.0 % |
| 26 | 2024-10-20 | 2024-10-21 | -3.2 % |
| 27 | 2024-11-07 | 2025-02-04 | -6.0 % |
| 28 | 2025-05-02 | 2025-05-03 | -0.8 % |
| 29 | 2025-05-08 | 2025-05-09 | +5.9 % |
| 30 | 2025-05-10 | 2025-05-11 | -2.9 % |
| 31 | 2025-05-13 | 2025-05-14 | -2.9 % |
| 32 | 2025-05-28 | 2025-05-29 | -2.2 % |
| 33 | 2025-06-10 | 2025-06-11 | -1.9 % |
| 34 | 2025-07-10 | 2025-11-04 | +11.0 % |

Ngay doi trang thai (close UTC; dong dau = mua khoi tao tai t0):

| ngay | lenh | gia |
|---|---|---|
| 2021-07-29 | BUY | 2382.92 |
| 2021-07-30 | SELL | 2461.81 |
| 2021-07-31 | BUY | 2531.05 |
| 2021-08-01 | SELL | 2555.69 |
| 2021-08-02 | BUY | 2606.93 |
| 2021-08-03 | SELL | 2509.04 |
| 2021-08-04 | BUY | 2724.78 |
| 2021-08-05 | SELL | 2826.99 |
| 2021-08-06 | BUY | 2891.58 |
| 2021-09-21 | SELL | 2765.90 |
| 2021-10-14 | BUY | 3790.82 |
| 2022-01-07 | SELL | 3199.24 |
| 2022-03-23 | BUY | 3036.00 |
| 2022-03-24 | SELL | 3110.76 |
| 2022-03-26 | BUY | 3145.00 |
| 2022-03-27 | SELL | 3295.65 |
| 2022-03-28 | BUY | 3332.92 |
| 2022-03-31 | SELL | 3281.51 |
| 2022-04-01 | BUY | 3455.21 |
| 2022-04-06 | SELL | 3168.51 |
| 2022-07-16 | BUY | 1355.85 |
| 2022-07-17 | SELL | 1338.65 |
| 2022-07-18 | BUY | 1581.04 |
| 2022-07-19 | SELL | 1542.32 |
| 2022-07-24 | BUY | 1597.70 |
| 2022-07-25 | SELL | 1440.79 |
| 2022-07-27 | BUY | 1635.74 |
| 2022-07-28 | SELL | 1724.52 |
| 2022-08-05 | BUY | 1736.81 |
| 2022-08-06 | SELL | 1690.60 |
| 2022-08-08 | BUY | 1777.05 |
| 2022-08-09 | SELL | 1702.76 |
| 2022-08-10 | BUY | 1853.57 |
| 2022-08-11 | SELL | 1880.19 |
| 2022-08-12 | BUY | 1958.28 |
| 2022-08-13 | SELL | 1983.55 |
| 2022-10-23 | BUY | 1364.20 |
| 2022-10-24 | SELL | 1343.61 |
| 2022-10-25 | BUY | 1459.74 |
| 2022-10-26 | SELL | 1566.10 |
| 2022-10-29 | BUY | 1619.55 |
| 2022-10-30 | SELL | 1590.44 |
| 2022-11-04 | BUY | 1644.78 |
| 2022-11-05 | SELL | 1626.98 |
| 2022-12-13 | BUY | 1320.69 |
| 2022-12-14 | SELL | 1307.44 |
| 2023-01-10 | BUY | 1335.62 |
| 2024-08-04 | SELL | 2688.92 |
| 2024-09-27 | BUY | 2694.43 |
| 2024-09-28 | SELL | 2675.21 |
| 2024-10-20 | BUY | 2746.91 |
| 2024-10-21 | SELL | 2666.70 |
| 2024-11-07 | BUY | 2895.47 |
| 2025-02-04 | SELL | 2731.19 |
| 2025-05-02 | BUY | 1842.20 |
| 2025-05-03 | SELL | 1833.52 |
| 2025-05-08 | BUY | 2207.39 |
| 2025-05-09 | SELL | 2345.04 |
| 2025-05-10 | BUY | 2583.23 |
| 2025-05-11 | SELL | 2514.57 |
| 2025-05-13 | BUY | 2679.71 |
| 2025-05-14 | SELL | 2609.74 |
| 2025-05-28 | BUY | 2681.60 |
| 2025-05-29 | SELL | 2631.39 |
| 2025-06-10 | BUY | 2816.40 |
| 2025-06-11 | SELL | 2771.61 |
| 2025-07-10 | BUY | 2951.29 |
| 2025-11-04 | SELL | 3287.05 |

Luoi 27 o (LN T / DD T . C1C2C3 . so lan doi; B&H +30.4 % / -79.3 %):

thr 0.65 | R=20 | R=30 | R=40
---|---|---|---
P=120 | -24.1 / -81.0 . xxx . 51 | +23.6 / -71.5 . xxx . 39 | +13.9 / -72.9 . xxx . 31
P=180 | -13.9 / -67.3 . xxx . 77 | -13.4 / -63.4 . xxx . 61 | -9.8 / -60.7 . xxx . 47
P=240 | +5.9 / -66.2 . xxx . 85 | +20.4 / -59.6 . xxx . 61 | +14.3 / -57.7 . xxx . 47

thr 0.70 | R=20 | R=30 | R=40
---|---|---|---
P=120 | +1.2 / -75.8 . xxx . 69 | +32.6 / -64.9 . xDx . 51 | +30.8 / -66.0 . xDx . 37
P=180 | +49.7 / -53.2 . xDx . 93 | +29.5 / -52.8 . xxx . 69 | +15.9 / -57.6 . xxx . 55
P=240 | +36.9 / -53.2 . xDx . 97 | +26.7 / -52.8 . xxx . 71 | +13.4 / -57.6 . xxx . 57

thr 0.75 | R=20 | R=30 | R=40
---|---|---|---
P=120 | -14.7 / -63.0 . xxx . 91 | -6.0 / -63.3 . xxx . 71 | +5.9 / -58.0 . xxx . 55
P=180 | +10.2 / -55.8 . xxx . 113 | -12.4 / -54.7 . xxx . 89 | -10.7 / -48.4 . xxx . 73
P=240 | -12.4 / -55.8 . xxx . 119 | -30.4 / -54.6 . xxx . 93 | -29.1 / -58.7 . xxx . 77

Phu (khong tham gia verdict) - warm-start lien tuc tu dau du lieu (2021-01-01; 1 lan doi truoc t0; t0 trang thai OFF): T +29.5 % / DD -52.8 % / 68 doi / 702 ngay OFF ; C1/C2/C3 = x/x/x

Phu (mo ta) - do nhay phi 0,30 %/chieu (ca T va B&H): T +17.0 % / CAGR +3.5 % / DD -54.8 % ; B&H +30.2 % / DD -79.3 % ; C1/C2/C3 = x/x/x ; luoi 0/27 o dat C1&C2
