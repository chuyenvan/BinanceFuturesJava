# F2_RESULT — Conditional exit: NULL

Pre-reg: `docs/prereg/PREREG_F2.md` (commit `a4b3b05`, viết + commit TRƯỚC run đầu).
Đo offline: `docs/experiment/F2_COND_EXIT_MEASURE.md` (commit `7bf80d3`).
3 run, 1 dataset dùng chung (`/home/ubuntu/wfo_ds_clean`, tái dùng của F1), không có run thứ 4.

## 1. Parity gate — PASS (byte-identical)

| kiểm | neo `C2b` | `F2_parity` | |
|---|---|---|---|
| md5 `printDone.csv` | `8f7afdfb27b15f5b6d4c886700def93c` | `8f7afdfb27b15f5b6d4c886700def93c` | PASS |
| số lệnh | 970 | 970 | PASS |
| equity | `b:60390` | `b:60390` | PASS |

Jar build lại (thêm 2 param) + dataset của F1 vẫn cho byte-identical ⇒ mặc định TẮT đúng
là no-op và batch hợp lệ. Cả 3 run trả `rc=1` — theo runbook đây không phải fail.

## 2. Cơ chế CÓ tác dụng và khớp đo offline

| | cond-exit (<168h) | time-stop 168h còn lại | offline dự báo cắt |
|---|---|---|---|
| `F2_parity` | 3 | 144 | — |
| `F2_a` (72h × 0.05) | **148** | 43 | 146 (107 loser + 39 winner) |
| `F2_b` (72h × 0.04) | **109** | 66 | 115 (86 loser + 29 winner) |

Đo offline trên nhãn dự báo gần đúng số lệnh bị cắt (148 vs 146; 109 vs 115). Phép đo
Giai đoạn 1 là công cụ dùng được; sai ở phần diễn giải hệ quả, không ở phần đếm.

`mean(profit | STOP_LOSS_DONE)` cải thiện mạnh: −18.90% → **−13.95%** (`F2_a`) / **−15.16%** (`F2_b`).
Đúng chiều giả thuyết. Nhưng đó không phải tiêu chí đã đăng ký.

## 3. PRIMARY — 2/3 FAIL ở CẢ HAI ô

| tiêu chí | ngưỡng | `C2b` | `F2_a` | `F2_b` |
|---|---|---|---|---|
| `TSloss%` | phải GIẢM | 15.15 | **19.04 ✗** | **17.57 ✗** |
| `mean(profit\|STOP_MARKET_DONE)` | giảm ≤ 0.3pp | 7.4760 | 7.4420 (−0.034pp) ✓ | 7.4638 (−0.012pp) ✓ |
| `win%` | phải TĂNG | 85.26 | **81.66 ✗** | **82.73 ✗** |

`TSloss%` và `win%` FAIL ở cả hai ô. Pre-reg mục 2 đã ghi TRƯỚC khi chạy rằng hai chỉ số
này lệch cơ học vì lệnh bị cond-exit mang cùng status `STOP_LOSS_DONE` — nhưng độ lệch
thực tế (+3.9pp `TSloss%`, −3.6pp `win%` ở `F2_a`) lớn hơn phần "cắt oan" thuần tuý:
tổng lệnh chỉ tăng 970 → 1,003 (+3.4%), tức **margin giải phóng KHÔNG quay vòng đủ nhanh**
để pha loãng mẫu số. Đó chính là kênh mà giả thuyết đặt cược vào, và nó yếu.

## 4. Ràng buộc CỨNG — FAIL ở underwater

| ràng buộc | ngưỡng | `C2b` | `F2_a` | `F2_b` |
|---|---|---|---|---|
| maxDD | ≤ 15% | −13.1% | −11.2% ✓ | −11.1% ✓ |
| underwater dài nhất | ≤ 120 ngày | 93 | **156 ✗** | **156 ✗** |
| năm âm | không | không | không ✓ | không ✓ |
| quý < −5% | không | không | −3.5% (2022Q1) ✓ | −2.5% (2022Q1) ✓ |
| tổng lệnh | ≥ 600 | 970 | 1,003 ✓ | 996 ✓ |

