# PLAN REX — Rank → Entry → eXit: hệ long mới, làm từng bước (MASTER 2026-10-16)

**Yêu cầu của owner (10-16 khuya).** Bỏ lối ước tính sơ sài, đào kỹ từng bước:
1. chọn coin tốt bằng model và xếp hạng (top k);
2. tìm thời điểm vào;
3. tìm cách thoát.

Mục tiêu là một hệ **mới**, không phải crash-buy: lãi có thể ít nhưng **ổn định**.

## 0. Rủi ro phương pháp (đọc trước)

1. **Tối ưu nối tiếp là bẫy nhân overfit.** Mỗi bước tune trên cùng lịch sử sẽ thổi phồng kết quả, và các bước cộng dồn vào nhau. Cách chặn:
   - mỗi bước có pre-reg riêng, commit trước khi chạy;
   - bước xong thì ĐÓNG BĂNG đầu ra, bước sau không được sửa bước trước;
   - lựa chọn chỉ làm trong walk-forward DEV, VAL dùng 1 lần cho mỗi bước, HO dùng 1 lần duy nhất ở cuối;
   - mỗi bước chỉ có một danh sách biến thể nhỏ (≤ 5–6), khai trước.
2. **Long-only alt phải vượt cả beta lẫn việc alt chảy máu so với BTC** (bài học T2-MOM). PnL ≈ phơi nhiễm thị trường × lợi suất thị trường + alpha chọn coin. Vì vậy:
   - Bước 1 đo alpha **tương đối so với universe**.
   - Bước 2 có một nhánh riêng cho "khi nào nên có mặt trên thị trường" (regime).
   - Không trộn hai thứ này vào cùng một con số.
3. **Không còn holdout sạch tuyệt đối.**
   - 2025 đã bị nhìn qua các anomaly đơn giản ở SCREEN_WIDE, nhưng chưa có model nào chạm vào.
   - 2026 là holdout của hệ hiện tại, đã dùng, nhưng hệ mới chưa chạm.
   - Trọng tài cuối là forward paper.
4. **Không ước tính khi có thể đo.** Vào và thoát ở Bước 2–3 đi bằng đường giá 1m thật (`~/vz_e1/raw/kline1m-*`, 2021-12 → 2025-12; 2026 lấy từ Kaggle). Không dùng high/low ngày để đoán thứ tự khớp.

## 1. Chia thời gian (cố định)

| Đoạn | Kỳ | Vai trò |
|---|---|---|
| Warm-up | 2021-01 → 2021-12 | Chỉ tính feature và làm dữ liệu train sớm. Không đánh giá |
| DEV | 2022-01-01 → 2024-12-31 | Walk-forward: train mở rộng, retrain hằng tháng, purge = horizon + 1 ngày. Mọi lựa chọn làm ở đây |
| VAL | 2025-01-01 → 2025-12-31 | Kiểm 1 lần cho mỗi bước, chỉ xác nhận dấu và độ lớn, không chọn |
| HO | 2026-01-01 → 2026-09-30 | Chạy 1 lần toàn hệ đã đóng băng |
| Forward | từ 2026-10 | Paper ≥ 8 tuần |

2020 vẫn SEALED.

## 2. Các bước

### Bước 0 — Nền dữ liệu (`PREREG_REX_S0`)
- **Panel ngày.** Mốc quyết định là 00:00 UTC ngày d+1, dùng dữ liệu tới close ngày d.
  - Universe point-in-time: perp USDT qv30 ≥ 20M, niêm yết ≥ 60 ngày, không phải stablecoin, CÓ cả coin đã delist.
- **Target** tính từ open d+1 (≈ close d):
  - lợi suất h = 1, 3, 7 ngày;
  - excess so với median universe;
  - MFE/MAE trong h ngày, đo từ 1m khi có, nếu không thì từ ngày (chỉ để mô tả).
- **Feature** chia 8 họ, mỗi họ chuẩn hoá rank theo mặt cắt từng ngày:
  - (a) momentum đa kỳ 1/3/7/14/28/56/90 ngày, cùng residual momentum so với BTC;
  - (b) vol và range: vol thực 7/30, ATR%, downside vol;
  - (c) hình dạng phân phối: skew, max/min ngày 30, tỷ lệ ngày tăng;
  - (d) volume và thanh khoản: qv, turnover, sốc volume 3/7 so với 30/90, Amihud;
  - (e) vị trí giá: khoảng cách tới max/min 7/30/90/365, các tỷ số MA;
  - (f) dòng lệnh taker: tỷ lệ taker buy 1/3/7 ngày và độ thay đổi;
  - (g) phái sinh: funding (mức, Δ, z-score), OI (Δ 1/3/7 ngày, OI/qv), long/short ratio top trader và toàn thị trường, có từ 2021-12;
  - (h) bối cảnh, giống nhau cho mọi coin: xu hướng và vol của BTC, breadth (% coin trên MA), dispersion. Họ (h) chỉ dùng ở Bước 2a, không dùng để xếp hạng.
