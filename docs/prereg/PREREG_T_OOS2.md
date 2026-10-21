# PREREG_T_OOS2 — kiểm độc lập lần 2 bộ lọc T (sleeve spot) trên BTC 2014–2017 (Bitstamp) và ETH 2018–2019 / 2021H2–2025

Ngày 2026-10-21. Viết + commit TRƯỚC khi tải/đụng dữ liệu của 3 kỳ mới (BTC Bitstamp 2013-07→2017-07, ETHUSDT 2017-08→2019-12 và 2021-01→2025-12) và trước mọi phép tính kết quả trên chúng.
Sau commit này không đổi tham số, cửa sổ, tiêu chí, phí, quy ước khớp lệnh, quy tắc xử lý dữ liệu. Chỉ-đọc: 0 Binance REST (chỉ file tĩnh data.binance.vision + Kaggle API tải dataset), 0 đụng 242/shadow/live, 0 push.
Điều kiện biên đã biết trước khi viết (minh bạch): tác giả prereg biết lịch sử giá BTC/ETH ở mức kiến thức chung (đỉnh BTC 12/2013, đáy 01/2015, bull 2017...), KHÔNG xem bất kỳ số liệu/kết quả nào của 3 kỳ trên trước khi chốt prereg này; luật T cố định nên kiến thức chung không đổi được tham số nào.

## 1. Mục tiêu và giới hạn

T (BTC_BASE 2e788551; T_OOS 2018–2019 prereg 27d33a1e / result fec04da5 = PASS yếu: DD −35,3 %, +75,4 %, 21/27 ô, lợi nhuận dồn vào 1 đợt +104 %, 15/18 đợt ≤ 2 ngày).
T_OOS chỉ kiểm 1 bear (2018) trên 1 tài sản. T_OOS2 thêm: (A) BTC ở một chế độ thị trường khác hẳn (2014 bear → 2015 đáy → 2016–2017 bull, trước Binance, sàn Bitstamp) là **phép thử chính cho BTC**; (B) kiểm tổng quát hoá sang tài sản khác (ETH).
Quy tắc phiên giải: PASS ⇒ "không bị bác bỏ", không phải bằng chứng; FAIL ⇒ ghi nhận bác bỏ, không có tiêu chí cứu. n sự kiện nhỏ.
**Dữ liệu 2020 niêm phong**: không tải, không đọc, không dùng kể cả warmup. Chỉ tải tháng ETH ≤ 2019-12 và ≥ 2021-01; file Kaggle BTC chứa dữ liệu tới hiện tại (gồm 2020+) ⇒ xem §2(A) về cách khoá (mọi dòng ≥ 2018-01-01 UTC bị bỏ ngay khi quét theo chunk: parser có nạp chúng vào bộ nhớ khi đọc chunk nhưng không xem giá, không tính, không ghi ra đĩa).

## 2. Dữ liệu cố định

**(A) BTC 2014-01-01 → 2017-07-31** — Kaggle dataset `mczielinski/bitcoin-historical-data` (file `btcusd_1-min_data.csv`, 377 MB, Bitstamp BTCUSD 1 phút; Kaggle API trên Oracle). Chỉ lấy cột `Timestamp`, `Close`. Lưu sha256/kích thước file gốc vào báo cáo.
- Lấy dòng có ts ∈ [2013-07-01 00:00, 2018-01-01 00:00) UTC (cột Timestamp = giây epoch UTC; nếu > 1e11 coi là ms). Dòng ts ≥ 2018-01-01 bị bỏ ngay khi quét theo chunk, chỉ đếm số dòng bị bỏ, không tính gì trên chúng, không ghi ra đĩa. Dòng Close NaN bị bỏ (đếm). Trùng ts: giữ dòng cuối (đếm).
- Close ngày UTC = Close của bar có ts lớn nhất trong ngày UTC (không lấp phút thiếu; ghi lại phân phối "khoảng cách từ bar cuối đến 23:59" và số bar/ngày chỉ để báo cáo, không sửa dữ liệu). Ngày không có bar nào = ngày thiếu → ffill close ngày trước; **tổng ngày thiếu trong 2013-07-01→2017-07-31 > 5 hoặc chuỗi thiếu liên tiếp > 3 ⇒ DỪNG, báo MASTER, không tính** (`btc_data_report_STOP.json`).
- Warmup: 2013-07-01→2013-12-31 (184 ngày close; không chấm). Cửa sổ chấm A: t0 = close 2013-12-31 → close 2017-07-31 (1308 bước ngày).
- Cắt cứng cuối kỳ 2017-07-31: dòng 2017-08-01→2018-01-01 chỉ được trích riêng làm `xcheck` 2017-08-17→2017-12-31 (đối chiếu với Binance BTCUSDT 1d spot đã có `docs/result/t_oos/btcusdt_1d_clean.csv`), KHÔNG vào bất kỳ phép tính chấm nào. **xcheck median |Bitstamp/Binance − 1| > 1 % ⇒ DỪNG** (sai đơn vị/lệch dữ liệu), báo cáo thêm p95/max/số ngày > 3 %.
- Sau khi xong, file gốc (zip/csv) bị XÓA khỏi Oracle (chỉ giữ sha256), giữ bản trích phút < 2018-01-01 (`btc_bitstamp_1m_2013-07_2017-12.csv.gz`, sha256 trong report) + close ngày sạch. Đơn vị giá USD (không phải USDT) — khác Binance, ghi trong báo cáo.

