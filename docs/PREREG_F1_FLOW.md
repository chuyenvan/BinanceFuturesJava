# PREREG_F1_FLOW — nới dòng cơ hội ở TỔNG EXPOSURE KHÔNG ĐỔI

Pre-registration. Viết và commit TRƯỚC run đầu tiên. Không sửa sau khi thấy số.

## 0. Kiểm khả thi (đã chạy TRƯỚC khi viết file này)

Hai param phải điều khiển được QUA PROFILE (không qua env — có `TRADING_PROFILE`
thì env tiền tố `SIM_` làm `Cfg` fail-fast `exit 2`):

- `SELECTOR_RANK_TOPK` — `Configs.java:341`, `Cfg.get(...)`, `static final int`. ĐỌC ĐƯỢC.
- `SIM_F_BASE` — `Configs.java:464`, `Cfg.get(...)` trong static block KHÔNG có guard
  (chỉ try/catch). Commit `f2ada23` mở override. ĐỌC ĐƯỢC.

Xác nhận thực nghiệm bằng `DumpConfig` trên 2 profile thử:

| profile | PROFILE_HASH | F_BASE | SELECTOR_RANK_TOPK | audit |
|---|---|---|---|---|
| `t_parity` (K=8, F=0.03) | `137557a8ecd2df6d` | 0.0300 | 8 | OK, 17/17 key được đọc |
| `t_k16` (K=16, F=0.015) | `fd30b1a83dfe83de` | 0.0150 | 16 | OK, 17/17 key được đọc |

`audit OK` = `SIM_F_BASE` thật sự bị code đọc, không phải key gõ sai rồi âm thầm
về default. => ĐỦ ĐIỀU KIỆN chạy.

## 1. Giả thuyết cơ học

Hệ **thiếu dòng cơ hội, không thiếu edge**. Bằng chứng:

- trung bình **1.83** vị thế mở;
- **62.5%** số giờ không giữ gì;
- `NO_BUDGET` = **0** dòng — budget CHƯA BAO GIỜ bind;
- margin tối đa **1,575** = **4.5%** equity ⇒ trung bình chỉ **~8%** vốn được triển khai.

Mọi lần nới gate trước đây đều làm maxDD xấu đi (`H1a_mom006` → **−21.1%**,
`H1b_rmax30` → **−44.3%**) vì size mỗi vị thế giữ NGUYÊN, nên nhiều vị thế hơn =
tổng exposure lớn hơn. **Chưa ai thử nới flow trong khi giữ tổng exposure không đổi.**

## 2. Dự đoán

Ở tổng exposure không đổi, tăng số vị thế đồng thời làm giảm phương sai danh mục
bằng đa dạng hoá: `sd(daily return)` giảm, maxDD giảm, underwater giảm, mean return
gần như không đổi ⇒ Sharpe tăng.

## 3. Runs: ĐÚNG 4, không hơn

Nền C2b (`profiles/c2b_min.properties`), **1 dataset build dùng chung**.
Bù `F_BASE` tỉ lệ nghịch với K để tích `K × F_BASE` giữ nguyên **0.24**:

| Tag | SELECTOR_RANK_TOPK | SIM_F_BASE | K×F_BASE |
|---|---|---|---|
| `F1_parity` | 8 | 0.03 | 0.24 |
| `F1_k16` | 16 | 0.015 | 0.24 |
| `F1_k24` | 24 | 0.010 | 0.24 |
| `F1_k32` | 32 | 0.0075 | 0.24 |

Mỗi biến thể là một **profile copy** khác `c2b_min.properties` đúng 2 dòng
(`SELECTOR_RANK_TOPK`, `SIM_F_BASE`). Không đổi bất kỳ param nào khác.

## 4. Tiêu chí PRIMARY — `sd(daily equity return)`

Tính từ chuỗi equity cuối ngày trong `logs/sim.out`, regex

    Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)