- **Kiểm dữ liệu:**
  - assert mọi feature có timestamp ≤ mốc quyết định;
  - độ phủ theo năm;
  - đối chiếu ngẫu nhiên giá trị feature với tính tay;
  - target của coin delist dùng giá cuối.

### Bước 1 — Selector: xếp hạng coin (`PREREG_REX_S1`)
- **Baseline:** IC rank từng feature đơn, theo năm. Biết feature nào có tín hiệu ổn định thì mới đưa vào model.
- **Model:**
  - LightGBM regression trên target excess đã rank hoá, với h chính khai trước;
  - walk-forward retrain hằng tháng, purge h + 1 ngày;
  - siêu tham số bảo thủ, cố định trước (không tune), 5 seed lấy trung bình.
  - Biến thể khai trước: chỉ họ a–e (giá), thêm f, thêm g; các h = 1/3/7.
- **Thước đo:**
  - IC ngày (mean, t-stat Newey-West), % tháng có IC > 0, IC theo năm;
  - lợi suất theo decile, kiểm tính đơn điệu;
  - excess của top-k (k = 5/10/20) so với universe và so với BTC, sau chi phí;
  - turnover.
- **Gate GO** (đặt cụ thể trong pre-reg):
  - IC DEV dương và có ý nghĩa thống kê, cả 3 năm DEV đều dương;
  - VAL 2025 IC > 0;
  - top-decile excess ròng > 0 ở cả DEV và VAL;
  - model phải hơn feature đơn tốt nhất.
- **Đầu ra đóng băng:** score mỗi coin mỗi ngày, dạng walk-forward OOS.

### Bước 2 — Vào lệnh (`PREREG_REX_S2`), chỉ trên tập top-k của Bước 1
- **2a — Regime:** khi nào nên phơi nhiễm long. ≤ 5 luật khai trước dựa trên họ (h). Đo trên danh mục top-k: vào luôn so với có lọc.
- **2b — Thời điểm vào theo từng coin, dùng 1m:**
  - vào ngay lúc 00:05 UTC;
  - đặt limit pullback −x % trong 24h, nếu không khớp thì bỏ;
  - chờ xác nhận breakout trong ngày;
  - vào dần theo VWAP.
  - Phải tính cả chi phí cơ hội của lệnh không khớp.
- **Gate:** so với vào ngay, cải thiện Sharpe/Calmar với block-bootstrap CI không chứa 0 trên DEV, và cùng dấu trên VAL.

### Bước 3 — Thoát lệnh (`PREREG_REX_S3`), dùng 1m
- **Biến thể:**
  - giữ cố định h;
  - thoát khi rank tụt khỏi top-m (có hysteresis);
  - trailing theo ATR;
  - TP/SL scale theo vol;
  - time-stop kết hợp TP.
- **Gate:** như Bước 2.

### Bước 4 — Danh mục và rủi ro (`PREREG_REX_S4`)
- k, trọng số (đều hoặc nghịch vol), trần gross, trần mỗi coin ≤ x % ADV.
- Chi phí: taker 0,05 % + slippage theo √participation, funding thật.
- Tuỳ chọn hedge short BTC (owner đã cho phép).
- **Chạy HO 2026 một lần**, tiêu chí khai trước: Sharpe, maxDD, độ ổn định theo tháng, correlation với crash-buy.
- Sau đó forward paper.

## 3. Nguyên tắc vận hành
- Mỗi bước: pre-reg → commit → chạy → kiểm dữ liệu → result → ledger → memory.
- Có FAIL thì dừng ở bước đó. Không "cứu" bằng cách đổi tham số sau khi đã thấy kết quả.
- Nếu Bước 1 FAIL (không có selector ổn định), các bước sau mất nền và không làm tiếp. Lúc đó báo owner ngay.
- Code: `research/rex/`. Dữ liệu: `~/claude_master/rex/`. Ghi log bằng `logging`, không dùng print.
