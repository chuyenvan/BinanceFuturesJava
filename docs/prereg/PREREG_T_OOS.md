# PREREG_T_OOS — kiểm ngoài mẫu bộ lọc T (BTC sleeve) trên 2018–2019

Ngày 2026-10-20. Viết + commit TRƯỚC khi tải dữ liệu 2018–2019 và trước mọi phép tính kết quả trên 2018–2019. Sau commit này
không đổi tham số, cửa sổ, tiêu chí, phí, quy ước khớp lệnh. Chỉ-đọc: 0 Binance REST (chỉ file tĩnh data.binance.vision), 0 đụng 242/shadow/live, 0 push.

## 1. Mục tiêu và giới hạn

Bộ lọc T (BTC_BASE, `docs/result/BTC_BASE.md` §3) trên DEV 2021-07→2025: sleeve về 0 khi close ngày ≤ 70 % đỉnh close 180 ngày; vào lại khi
close ngày > max close 30 ngày trước đó. Lo ngại: 1 tài sản, chủ yếu né 1 bear (2022), cùng họ trend-filter (MA200 từng FAIL).
Owner yêu cầu kiểm ngoài mẫu trên 2018–2019 (bear 2018 + hồi phục 2019). Chỉ kiểm sleeve BTC đứng riêng (T vs B&H BTC), KHÔNG có crash-buy
(không có sim 2018–2019). n sự kiện nhỏ (dự kiến vài lần đổi trạng thái) ⇒ **PASS chỉ là "không bị bác bỏ", không phải bằng chứng**; FAIL ⇒ T không vào v1.1.
**Dữ liệu 2020 niêm phong**: không tải, không dùng, kể cả warmup/thống kê (tháng cuối được tải: 2019-12).

## 2. Định nghĩa T (tái dùng đúng nghĩa `bb_core.simulate`, dòng 374–386)

- Mốc ngày: close ngày UTC = close nến 1d Vision (tương đương close phút 23:59 UTC dùng ở bb_core). Quyết định tại close ngày d chỉ dùng close ≤ d;
  khớp lệnh tại chính close ngày d đó (quy ước gốc: quyết định + khớp ở close phút 23:59).
- Tham số trung tâm: thr = 0,70, P = 180, R = 30.
- Nếu đang ON: chuyển OFF khi `close[d] <= thr * max(close[d-(P-1) .. d])` (đỉnh **gồm** ngày hiện tại, cửa sổ P close).
- Nếu đang OFF: chuyển ON khi `close[d] > max(close[d-R .. d-1])` (max **không gồm** ngày hiện tại, R close trước đó) và d ≥ 1.
- Tối đa 1 chuyển trạng thái/ngày (cấu trúc if/else của gốc). Trạng thái khởi tạo ON (như gốc: ON tại đầu cửa sổ).
- Cửa sổ mở rộng khi chưa đủ lịch sử: dùng `max(0, ·)` như gốc, tức đỉnh/max lấy trên phần dữ liệu có sẵn kể từ 2017-08-17
  (dữ liệu Vision spot BTCUSDT 1d bắt đầu 2017-08-17). Đủ 180 ngày close từ 2018-02-12; xem §6(a).
- Vị thế: ON = 100 % BTC (spot), OFF = 100 % USDT lãi 0. Không đòn bẩy.
- Cài đặt: `t_states` trong `docs/result/t_oos/t_oos.py` là bản sao từng dòng của logic trên; V1 (§7) kiểm khớp số bb_core trên DEV.

## 3. Cửa sổ chấm, phí, chỉ số