với `equity = b + unP`. ~**900** quan sát ngày ⇒ **n_eff lớn, khác hẳn terminal equity**.

Dự đoán: **giảm đơn điệu theo K**.
Báo kèm `Sharpe = mean(daily ret) / sd(daily ret) × sqrt(365)`.

## 5. SANITY (không phải tiêu chí)

Số vị thế đồng thời trung bình phải **TĂNG** theo K.
Nếu không tăng ⇒ gate mới là ràng buộc bind chứ không phải K; ghi rõ như vậy,
phán quyết là **"K không phải đòn bẩy"**, đóng hướng.

## 6. KIỂM SOÁT C1 — bắt buộc, quyết định TÍNH HỢP LỆ

Đo vốn triển khai thực tế: mỗi run tính `mean(tổng margin đang mở) / equity` theo
TỪNG NGÀY, rồi lấy trung bình. Con số này phải nằm trong **±20%** so với `F1_parity`.

Nếu lệch quá ⇒ **phép bù thất bại, so sánh KHÔNG hợp lệ**; báo cáo đúng như vậy và
**KHÔNG phán quyết**.

Cách tính: từ `printDone.csv` mỗi lệnh có `start`, `end`, `margin` — dựng chuỗi ngày
rồi cộng margin của các lệnh đang mở.

## 7. Ràng buộc CỨNG (vi phạm là LOẠI, bất kể mọi thứ khác)

- maxDD ≤ **15%**
- underwater ≤ **120 ngày**
- **không năm nào âm**
- **không quý nào < −5%**

## 8. Equity KHÔNG phải tiêu chí

Báo cáo riêng, dán nhãn. Lý do: `sd(ΔCAGR)` = **2.57pp**; `E[max nhiễu]` với N=50 =
**+7.2pp**; DEV đã chạy ~**125** run. `sd(daily return)` thì ngược lại — n≈900,
đo được thật.

## 9. Parity gate

`F1_parity` phải **byte-identical** `/home/ubuntu/java/devrun/C2b`:
md5 `printDone.csv` = `8f7afdfb27b15f5b6d4c886700def93c`, `b:60390`, **970** lệnh.

Không pass ⇒ **DỪNG cả batch**.

## 10. Quy tắc quyết định (chốt TRƯỚC khi chạy)

1. Chọn K có `sd(daily return)` **THẤP NHẤT** trong số các run thoả **C1** + **toàn bộ
   ràng buộc cứng** (mục 7).
2. Nếu `sd` **không giảm theo K** ⇒ giả thuyết đa dạng hoá **SAI**: ghi **null**,
   đóng hướng, **KHÔNG thử K khác**.
3. Nếu **K lớn nhất (32) thắng** ⇒ ghi rõ đây là **mút của grid**, cần một pre-reg
   MỚI để đi xa hơn. Không tự nới trong batch này.

## 11. Rủi ro đã biết của thiết kế này

- `docs/AGENT_RUNBOOK.md` mục 4 kết luận **sizing (F_BASE/U_MAX/DCA_GRID_SCALE)
  KHÔNG đo được trên DEV**. Ở đây `F_BASE` KHÔNG phải đối tượng nghiên cứu, chỉ là
  **biến bù** để giữ tổng exposure cố định; đối tượng là K. C1 là thứ kiểm tra phép
  bù có thật sự giữ exposure hay không — nếu C1 fail thì toàn bộ so sánh vô hiệu.
- `K × F_BASE` là hằng số chỉ đúng NẾU budget tuyến tính theo `F_BASE` và số vị thế
  tuyến tính theo K. Throttle `(1 − U/U_MAX)` là phi tuyến ⇒ C1 có thể lệch. Đây
  chính là lý do C1 là gate hợp lệ, không phải phần trang trí.
- K=8 (sim) vs K=5 (live) chưa đóng — kết quả K lớn càng làm khoảng cách sim/live rộng ra.
