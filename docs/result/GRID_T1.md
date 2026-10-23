# RESULT GRID_T1 — grid trading có cửa không: kiểm tiền đề VR + G-RANGE/G-DYN có luật + control random-walk

- **Ngày:** 2026-10-23. **Repo:** `~/claude_master/vz_e1_wt`, nhánh `research/vz-e1`.
- **Prereg:** `docs/prereg/PREREG_GRID_T1.md`, commit **1944463f**, sha256 **75e6d1089f157858bdca96227de88630739c79558af487143b4a351161f85488**. Prereg commit TRƯỚC khi tính PnL.
- **Code:** `research/grid_t1/` — `g_cache.py`, `g_fund.py`, `g_vr.py`, `grid_engine.c` (+ `g_sim.py` ctypes), `g_run.py`, `g_report.py`, `g_validate.py`.
- **Output:** `docs/result/grid_t1/{vr.json,grid_t1_metrics.json,validate.json}`.
- **Kỳ:** E = 2022-01-01 → 2023-12-31; C = 2024-01-01 → 2025-12-31 (UTC). 2021-12 chỉ warmup. **Không đụng 2026, không đụng 2020.**

## 0. TL;DR — verdict: **NO-GO, đóng họ grid**

1. **Tiền đề FAIL ở C.** E có 56,9 % tài sản VR(1h) < 1 có ý nghĩa (z < −1,96); **C chỉ 6,8 %** (VR median vẫn 0,86 nhưng không significant vì vol clustering). Grid chỉ có cơ sở nếu mean-revert ở thang bước lưới — điều đó không tái lập được ngoài mẫu.
2. **G-RANGE lỗ ròng** cả hai kỳ: Sharpe −2,26 (E) / −1,41 (C), CAGR −1,6 % / −1,8 %, tệ hơn **90 % / 80 %** đường control random-walk. Nguyên nhân cơ học: 99,7 % lệnh stop đến từ ADX(4h) ≥ 20, lưới chỉ **bật 8,7 % thời gian**, mỗi episode ~3 giờ.
3. **G-DYN (paper 2506.11921) không có edge**: Sharpe 0,26 (E) / 0,22 (C), CAGR +1,6 % / −0,9 %, maxDD −35 % / −30 %, **không vượt p95 control** (control p95 = 0,50 E; 1,00 C). Kỳ C control trung vị (0,49) còn cao hơn thật.
4. Không đạt bất kỳ tiêu chí SỐNG nào ngoài maxDD của G-RANGE (nhưng maxDD nhỏ vì gần như không vào lệnh). **Không thử biến thể khác.**

---

## 1. Dữ liệu & kiểm tra

| Hạng mục | Giá trị |
|---|---|
| Kline 1m | 49 file tháng Vision UM, 2021-12 → 2025-12, 101 symbol được cache |
| Rổ E / C | BTC + ETH + top-10 alt point-in-time; universe hợp 63 / 57 symbol (chốt trong prereg) |
| Số tài sản/ngày | trung bình 12,0 |
| Funding | 374.405 dòng thật (8h/4h) từ file tĩnh `data.binance.vision`; 101/101 symbol có dữ liệu |
| File funding thiếu | 1.464 tháng-symbol: 1.337 trước ngày list + 127 sau delist (không phải gap trong cửa sổ giao dịch) |
| Gap funding > 35 ngày | 0 |
| Delist | dừng giao dịch tại bar cuối (LUNA, FTT, REEF, …); không đầu độc dữ liệu sau delist |

**Kiểm tra engine (V1, `validate.json`)** — chạy 20 đường GBM độc lập (σ = 8 bp/phút, 200k bar, phí = 0, funding = 0):
- G-RANGE: mean −0,17 %, median −0,07 % trên 139 ngày ⇒ **≈ 0**, đúng kỳ vọng lý thuyết của grid truyền thống trên random walk.
- G-DYN: mean **−8,8 %**, median −5,8 % trên 139 ngày ⇒ bản thân luật DGT (như paper mô tả) đã âm trên random walk, trước phí. Xem §7.1.

---

## 2. Bước 0 — variance ratio Lo–MacKinlay (1m → q phút)