- Moc t0 = close ngày 2017-12-31 (≡ 2018-01-01 00:00 UTC); equity tham chiếu 1,0 USDT tại t0. Tại t0 trạng thái khởi tạo ON rồi áp luật như mọi ngày
  (dùng close ≤ 2017-12-31). Chấm tới close ngày 2019-12-31 (730 bước ngày). Đây là cửa sổ OOS 2018-01-01→2019-12-31 (**primary**, quy ước "cold start ON
  tại đầu cửa sổ" giống bb_core, vì gốc cũng khởi tạo ON tại đầu cửa sổ DEV).
- Phí spot 0,10 %/chiều + trượt 0,05 %/chiều = 0,15 %/chiều tính trên notional, cho cả T và B&H. B&H mua tại close t0 (trả phí vào), giữ tới hết kỳ.
  Không thanh lý cuối kỳ (cả hai). OFF giữ USDT lãi 0.
- Chỉ số tính trên equity theo close ngày (chuỗi bắt đầu 1,0 tại t0 trước giao dịch): tổng lợi nhuận, CAGR = E_end^(365/730) − 1, maxDD (đỉnh-đáy trên chuỗi close
  ngày, kèm ngày đỉnh/đáy), số lần đổi trạng thái, số ngày OFF (đếm số ngày quyết định có trạng thái OFF sau quyết định, như `trend_off_days` của gốc),
  lợi nhuận từng đợt ON (net phí cả hai chiều; đợt còn mở cuối kỳ tính MTM net phí vào).

## 4. Tiêu chí chính (đều phải đạt, tại tham số trung tâm)

- **C1**: |maxDD(T)| ≤ 0,6 × |maxDD(B&H)| trên cửa sổ OOS.
- **C2**: tổng lợi nhuận T ≥ tổng lợi nhuận B&H trên cửa sổ OOS.
- **C3**: |maxDD(T)| ≤ 40 % tuyệt đối (không có chuỗi mất mát do whipsaw vượt 40 %), maxDD đo trên close ngày.

## 5. Độ bền (điều kiện phụ)

Lưới lân cận cố định: thr ∈ {0,65; 0,70; 0,75} × P ∈ {120; 180; 240} × R ∈ {20; 30; 40} = 27 ô (ô trung tâm 0,70/180/30 = T; kiểm assert trùng primary).
Mỗi ô chạy đúng cùng cửa sổ/phí/quy ước §2–§3, đánh giá C1 và C2 của ô đó (so với cùng B&H). **Điều kiện phụ: ≥ 19/27 ô (≥ 70 %, ceil 18,9) đạt cả C1 và C2.**
Lưới KHÔNG dùng để chọn tham số mới; chỉ báo cáo C3 từng ô (không vào điều kiện).

## 6. Verdict và báo cáo bắt buộc

**PASS (không bị bác bỏ)** nếu C1 ∧ C2 ∧ C3 ∧ điều kiện phụ; ngược lại **FAIL ⇒ T không được đưa vào v1.1**. Không có tiêu chí cứu nào khác.
Phần phụ dưới đây CHỈ báo cáo, không tham gia verdict (kể cả nếu khác verdict primary — khi đó ghi rõ là bất đồng, không đổi verdict):

(a) Cửa sổ phụ bắt đầu 2018-02-14 (khi đủ 180 ngày close): cắt từ chính đường primary, rebase tại close 2018-02-13 (T giữ vị thế kế thừa), cùng chỉ số + C1–C3.
(b) Warm-start: máy trạng thái chạy liên tục từ 2017-08-17 (ON khởi tạo ngày đầu dữ liệu, cửa sổ mở rộng), tính tiền từ t0 với vị thế kế thừa trạng thái tại t0.

Báo cáo bắt buộc (`docs/result/T_OOS.md`): bảng T vs B&H (tổng lợi nhuận, CAGR, maxDD, ngày đỉnh-đáy, số lần đổi, số ngày OFF, lợi nhuận từng đợt ON), danh sách ngày đổi trạng thái kèm giá,
bảng/heatmap 27 ô, và cùng chỉ số T vs B&H BTC-only trên DEV (2021-06-30→2025-12-30, từ `px_btceth.npz` USDT-M 1m→close ngày, **cùng phí 0,15 %/chiều**) để so độ nhất quán
(lưu ý: DEV dùng giá perp USDT-M, OOS dùng giá spot — ghi trong báo cáo).

## 7. Kiểm vệ sinh (bắt buộc trước khi báo)

- **V1**: tái tạo T trên DEV bằng `bb_core.load_px('D')` + `t_states` phải khớp BTC_BASE: **475 ngày OFF, 41 lần đổi trạng thái**; sai lệch phải giải thích. (Đã chạy thử trên DEV,
  chưa chạm dữ liệu 2018–2019: 475 / 41 khớp.)
- **V2**: không có dữ liệu ≥ 2020-01-01 (assert ngày max < 2020-01-01; chỉ tải tháng ≤ 2019-12; DEV `px_btceth.npz` bắt đầu 2021-01-01).
- **V3**: không look-ahead: cắt dữ liệu sau mốc và thay giá sau mốc bằng random walk ⇒ state + equity ≤ mốc không đổi (3 mốc OOS: 2018-04-30, 2018-12-31, 2019-06-30; 2 mốc DEV).
- **Dữ liệu**: sha256 từng file theo `.CHECKSUM` Vision phải khớp; đủ 867 ngày 2017-08-17→2019-12-31, không trùng. Ngày thiếu (nếu có) được ffill close ngày trước (ngày phẳng) và ghi lại; > 3 ngày thiếu
  ⇒ dừng, báo MASTER, không tính.
- Lỗi crash của script (không đổi logic) có thể sửa sau commit này nhưng phải ghi trong báo cáo; mọi thay đổi logic/tham số bị cấm.

## 8. Mã

Commit cùng prereg (chưa chạy trên dữ liệu 2018–2019): `docs/result/t_oos/t_oos_data.py` (sha256 d129560e7dae6061668feef321bcdded1cadd1007aedcf6661783e6974da9293),
`docs/result/t_oos/t_oos.py` (sha256 d36af81313e95829b285064c03995e8b81bb79ad16565db30cc60a14a560cfaf).
