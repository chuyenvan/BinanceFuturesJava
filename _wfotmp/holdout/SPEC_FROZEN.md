# SPEC ĐÓNG BĂNG — Holdout ngoài vũ trụ

**Ngày viết:** 2026-08-30
**Trạng thái:** DỰ THẢO — chờ Uni Claude duyệt. Sau khi duyệt thì KHÓA, không sửa.
**Nguyên tắc:** chạy ĐÚNG MỘT LẦN. Nhìn kết quả rồi sửa spec = holdout chết.

---

## 0. Câu hỏi cần trả lời

> Quy tắc `ensemble trend + vol targeting` phát hiện trên BTC/ETH (2017–2026, ~67 cược
> độc lập, Sharpe 1,22, p<0,001 so với null hoán vị) là **quy luật cấu trúc** hay là
> **may mắn của một mẫu nhỏ**?

Kiểm bằng cách áp y nguyên, không chỉnh một chữ, lên 40 tài sản truyền thống mà
người phân tích CHƯA TỪNG chạy chiến lược lên (dữ liệu mới tải 2026-08-30, chỉ mới
kiểm tra chất lượng thô, chưa tính một chỉ số hiệu suất nào).

---

## 1. Thuật toán — không còn ô trống

Áp ĐỘC LẬP cho từng tài sản. Không có tầng chọn universe (tradfi không có
xếp hạng thanh khoản tương đương crypto).

```
Với mỗi tài sản, mỗi ngày giao dịch t (dùng giá đóng cửa ĐIỀU CHỈNH):

  B1. TÍN HIỆU TREND
      sig[t] = ( 1[close[t] > SMA(close,50)[t]]
               + 1[close[t] > SMA(close,100)[t]]
               + 1[close[t] > SMA(close,200)[t]] ) / 3
      -> nhận giá trị 0, 1/3, 2/3, 1
      SMA yêu cầu min_periods = đúng độ dài cửa sổ (không tính thiếu)

  B2. ĐỘ LỚN THEO BIẾN ĐỘNG
      rv[t]   = stdev(ret, 30 ngày)[t] * sqrt(252)      # 252, KHÔNG phải 365
      size[t] = min( 0.40 / rv[t] , 1.00 )

  B3. MỤC TIÊU
      raw[t] = sig[t] * size[t]

  B4. LỌC LƯỚI
      nếu |raw[t] - đang_giữ| / max(đang_giữ, 1e-9) > 0.20  -> đổi sang raw[t]
      ngược lại -> giữ nguyên
      (đang_giữ == 0 hoặc raw[t] == 0 thì luôn đổi)

  B5. ĐỘ TRỄ THỰC THI
      pos[t] = held[t-1]          # exec_lag = 1 ngày
      Lãi ngày t = pos[t] * ret[t]
      Phí ngày t = |pos[t] - pos[t-1]| * FEE

  B6. ĐIỀU KIỆN LỊCH SỬ
      pos[t] = 0 nếu chưa có đủ 200 nến tính đến t-1
```

**LONG-ONLY. Không short. Không đòn bẩy (size ≤ 1,00). Không stop loss.
Không take profit.** Phần vốn không vào lệnh nằm tiền mặt, lãi suất = 0.

### Tham số — KHÓA, không quét, không tối ưu

| Tham số | Giá trị | Nguồn |
|---|---|---|
| `ma_lbs` | (50, 100, 200) ngày | y hệt crypto |
| `target_vol` | 0,40/năm | y hệt crypto |
| `vol_win` | 30 ngày | y hệt crypto |
| `max_size` | 1,00 | y hệt crypto |
| `band` | 0,20 | y hệt crypto |
| `exec_lag` | 1 ngày | y hệt crypto |
| `min_hist` | 200 nến | y hệt crypto |
| `bars_per_year` | **252** | đổi từ 365 — tradfi nghỉ cuối tuần |
| `FEE` | **0,05%** mỗi đơn vị turnover | mới; hợp đồng tương lai/ETF thanh khoản cao |

Chỉ **một** thay đổi so với crypto: `365 → 252` (bắt buộc, vì lịch giao dịch khác),
và mức phí thấp hơn (đúng thực tế tradfi). Mọi thứ khác giữ nguyên tuyệt đối.

---

## 2. Dữ liệu

Nguồn: Yahoo Finance chart API, tải 2026-08-30, giá đóng cửa **đã điều chỉnh**
(quan trọng với ETF trái phiếu — phần lớn lợi nhuận là coupon).

40 tài sản / 4 lớp / 309.635 nến / ~1.229 năm-tài-sản. Danh sách đầy đủ ở
`inventory.csv`.

### Xử lý dữ liệu — quy tắc cố định trước

- Bỏ nến có giá ≤ 0 hoặc thiếu.
- **KHÔNG** áp bộ lọc "nhảy >200%/ngày" như bên crypto: tradfi có những cú
  sốc thật (Black Monday 1987 −20,5% ở S&P, dầu 2020) và loại chúng là gian lận.
- **Quy tắc lỗ hổng (cơ học, chốt trước khi chạy):** với mỗi tài sản, nếu tồn tại
  lỗ hổng > 30 ngày lịch giữa hai nến liên tiếp thì **cắt bỏ toàn bộ phần trước
  lỗ hổng cuối cùng đó**, chỉ giữ đoạn liên tục về sau. Áp đồng nhất cho cả 40 mã.
  Hiện chỉ ảnh hưởng 2 mã:
  - `SEK=X` — lỗ hổng 215 ngày (2003-04-30 → 2003-12-01, thiếu dữ liệu) → giữ từ 2003-12-01
  - `PL=F` — lỗ hổng 78 ngày (2004-04-27 → 2004-07-14) → giữ từ 2004-07-14.
    Việc này đồng thời loại bỏ cú −43,5% ngày 2000-04-26 (775 → 438), gần như
    chắc chắn là lỗi nối hợp đồng chứ không phải biến động thật.