Median VR và % tài sản có `VR < 1` với `z < −1,96` (heteroskedasticity-robust):

| q | E median VR | E % sig | C median VR | C % sig |
|---|---|---|---|---|
| 5m | 0,977 | 36,9 % | 0,998 | 8,5 % |
| 15m | 0,946 | 53,8 % | 0,959 | 10,2 % |
| **1h** | **0,913** | **56,9 %** | **0,865** | **6,8 %** |
| 4h | 0,884 | 44,6 % | 0,813 | 5,1 % |
| 1d | 0,888 | 20,0 % | 0,801 | 1,7 % |
| n tài sản | 65 | | 59 | |

- **Gate prereg (≥ 50 % tại 1h/4h/1d ở CẢ E và C): FAIL** — E pass (1h), C fail (cao nhất 6,8 %).
- BTC/ETH (VR, z):
  - BTC E: 1h 0,907 (−3,31); 4h 0,897 (−2,47); 1d 0,935 (−0,85).
  - ETH E: 1h 0,940 (−2,11); 4h 0,932 (−1,56); 1d 0,952 (−0,59).
  - BTC C: 1h 0,922 (−3,20); 4h 0,903 (−2,63); 1d 0,870 (−1,94).
  - ETH C: 1h 0,953 (−1,57); 4h 0,965 (−0,82); 1d 0,984 (−0,24).
- Đọc: **2022–2023 có mean-reversion thật ở 15m–4h; 2024–2025 median VR vẫn < 1 nhưng đa số không significant** (vol clustering làm phương sai robust phình to). Tiền đề "grid có edge vì giá mean-revert ở thang lưới" **không bền qua kỳ C**, đặc biệt trên BTC/ETH.

Autocorr lag-1 (tham khảo): hầu hết |ρ| < 0,03 ở 1h/4h/1d; không có tín hiệu định hướng dùng được.

---

## 3. Bước 1 — kết quả rổ đều trọng số (net maker + funding thật)

Bảng đầy đủ (gross / maker / taker). Sharpe ngày hoá √365; CAGR trên equity ngày; worst week = tổng 7 ngày tệ nhất.

### 3.1 G-RANGE (lưới số học 14 ngày, size cố định, stop cứng, ADX(14,4h)<20)

| Bản | Kỳ | Sharpe | CAGR | ret 2 năm | maxDD | tuần tệ nhất |
|---|---|---|---|---|---|---|
| gross (0 phí, 0 funding) | E | −1,23 | −0,84 % | −1,67 % | −2,5 % | −0,5 % |
| maker 0,02 % + funding | E | **−2,26** | **−1,56 %** | −3,09 % | −3,7 % | −0,6 % |
| taker 0,05 % | E | −2,77 | −1,91 % | −3,79 % | −4,3 % | −0,6 % |
| gross | C | −0,85 | −1,09 % | −2,17 % | −2,9 % | −1,6 % |
| maker + funding | C | **−1,41** | **−1,81 %** | −3,60 % | −3,6 % | −1,6 % |
| taker | C | −1,69 | −2,18 % | −4,32 % | −4,3 % | −1,7 % |

- Phí ăn ~0,7–1,0 % vốn/2 năm; gross đã âm ⇒ **không phải câu chuyện phí**.
- **99,7 % stop là do ADX**, không phải do phá biên: E 30.520/30.623; C 27.560/27.637. Chỉ 46 + 34 lần stop đáy, 57 + 43 lần stop đỉnh trên toàn bộ 124 tài sản-kỳ.
- **Thời gian bật lưới: 8,7 % (E) / 8,8 % (C)**; gross trung bình 0,2 % vốn. Nguyên nhân: ADX(4h) < 20 chỉ chiếm ~28–31 % số nến 4h, cộng cooldown 24h sau mỗi stop ⇒ mỗi episode hoạt động ~3 giờ, 0,4 lệnh/episode.

### 3.2 G-DYN (paper 2506.11921)