**(B) ETHUSDT spot, Vision 1d** (`data.binance.vision/data/spot/monthly/klines/ETHUSDT/1d/`): sha256 từng file theo `.CHECKSUM` phải khớp; đủ ngày, không trùng; open_time 00:00 UTC; assert không có ngày năm 2020; ngày thiếu mỗi đoạn ≤ 3 ⇒ ffill close ngày trước + ghi lại, > 3 ⇒ DỪNG báo MASTER.
- B1: file 2017-08 → 2019-12 (ngày 2017-08-17→2019-12-31); chấm 2018-01-01→2019-12-31 (t0 = close 2017-12-31; 730 bước), lịch sử trước t0 = 137 ngày close (cửa sổ mở rộng cho đến 2018-02-12, như T_OOS BTC).
- B2: file 2021-01 → 2025-12 (ngày 2021-01-01→2025-12-31; **không dùng 2020**); chấm 2021-07-01→2025-12-31 (t0 = close 2021-06-30; 1645 bước), warmup 2021-01-01→2021-06-30 = 181 ngày close tại t0. **Ảnh hưởng warmup ngắn (ghi trước):** P = 180 đủ cửa sổ tại t0 (181 ≥ 180) nhưng chỉ vừa đủ; các ô lưới P = 240 dùng cửa sổ mở rộng (đỉnh chỉ trên 181 ngày) cho đến khi đủ 240 ngày (~2021-08-28), tức đỉnh có thể bị đánh giá thấp so với lịch sử thật ở 2020 (không dùng) ⇒ lưới P = 240 hơi khác nghĩa trong ~2 tháng đầu; không điều chỉnh.
- Bất đối xứng độc lập (ghi trước, không đổi verdict): B2 trùng khung thời gian với DEV của chính luật T (BTC_BASE phát triển trên 2021-07→2025) ⇒ B2 chỉ độc lập về tài sản, KHÔNG độc lập về thời gian; ETH và BTC tương quan cao. B1 trùng khung thời gian với T_OOS BTC (2018–2019) nhưng là tài sản khác. Chỉ A độc lập cả thời gian lẫn nền tảng dữ liệu.

## 3. Định nghĩa T, vị thế, phí, chỉ số (giữ nguyên T_OOS)

Tái dùng ĐÚNG các hàm trong `docs/result/t_oos/t_oos.py` (sha256 d36af81313e95829b285064c03995e8b81bb79ad16565db30cc60a14a560cfaf; bản sao từng dòng bb_core.simulate :374–386), nạp theo đường dẫn và assert sha256: `t_states`, `run_equity`, `bh_equity`, `metrics`, `evaluate`, `ep_rows`, `trade_rows`, `lookahead_check`, hằng `BASE` (thr 0,70 / P 180 / R 30), `GRID_*`, `COST`.
- Mốc ngày: close ngày UTC; quyết định + khớp tại close ngày d chỉ dùng close ≤ d. ON: chuyển OFF khi `close[d] ≤ thr × max(close[d−(P−1)..d])` (đỉnh gồm ngày hiện tại); OFF: chuyển ON khi `close[d] > max(close[d−R..d−1])` (không gồm ngày hiện tại). Tối đa 1 chuyển/ngày. **Trạng thái khởi tạo ON tại t0** (cold start, primary) áp luật tại t0 và các ngày sau với lịch sử close sẵn có (warmup); cửa sổ mở rộng khi chưa đủ.
- ON = 100 % tài sản spot; OFF = tiền mặt lãi 0. Phí 0,10 % + trượt 0,05 % = 0,15 %/chiều (cả T và B&H). B&H mua tại close t0, giữ tới hết kỳ; không thanh lý cuối kỳ. Chỉ số trên equity theo close ngày bắt đầu 1,0: tổng LN, CAGR = E_end^(365/số bước) − 1, maxDD (kèm ngày đỉnh → đáy), số lần đổi, số ngày OFF (đếm ngày quyết định có trạng thái OFF / tổng ngày quyết định), LN từng đợt ON (net phí cả hai chiều; đợt mở cuối kỳ tính MTM).