Underwater 156 ngày = **+68% so với 93 ngày** của baseline, ở cả hai ô. Cùng con số 156
với `X72` của E1 — cắt sớm (dù có điều kiện hay phẳng) đều kéo dài chuỗi underwater vì
tiền được thả ra đúng lúc thị trường không có gì để mua.

## 5. PHÁN QUYẾT

Quy tắc pre-reg mục 9: chọn ô thoả TOÀN BỘ PRIMARY và TOÀN BỘ ràng buộc cứng.

> ## NULL — không ô nào thoả. ĐÓNG HƯỚNG conditional exit.

`F2_a` và `F2_b` đều FAIL 2/3 PRIMARY và FAIL ràng buộc underwater. Không có ô thứ ba để
thử: quota 3/3 đã dùng, và pre-reg cấm mở rộng lưới sau khi thấy số.

**Điều học được (không dùng để đảo phán quyết):** giả thuyết "chất lượng lệnh thắng là
hằng số, biến duy nhất là coin có chạy hay không" ĐÚNG ở phần chẩn đoán — cắt trúng nhóm
chết (`mean(profit|SL)` −18.90 → −13.95), gần như không đụng chất lượng lệnh thắng
(`mean(profit|SM)` −0.034pp). Nhưng đường truyền giá trị mà nó giả định — **margin giải
phóng sớm được tái triển khai** — không tồn tại ở mức đủ lớn: tổng lệnh chỉ +3.4%. Đây là
lần thứ hai (sau F1) một hướng chết vì kênh tái triển khai vốn yếu hơn giả định.

## 6. Equity — KHÔNG PHẢI TIÊU CHÍ

Mục này chỉ để báo cáo. `sd(ΔCAGR)` exit params = 2.57pp, `E[max nhiễu]` N=50 = +7.2pp,
DEV đã ~125 run ⇒ không được dùng để chọn.

| tag | equity cuối | tổng ret | sumPNL | medP | meanP |
|---|---|---|---|---|---|
| `C2b` / `F2_parity` | 60,390 | +72.5% | 25,391 | 5.50 | 3.48 |
| `F2_a` | 61,851 | +76.7% | 26,852 | 5.50 | 3.37 |
| `F2_b` | 62,317 | +78.0% | 27,317 | 5.50 | 3.49 |

Cả hai ô có equity CAO HƠN baseline (+4.2pp / +5.5pp tổng ret) và maxDD THẤP HƠN. Biên độ
này nằm gọn trong nhiễu đã đo (2.57pp cho MỘT thay đổi exit param) và **equity đi ngược
phán quyết** — đúng tình huống luật cứng #3 được viết ra để xử lý. Phán quyết vẫn là NULL.
`medP` = 5.50 không đổi ở cả 3 run, lặp lại đúng phát hiện của F1.

## 7. Truy nguyên

| tag | profile | md5 `printDone.csv` | n | equity |
|---|---|---|---|---|
| `C2b` (neo) | `c2b_min.properties` | `8f7afdfb27b15f5b6d4c886700def93c` | 970 | 60,390 |
| `F2_parity` | `c2b_min.properties` | `8f7afdfb27b15f5b6d4c886700def93c` | 970 | 60,390 |
| `F2_a` | `f2_a.properties` (72 / 0.05) | `8106e8632dcf35aa3d084f0d330d45f3` | 1,003 | 61,851 |
| `F2_b` | `f2_b.properties` (72 / 0.04) | `292ee5d18b6356acbd59a9e6a3ff67ff` | 996 | 62,317 |

Build: `PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH mvn -DskipTests package`
(BUILD SUCCESS 22.8s; `tools/check_cfg_gateway.sh` OK). Dataset `/home/ubuntu/wfo_ds_clean`
**tái dùng của F1, KHÔNG build mới** (tiết kiệm 1.8G trên đĩa còn 16G) và **KHÔNG xoá** —
nó có trước F2. Code: 2 param `SIM_COND_EXIT_HOURS` / `SIM_COND_EXIT_MIN_FAV` giữ nguyên
trong repo, mặc định 0 = TẮT = byte-identical; profile `f2_a`/`f2_b` giữ lại để tái lập.
