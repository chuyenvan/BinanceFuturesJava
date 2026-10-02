# RESULT_SHORT_BETANEUTRAL — short top-K8 (N1b) + long EW cùng tick, tách beta alt

Pre-reg: `docs/prereg/PREREG_SHORT_BETANEUTRAL.md` (`6610b587`, commit **TRƯỚC** đo). Nguồn: audit §10 (`a6867424`).
Script: `research/analysis/short_betaneutral_score.py` · số: `docs/result/RESULT_SHORT_BETANEUTRAL.json`.
0-sim, 0 kernel, 0 Java; bins `~/sm_pathexit/sm/OLD_ndown_S42` (16 fold OOS) · nhãn `ds_label15m` · funding `/tmp/fund_cache.npz`.
Cửa sổ chính: tick `2022-01-01 ≤ t`, `t + 72h ≤ 2026-01-01` ⇒ **139 094 tick**, 1 111 217 lệnh short (7,99/tick). Chạy 1,6 phút.

## 0. VERDICT: **NO-GO** ⇒ **ĐÓNG HƯỚNG SHORT trên dữ liệu hiện có** (theo luật §6 khoá)

Beta đã được tách (β spread **+0,03**), rank-IC dương **4/4 năm**, nhưng spread beta-neutral sau phí 2 chân + funding
2 chân chỉ **+0,019 %/72h**, CI raw **[−0,181; +0,215] %** chứa 0, **2/4 năm** dương, stress 0,150 %/chân **−0,057 %**.

| # | Điều kiện | Số | Kết quả |
|---|---|---|---|
| 1 | Sanity tái lập V3 (±0,03 pp) | net_pre **+0,3865 %** (mục tiêu +0,409; Δ −0,022 pp) · fund_mean **−0,5811 %** (mục tiêu −0,580; Δ −0,001 pp) | **PASS** |
| 2 | mean > 0, CI raw **và** ×1,21 ngoài 0 | +0,0189 % · raw [−0,1808; +0,2149] · ×1,21 [−0,2227; +0,2560] | **FAIL** |
| 3 | ≥ 3/4 năm spread > 0 | 2/4 (2022 +, 2023 +, 2024 −, 2025 −) | **FAIL** |
| 4 | rank-IC > 0 cả 4 năm | +0,048 / +0,035 / +0,054 / +0,069 | **PASS** |
| 5 | stress 0,150 %/chân > 0 (điểm) | −0,0571 % | **FAIL** |

Sanity tham khảo (không phải cổng): arm SHORT42 của V3 (`/tmp/smv3.json`) net_pre +0,3857 % · fund −0,5810 % ·
n 1 114 016; ở đây n 1 113 792 (join 35 446 939 vs 35 450 551 dòng của V3, −0,01 %) ⇒ bins `OLD_ndown_S42` ≈ bins V3 SHORT42.

## 1. Spread beta-neutral (mean theo tick, %/72h)

| Đại lượng | mean | CI raw | CI ×1,21 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|
| **spread** (phí 0,112 %×2, funding 2 chân) | **+0,019** | [−0,181; +0,215] | [−0,223; +0,256] | +0,137 | +0,125 | −0,004 | −0,182 |
| spread stress (0,150 %×2) | −0,057 | [−0,257; +0,139] | [−0,299; +0,180] | +0,061 | +0,049 | −0,080 | −0,258 |
| F3-bound (phụ, funding lệnh cắt tới tHitFav) | +0,040 | [−0,161; +0,231] | [−0,204; +0,271] | +0,139 | +0,134 | −0,002 | −0,112 |

Phân rã mean spread: excess **gross** (short sau cắt + long EW, trước phí & funding) **+0,212 %** − phí 2 chân 0,224 % +
funding ròng 2 chân **+0,031 %** (short +0,033 %, long EW trả ≈ +0,002 %) = +0,019 %.

## 2. Beta + IC

| Đại lượng | Số | Ghi chú |
|---|---|---|
| β chân short (mean retEnd_72h của K8, chưa cắt, trên R_EW theo tick) | **1,038** | corr 0,752 ⇒ chân short ≈ thị trường alt |
| β spread trên R_EW | **+0,030** | beta đã tách gần hết |
| rank-IC toàn kỳ (Spearman(score, −ret) theo tick, toàn bins ∩ nhãn, không lọc N1b) | **+0,0517** | khớp +0,052 của audit |
| rank-IC 2022 / 2023 / 2024 / 2025 | +0,048 / +0,035 / +0,054 / +0,069 | dương 4/4 |
| Universe EW / tick (mean) | 254,3 symbol | R_EW mean −0,154 %/72h; F_EW +0,002 % |
| N1b giữ (tỷ lệ dòng bins qua lọc) | 81,2 % | top-8 chọn **sau** lọc ⇒ 7,99 lệnh/tick |
| cắt +30 % | 8,0 % lệnh | |