## 4. Tiêu chí mỗi kỳ (A, B1, B2 độc lập; tại tham số trung tâm)

- **C1**: |maxDD(T)| ≤ 0,6 × |maxDD(B&H)|. **C2**: tổng LN(T) ≥ tổng LN(B&H). **C3**: |maxDD(T)| ≤ 40 % tuyệt đối.
- **Điều kiện phụ**: lưới 27 ô thr ∈ {0,65; 0,70; 0,75} × P ∈ {120; 180; 240} × R ∈ {20; 30; 40}, ≥ 19/27 ô (≥ 70 %) đạt C1 ∧ C2; ô trung tâm = primary (assert). Lưới KHÔNG dùng để chọn lại tham số; C3 từng ô chỉ báo cáo.
- Kỳ **PASS (không bị bác bỏ)** ⇔ C1 ∧ C2 ∧ C3 ∧ điều kiện phụ; ngược lại **FAIL**. Không có tiêu chí cứu.

## 5. Verdict tổng

- **(A) BTC 2014–2017** = phép thử chính cho BTC: PASS ⇒ "T không bị bác bỏ lần 2 (BTC)"; FAIL ⇒ "T bị bác bỏ trên BTC 2014–2017" (không còn được mô tả là không bị bác bỏ lần 2).
- **(B) ETH** = kiểm tổng quát hoá, báo PASS/FAIL từng kỳ (B1, B2): cả 2 PASS ⇒ "T không bị bác bỏ trên ETH (B2 chỉ độc lập về tài sản)"; cả 2 FAIL ⇒ ghi đúng "**T không tổng quát sang ETH**"; 1 PASS 1 FAIL ⇒ "hỗn hợp, không kết luận tổng quát". B không thay verdict A và A không thay verdict B.
- Phần phụ CHỈ báo cáo, không tham gia verdict, kể cả khi bất đồng (khi đó ghi rõ là bất đồng): (a) warm-start: máy trạng thái chạy liên tục từ ngày đầu dữ liệu (ON khởi tạo ngày đầu, cửa sổ mở rộng), tính tiền từ t0 với vị thế = trạng thái tại t0; (b) **độ nhạy phí 0,30 %/chiều** (gấp đôi; cả T và B&H): primary + C1–C3 + số ô lưới đạt C1∧C2 — mô tả, không verdict.

## 6. Báo cáo bắt buộc (`docs/result/T_OOS2.md`, bảng tự sinh từ `t_oos2_tab.md`)

Mỗi kỳ: bảng T vs B&H (tổng LN, CAGR, maxDD + ngày đỉnh → đáy, số lần đổi, ngày OFF), số đợt ON, đợt thắng, đóng góp đợt lớn nhất (LN và tỷ phần log-LN), **LN các đợt còn lại nhân lại** (tích (1+LN_i) của mọi đợt trừ đợt có LN lớn nhất, trừ 1), danh sách đợt ON, danh sách ngày đổi trạng thái kèm giá, bảng 27 ô, warm-start, độ nhạy phí 0,30 %. Kèm bảng dữ liệu (nguồn, sha256, ngày thiếu, QA) và V1–V3.

## 7. Kiểm vệ sinh (bắt buộc trước khi báo)