- Đã đối chiếu các cú biến động cực đại còn lại với lịch sử có thật, đều ĐÚNG,
  nên **giữ nguyên**: S&P 500 −20,5% ngày 1987-10-19 (Black Monday);
  Hang Seng −33,3% ngày 1987-10-26 (mở lại sau 4 ngày đóng cửa);
  WTI −45,2% ngày 2020-04-21 (tuần giá dầu âm);
  S&P 500 nghỉ 12 ngày 1933-03 (Bank Holiday của Roosevelt).
- Mỗi tài sản dùng toàn bộ lịch sử sẵn có, không cắt ngắn cho khớp nhau.

---

## 3. Cách đo

Mỗi tài sản: mỗi $1.000 độc lập.

- `Sharpe_strat[i]`, `Sharpe_hold[i]` — mua-và-giữ là đối chứng
- `maxDD_strat[i]`, `maxDD_hold[i]`
- Thống kê chính: **trung bình Sharpe qua 40 tài sản**
- Phụ: trung vị, tách theo lớp tài sản, danh mục equal-weight

### Kiểm định ý nghĩa

**Null = xoay vòng chuỗi vị thế, CÙNG một số ngày cho TẤT CẢ tài sản**
(giữ tương quan chéo — chính là null bảo thủ đã dùng ở crypto).
Giữ nguyên exposure, turnover, độ dài nắm giữ; chỉ phá liên kết với giá.
**1.000 lần xoay.** p-value = tỷ lệ null ≥ quan sát.

---

## 4. TIÊU CHÍ SỐNG/CHẾT — viết TRƯỚC khi chạy

### ĐẠT — cần THỎA MÃN CẢ 4

| # | Điều kiện | Ngưỡng |
|---|---|---|
| 1 | Trung bình Sharpe chiến lược > trung bình Sharpe mua-giữ | hiệu > 0 |
| 2 | p-value hoán vị trên trung bình Sharpe | **p < 0,01** |
| 3 | Số lớp tài sản mà Sharpe chiến lược > null trung bình | **≥ 3 / 4 lớp** |
| 4 | Cải thiện maxDD trung bình (tương đối) | **≥ 30%** |

→ Trend following là quy luật cấu trúc. Kết quả crypto là một trường hợp của nó.
Tiếp tục sang forward test và triển khai.

### CHẾT — nếu (2) thất bại

`p ≥ 0,05` → **Bỏ hướng trend following làm lõi.** Kết quả crypto nhiều khả năng
là nhiễu của mẫu nhỏ. Không tinh chỉnh, không thử biến thể, không tìm lý do
biện hộ cho từng lớp tài sản.

### TRUNG GIAN — `0,01 ≤ p < 0,05` hoặc thiếu 1 trong 3 điều kiện còn lại

→ Edge có tồn tại nhưng **yếu hơn kết quả crypto gợi ý**. Hạ kỳ vọng xuống,
lấy Sharpe quan sát ở tradfi làm mốc thay cho con số crypto. Không bỏ, nhưng
cũng không được dùng lại con số 1,22.

---

## 5. Kỳ vọng ghi trước (để không biện hộ sau)

Ghi ra đây để sau khi thấy kết quả không thể nói "tôi đã biết trước":

- **Chỉ số cổ phiếu:** kỳ vọng ĐẠT. Có drift dương + xu hướng kéo dài.
- **Hàng hoá:** kỳ vọng ĐẠT, mạnh nhất. Đây là sân nhà kinh điển của trend following.
- **Trái phiếu:** kỳ vọng ĐẠT nhưng yếu. Bull 40 năm rồi sập 2022 — có xu hướng dài.
- **Tiền tệ:** kỳ vọng YẾU NHẤT, có thể trượt. Long-only trên FX gần như vô nghĩa
  vì cặp tiền không có drift dương tự nhiên. **Đây là điểm yếu đã biết TRƯỚC của
  bài test, không phải cái cớ dựng sau.** Vì vậy tiêu chí (3) chỉ đòi 3/4 lớp.
- **Sharpe trung bình dự đoán:** 0,3 – 0,6. Nếu ra > 1,0 thì phải nghi ngờ lỗi,
  không phải mừng.

---

## 6. Quy trình chạy

1. Uni Claude duyệt spec này.
2. Băm SHA-256 spec + `sim/engine.py`, ghi lại.
3. Chạy MỘT LẦN.
4. Đối chiếu tiêu chí ở mục 4. Chấp nhận kết quả.
5. Không chạy lại với tham số khác. Nếu muốn thử biến thể → phải là spec mới,
   trên dữ liệu khác, và ghi rõ đây là lần nhìn thứ hai.

---

## 7. Điều spec này KHÔNG chứng minh được

Kể cả khi ĐẠT hết 4 tiêu chí:

- Không chứng minh chiến lược lãi trên **crypto trong tương lai**.
- Không chứng minh nó hơn **mua-và-giữ BTC** (bootstrap crypto cho KTC95%
  [−0,23; +0,97], vẫn chứa 0 — kết quả này không đụng tới điều đó).
- Không loại được rủi ro vận hành: slippage thật, lệch giá, lỗi dữ liệu live.
- Không nói gì về quy mô vốn hay sức chứa.

Nó chỉ trả lời đúng một câu: **cơ chế này có thật hay không.**