## 3. Đối chiếu directional (cùng tập K8 sau N1b, không hedge, phí 1 chân)

| | mean | CI raw | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| directional short | +0,287 % | [−0,263; +0,852] | +1,236 | −0,480 | −0,167 | +0,573 |
| **beta-neutral spread** | **+0,019 %** | [−0,181; +0,215] | +0,137 | +0,125 | −0,004 | −0,182 |
| chân long EW (R_EW − F_EW) | −0,156 % | [−0,681; +0,377] | | | | |

Half-width CI co **~2,8×** (±0,55 → ±0,20 %), **không** 5–8× như ước tính trước (audit §8 dựa trên STATE 24h).
Chênh directional − spread = 0,27 pp = beta (DEV alt EW −0,154 %/72h) + phí chân thứ hai 0,112 %; sau tách beta còn
+0,212 % gross — thấp hơn ước tính trước +0,34 % — và bị phí chân thứ hai (0,112 %) ăn gần hết.

## 4. Đối chiếu ước tính trước (pre-reg §8)

Dự kiến ~+0,1 %/72h, half-width ±0,08–0,12 %. Thực tế +0,019 %, half-width ±0,20 %. Cả hai đều xấu hơn dự kiến ⇒
không phải "sát ngưỡng": điểm ước lượng ≈ 0, năm 2025 (IC cao nhất +0,069) lại có spread âm nhất (−0,18 %).

## 5. Giới hạn (khai báo)

1. **1 seed** (bins `OLD_ndown_S42`), đúng pre-reg; không dùng SHORT7/13 để "chọn".
2. **Chân long EW lạc quan về chi phí:** rổ ~254 symbol (gồm alt kém thanh khoản), rebalance mỗi tick, nhưng chỉ trừ
   0,112 %/vòng như chân short ⇒ chi phí thực của chân hedge **cao hơn** ⇒ spread thực **≤** số báo cáo. Không đổi verdict.
3. **Funding chân short tính cả 72h** kể cả 8 % lệnh bị cắt (F3, bảo thủ). F3-bound (funding tới `tHitFav_72h`, vẫn
   ≥ thời điểm chạm +30 %) chỉ nâng spread lên +0,040 %, CI vẫn chứa 0, 2/4 năm ⇒ không đổi verdict.
4. **Lệnh 72h chồng lấp** giữa các tick 15 phút ⇒ CI block-72h hơi hẹp; ×1,21 là bù thô. Hướng lệch: lạc quan.
5. Long EW **không cắt**, không mô hình liquidation/borrow; notional 2 chân bằng nhau theo tick (không vol-scaling).
6. **Sửa dấu bản nháp §10 trước khi đo** (`+R_EW` cho chân long; nháp viết `−mean_EW`) — ghi trong pre-reg §3.
7. Sanity lệch mục tiêu mean-seed **−0,022 pp** (trong dung sai 0,03) vì mục tiêu là trung bình 3 seed; so arm SHORT42
   riêng lệch +0,0008 pp. Join nhãn `ds_label15m` thiếu 3 612 dòng (−0,01 %) so V3 — không đáng kể.
8. IC dương 4/4 năm **không** chuyển thành spread top-K8 dương bền: kỹ năng xếp hạng có thật (thống kê) nhưng biên
   kinh tế ở đuôi top-8 sau phí 2 chân ≈ 0. Không chạy biến thể (K/decile/C/T khác) — bị cấm bởi pre-reg §7.

## 6. Hệ quả theo luật

**NO-GO ⇒ đóng hướng SHORT trên dữ liệu hiện có.** Chỉ mở lại khi có data mới (liquidation/L2 từ 09/2026 tích luỹ đủ
forward). Không có vòng "thử thêm biến thể".

## 7. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_BETANEUTRAL.md` | pre-reg (`6610b587`, TRƯỚC đo) |
| `research/analysis/short_betaneutral_score.py` | chấm 0-sim (sanity → IC → K8 sau N1b → EW → spread/CI/năm/β/stress/F3) |
| `docs/result/RESULT_SHORT_BETANEUTRAL.json` | số đầy đủ |

Tuân thủ: không `.java`, không Java sim, không Kaggle, không 242/LIVE, không dữ liệu 2026 (cửa sổ `t + 72h ≤ 2026-01-01`),
không xoá dữ liệu, không đọc secret. Lúc chạy chỉ có dịch vụ thường trực (trading manager, Aerospike, gateway), không job nặng khác.