| Bản | Kỳ | Sharpe | CAGR | ret 2 năm | maxDD | tuần tệ nhất |
|---|---|---|---|---|---|---|
| G-DYN-g (geometric, quyết định) | E | **0,26** | **+1,59 %** | +3,20 % | **−35,2 %** | −24,6 % |
| G-DYN-g | C | **0,22** | **−0,89 %** | −1,78 % | **−30,4 %** | −26,4 % |
| G-DYN-a (arithmetic, chẩn đoán) | E | 0,32 | +4,09 % | +8,35 % | −37,7 % | −26,2 % |
| G-DYN-a | C | 0,22 | −0,86 % | −1,71 % | −32,0 % | −25,7 % |
| G-DYN-g taker | E / C | 0,27 / 0,20 | +1,94 / −1,82 % | +3,93 / −3,62 % | −36,9 / −30,9 % | −25,2 / −26,5 % |

- Lợi nhuận (nếu có) đến từ **exposure long**, không phải grid: gross trung bình 45 % vốn; DD 30–38 %; tuần tệ nhất −25 %.
- Funding ròng E **−1,84** (nhận, do funding alt âm trong bear 2022), C **−0,34** (nhận) — không phải nguồn lỗ chính.
- 12.706 (E) / 16.886 (C) lần reset; phí 5,0 / 6,3 % vốn/2 năm ở maker.

---

## 4. CONTROL random-walk (block bootstrap 1m, block = 60 bar, 60 seed/tài sản/kỳ)

| Kỳ | Luật | p05 | p50 | p95 | % control vượt thật | percentile của thật |
|---|---|---|---|---|---|---|
| E | G-RANGE | −2,36 | −1,50 | −0,27 | **90 %** | 10 |
| E | G-DYN-g | −0,73 | −0,07 | 0,50 | 17 % | 83 |
| C | G-RANGE | −1,70 | −0,96 | −0,28 | **80 %** | 20 |
| C | G-DYN-g | −0,23 | 0,49 | 1,00 | **78 %** | 22 |

- G-RANGE thật **tệ hơn random walk** ở cả hai kỳ (control cũng âm vì phí + ADX churn, nhưng ít âm hơn).
- G-DYN không vượt p95 ở kỳ nào; ở C nó còn **dưới trung vị control**.
- Ý nghĩa: không có bằng chứng edge ngoài "long exposure + may mắn kỳ E"; control chứng minh điều đó.

---

## 5. Tiêu chí SỐNG (prereg §5)

| Tiêu chí | G-RANGE | G-DYN-g |
|---|---|---|
| Net Sharpe ≥ 1,0 ở E | ✗ (−2,26) | ✗ (0,26) |
| Net Sharpe ≥ 1,0 ở C | ✗ (−1,41) | ✗ (0,22) |
| > p95 control E | ✗ | ✗ |
| > p95 control C | ✗ | ✗ |
| maxDD ≤ 20 % cả hai | ✓ (−3,7 / −3,6 %) | ✗ (−35 / −30 %) |
| Taker dương cả hai | ✗ (−2,77 / −1,69) | ✓ (0,27 / 0,20) |
| LOO ≥ 0,5 cả hai | ✗ (min −2,41 / −1,69) | ✗ (min 0,199 / 0,162) |
| Gate tiền đề VR | ✗ (FAIL ở C) | ✗ |

**Không có luật nào sống.** G-RANGE chỉ "đạt" maxDD vì gần như không vào lệnh; G-DYN chỉ "đạt" taker dương nhưng Sharpe ~0,2 và DD ~1/3 vốn.

---

## 6. Tương quan crash-buy & PnL trong các đợt sập

Tương quan lợi suất ngày với equity X14 DEV (trung bình 8 seed, chuỗi phút → ngày):

| Luật | E | C |
|---|---|---|
| G-RANGE | −0,028 | −0,002 |
| G-DYN-g | −0,029 | +0,032 |

PnL trong cửa sổ sập (%):

| Cửa sổ | G-RANGE E | G-DYN E | G-RANGE C | G-DYN C |
|---|---|---|---|---|
| LUNA 2022-05 | −0,1 | **−5,1** | — | — |
| 3AC 2022-06 | +0,1 | **−11,8** | — | — |
| FTX 2022-11 | −0,5 | **−14,5** | — | — |
| 2024-04 | — | — | −0,1 | −10,7 |
| 2024-08-05 | — | — | −0,1 | −8,9 |
| 2025-02-03 | — | — | −0,3 | −7,9 |
| 2025-03 | — | — | −0,2 | −10,0 |
| 2025-10-10 | — | — | −0,7 | **−24,5** |