- **V1**: tái lập T_OOS BTC 2018–2019 bằng chính mã `t_oos2.py` + `t_oos.py` trên `docs/result/t_oos/btcusdt_1d_clean.csv` (sha256 b08921d392de29b310c93dd298d7f4bdc7f781abb9e839efccee2565b7e85f7a): **+75,4 %, DD −35,3 %, 35 lần đổi, 523 ngày OFF, 21/27 ô, 18 đợt, danh sách giao dịch** khớp từng số với `t_oos_res.json` (assert). Hàm đo phí-0,30 % (`evaluate_cost`) phải cho kết quả = `evaluate` tại phí 0,15 %. (Đã chạy trên dữ liệu T_OOS cũ trước commit này; không đụng dữ liệu kỳ mới.)
- **V2**: không có dữ liệu năm 2020: assert không ngày nào có năm 2020 trong mọi CSV sạch; BTC Bitstamp max < 2017-08-01 (+ xcheck < 2018-01-01); ETH chỉ tháng 2017-08..2019-12 và 2021-01..2025-12.
- **V3**: không look-ahead (cắt dữ liệu sau mốc và thay giá sau mốc bằng random walk ⇒ state + equity ≤ mốc không đổi), mốc cố định: A 2015-06-30, 2016-06-30, 2017-03-31; B1 2018-04-30, 2018-12-31, 2019-06-30; B2 2022-06-30, 2023-12-31, 2025-03-31 (cả 2 kiểu, `lookahead_check` của T_OOS).
- **Dữ liệu**: theo §2 (checksum ETH 100 %, không trùng, ngày thiếu, assert không 2020, QA Bitstamp, xcheck, quy tắc DỪNG).
- Tự kiểm mã trước commit (không dùng dữ liệu kỳ mới): `t_oos2.py --mode selftest` (V1 pass), parser BTC thử trên dữ liệu tổng hợp ngẫu nhiên (`t_oos2_synth.py`), parser ETH thử trên BTCUSDT 2025-10..11 (khung DEV); pipeline `--mode run` thử trên random-walk tổng hợp (không phải giá thật).
- Lỗi crash của script (không đổi logic) có thể sửa sau commit này nhưng phải ghi trong báo cáo; mọi thay đổi logic/tham số/tiêu chí bị cấm.

## 8. Đặc điểm đã biết trước (ghi để không giải thích sau khi thấy kết quả)

1. Cold-start ON tại t0: ở A, t0 = 2013-12-31 ngay sau đỉnh 12/2013; T khởi tạo ON rồi có thể về OFF ngay 2014-01-01 (đợt #1 ngắn, chịu phí 2 chiều) — là artefact quy ước khởi tạo ON giữ đúng gốc; warm-start báo cáo phụ.
2. C2 kỳ A: BTC 2014-01→2017-07 là chuỗi tăng dài sau bear 2014 ⇒ B&H có LN dương lớn dù DD sâu; C2 (T ≥ B&H) khó hơn T_OOS (nơi B&H âm). Không điều chỉnh tiêu chí.
3. ETH có DD và biến động lớn hơn BTC; C3 (≤ 40 %) có thể trượt vì tài sản, không phải vì luật; không nới.
4. Bitstamp là USD fiat, thanh khoản 2014 mỏng, close "bar cuối trong ngày" có thể sớm hơn 23:59 (khoảng cách ghi trong báo cáo); phí 0,15 %/chiều giữ nguyên như spot Binance.
5. Verdict phụ thuộc n nhỏ (số đợt ON), có thể dồn vào 1 đợt; báo cáo đóng góp đợt lớn nhất và LN các đợt còn lại.

## 9. Mã

Commit cùng prereg (chưa chạy trên dữ liệu kỳ mới), thư mục `docs/result/t_oos2/`:
- `t_oos2.py` sha256 647ddf4029703f10c99f48d8b2dfd17f8e65570111111eebffde54d78aea43a1 (runner + V1 + bảng)
- `t_oos2_data_btc.py` sha256 2a24e0d073adadc6e7144f02a6a0f7a91c457eb7d29b69d801d86438f1bc9c2d
- `t_oos2_data_eth.py` sha256 6fbc05e33e35bae7a175dad4d7a7f8b9c2528a2812b05a20c5940e232b980ba3
- `t_oos2_synth.py` sha256 c41dc21f3887a6b5eac9934b33572ed7971966a8c0bf67d88161c099e00340ce (dữ liệu tổng hợp kiểm parser)
- Phụ thuộc: `docs/result/t_oos/t_oos.py` sha256 d36af81313e95829b285064c03995e8b81bb79ad16565db30cc60a14a560cfaf.
Dữ liệu tải về đặt ngoài repo: `~/claude_master/t_oos2/data/{raw,clean}` (thư mục riêng, không chứa script).