G-DYN là "long coin + grid", nên đúng bản chất **âm nặng khi sập** và tương quan ~0 với hệ crash-buy (vì hệ crash-buy cũng long, nhưng thời điểm/độ lớn khác). G-RANGE gần như đứng ngoài thị trường nên PnL sập ~0.

---

## 7. Bất thường & bài học

### 7.1 Paper 2506.11921: text và code release không khớp — DGT âm trên random walk
- Text §3.1: khi vượt biên trên, "initial capital is fully recovered and reinvested" ⇒ phải bán coin để thu vốn. Code release (`handle_up_break`) **không bán COIN**, lại cộng thêm `grid_principal` vào USDT trong khi coin vẫn giữ ⇒ **double-count vốn**, thổi phồng kết quả "outperformance".
- Bản cài đặt ở đây theo **text** (prereg §3.3): bán toàn bộ coin khi vượt biên trên. Hệ quả: sau một lần phá đáy, coin mua dải giá cao bị bán lại khi giá chỉ hồi +10 % từ đáy lưới mới ⇒ **lỗ cấu trúc**; trên random walk 0 phí, DGT mất −8,8 %/139 ngày. Đây là lý do G-DYN không thể có edge dù có mean-reversion.
- Nếu ai muốn bảo vệ DGT, phải prereg riêng với định nghĩa "carried coin" rõ ràng; task này **không** làm.

### 7.2 ADX gate biến G-RANGE thành "chiến lược ngồi ngoài"
- ADX(14,4h) < 20 chỉ ~28–31 % thời gian; stop ngay khi ADX ≥ 20 + cooldown 24h ⇒ exposure 8,7 %, episode ~3h.
- Vì vậy kết quả G-RANGE chủ yếu đo **chi phí whipsaw của gate**, không đo edge của grid. Prereg đã chốt luật này nên verdict giữ nguyên; nhưng phải đọc đúng: **"grid + trend filter cứng" = gần như không giao dịch**.
- Không chạy biến thể "chỉ gate lúc vào, không thanh lý khi ADX tăng" — ngoài prereg, sẽ là task riêng.

### 7.3 VR: median < 1 nhưng z không significant ở C
- Vol clustering làm θ (robust) lớn; median VR 0,86 ở 1h vẫn không đủ bằng chứng. Đây là bài học: **đừng dùng median VR làm bằng chứng edge**, phải dùng z và kiểm ngoài mẫu.

### 7.4 Khác
- Funding: 1.464 tháng-symbol thiếu file, toàn bộ trước list hoặc sau delist; không có gap trong cửa sổ giao dịch.
- Delist: LUNA/FTT/REEF… dừng tại bar cuối, không forward-fill giả; có thể lạc quan vì không mô phỏng haircut delist.
- Khớp limit "chạm là khớp" là lạc quan; bản taker không sửa được queue risk, chỉ sửa phí.
- Không có lệnh nào bị chặn; không truy cập 242, không REST Binance, không dùng 2020/2026.

---

## 8. Kết luận

- **Tiền đề lý thuyết không đứng vững ngoài mẫu**: mean-reversion ở thang 1h–4h rõ ở 2022–2023, biến mất (statistically) ở 2024–2025.
- **Grid có luật vào/ra theo đúng yêu cầu vẫn lỗ**; DGT của paper không tạo edge khi cài đúng text, và bản code của tác giả có lỗi double-count.
- **Đóng họ grid trong task này.** Không thử biến thể, không đổi ngưỡng, không chọn lại universe.

Nếu owner vẫn muốn theo grid, cần một prereg mới với giả thuyết khác hẳn (ví dụ: gate chỉ lúc entry + range theo volume profile), và **phải chấp nhận rằng control random-walk là chuẩn tối thiểu** — mọi báo cáo grid không vượt p95 control đều là nhiễu.
