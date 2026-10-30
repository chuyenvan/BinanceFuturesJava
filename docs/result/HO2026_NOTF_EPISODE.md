# HO2026_NOTF_EPISODE — ΔROI +3,3 pp đến từ đâu theo thời gian, và nó mong manh cỡ nào (2026-10-30)

MÔ TẢ. Không chạy sim mới, không tune, không đổi X/cấu hình/ngưỡng. Nguồn: `printDone.csv` của 48 kernel
(3 cấu hình × A0/A1 × 8 seed) + MTM dựng lại độc lập từ giá 1m Vision (`~/claude_master/audit_1030/aud_mtm.py`,
`mtm_all_eq.npz`). Script trong repo: `research/ho2026_notf/ep_blocks.py`.

## 0. TL;DR

1. ΔROI W9 (A1 − A0): **+3,28 pp** (k24-s) / **+3,33 pp** (x14) — khớp `HO2026_NOTF.md`.
2. **Tháng 6 chiếm phần lớn**: đóng góp +4,08 / +3,95 pp (theo Σ Δ ngày), **124 % / 119 %** của ΔROI cả cửa sổ.
   **Bỏ tháng 6 ⇒ ΔROI = −1,30 / −1,17 pp** (audit; tính lại bằng ROI ghép lãi: −1,13 / −1,07).
3. **Trong tháng 6, 5 ngày 06-02..06-06 = +2,32 / +2,22 pp (71 % / 67 %)**. Bỏ 5 ngày này ⇒ ΔROI = **+0,96 / +1,11 pp**
   (audit; tính lại: +0,90 / +1,01), dương ở **6/8** và **5/8** seed.
4. **Bootstrap theo khối ngày** (moving block 5 ngày, B=5 000, không resample seed): mean +3,05 / +2,98 pp,
   CI 90 % **[−1,77; +8,61] / [−1,64; +8,24]**, **P(ΔROI ≤ 0) = 17,2 % / 16,1 %**. Khối 21 ngày: P(≤0) = 19,6 % / 18,6 %.
5. Kết luận: ΔROI **có thật trong mẫu** nhưng **mong manh** — dồn vào 1 tháng và 5 ngày cụ thể; nếu chuỗi ngày
   của năm 2026 được xáo lại theo tuần/tháng thì ~1/5 khả năng không còn lợi thế. Không đủ cơ sở để coi +3,3 pp là
   đặc tính ổn định của universe A1.

## 1. Định nghĩa

- `r_t = E_t/E_{t-1} − 1`, `E_t` = equity MTM cuối ngày UTC t (giá close 1m Vision); `E_{-1}` = equity_start.
- **đóng góp tháng** = `100 · Σ_{t∈tháng} (r_t(A1) − r_t(A0))` (pp của e0, cộng được, khớp cách audit đang dùng).
- **ΔROI tháng** = `[Π(1+r(A1))−1] − [Π(1+r(A0))−1]` trong tháng (ghép lãi) — in kèm để thấy khác biệt định nghĩa.
- Năm "bỏ X" = tính lại ROI trên chuỗi ngày **không** thuộc X rồi trừ nhau (ghép lãi qua các ngày còn lại).
- Seed: mọi số là **trung bình 8 seed**; bootstrap **chỉ resample trục ngày**, không resample seed (theo yêu cầu).

## 2. ΔROI theo tháng (2026)

**k24-s** (W9 = +3,28 pp; Σ đóng góp ngày = +3,01 pp do ghép lãi khác tuyến tính):

| tháng | đóng góp (pp) | ΔROI tháng (pp) | seed dương |
|---|---|---|---|
| 01 | +0,01 | +0,01 | 4/8 |
| 02 | +0,25 | +0,26 | 5/8 |
| 03 | −0,17 | −0,17 | 4/8 |
| 04 | +0,38 | +0,39 | 3/8 |
| 05 | +0,15 | +0,15 | 6/8 |
| **06** | **+4,08** | **+4,30** | **8/8** |
| 07 | +1,31 | +1,28 | 6/8 |
| 08 | −1,87 | −1,89 | 1/8 |
| 09 | −1,14 | −1,14 | 2/8 |

**x14** (W9 = +3,33 pp):

| tháng | đóng góp (pp) | ΔROI tháng (pp) | seed dương |
|---|---|---|---|
| 01 | +0,07 | +0,08 | 4/8 |
| 02 | +0,20 | +0,21 | 6/8 |
| 03 | −0,09 | −0,09 | 4/8 |
| 04 | +0,06 | +0,06 | 2/8 |
| 05 | +0,05 | +0,05 | 4/8 |
| **06** | **+3,95** | **+4,17** | **8/8** |
| 07 | +1,26 | +1,23 | 6/8 |
| 08 | −1,73 | −1,76 | 2/8 |
| 09 | −0,82 | −0,82 | 1/8 |

Đọc: ngoài tháng 6–7, ΔROI **âm** ở 03, 08, 09 (và 08/09 chỉ 1–2/8 seed dương). Tháng 6 là tháng duy nhất **8/8 seed dương**.

## 3. Độ nhạy (bỏ mùa/tháng/đợt)

| phép bỏ | k24-s | x14 | nguồn |
|---|---|---|---|
| không bỏ gì (W9) | **+3,28** | **+3,33** | audit |
| bỏ **tháng 6** | **−1,30** | **−1,17** | audit (`mech.py`) |
| bỏ **06-02..06-06** | **+0,96** | **+1,11** | audit |
| bỏ tháng 6 — tính lại bằng ROI ghép lãi | −1,13 | −1,07 | `ep_blocks.py` |
| bỏ 06-02..06 — tính lại bằng ROI ghép lãi | +0,90 | +1,01 | `ep_blocks.py` |
| chỉ tháng 6 | +4,30 | +4,17 | `ep_blocks.py` |

Hai cách tính lệch nhau 0,1–0,2 pp (do audit dùng Σ Δ tuyệt đối chia e0, ở đây dùng ROI ghép lãi); **dấu và bậc
độ lớn giống nhau**. Số audit được giữ làm số chính vì đã dùng trong `HO2026_NOTF_MECH.md` §6.

## 4. Bootstrap theo khối (ngày, không theo seed)

Moving block bootstrap trên chuỗi 273 ngày Δ (trung bình 8 seed), B = 5 000:

| cấu hình | khối | mean | p05 | p50 | p95 | P(ΔROI ≤ 0) |
|---|---|---|---|---|---|---|
| k24-s | 5 ngày | +3,05 | −1,77 | +2,87 | +8,61 | **17,2 %** |
| k24-s | 21 ngày | +3,01 | −2,57 | +2,91 | +9,09 | **19,6 %** |
| x14 | 5 ngày | +2,98 | −1,64 | +2,78 | +8,24 | **16,1 %** |
| x14 | 21 ngày | +2,96 | −2,24 | +2,81 | +8,56 | **18,6 %** |

Ghi chú: 117–124/273 ngày có Δ = 0 (không có leg đóng trong ngày) — bootstrap giữ nguyên cấu trúc này vì lấy khối
ngày liền nhau. Khối 21 ngày (≈ tháng) cho CI rộng hơn và P(≤0) cao hơn, đúng chiều "dồn cụm".

## 5. Kết luận về độ mong manh

- ΔROI +3,3 pp **không phải hiệu ứng rải đều**: bỏ tháng 6 ⇒ âm; bỏ 5 ngày 06-02..06 ⇒ chỉ còn +0,96/+1,11 pp.
- 5 ngày đó ứng với **đợt TF bị lỗ** ở A0 (238 leg TF, 68,5 % rơi 06-02..05, PnL −7 900; xem `HO2026_NOTF_MECH.md` §6).
  Nói cách khác: phần lớn "lợi thế" của A1 là **né một đợt lỗ cụ thể của universe cũ**, không phải cải thiện cấu trúc
  lặp lại đều.
- Bootstrap khối tuần/tháng: **~1/5 khả năng ΔROI ≤ 0** nếu năm 2026 được xáo lại theo cụm. Vì vậy **không** nên
  phát hành A1 như "universe tốt hơn 3,3 pp"; nếu phát hành thì phải ghi rõ kỳ vọng phụ thuộc chế độ thị trường
  tháng 6/2026 và theo dõi out-of-sample.
- **CHƯA GIẢI THÍCH**: vì sao tháng 8 và 9 ΔROI âm (1–2/8 seed dương); chưa truy được chuỗi quyết định
  (slot/gate/size) ở mức order cho các tháng này.

## 6. Tái lập

```
python3 research/ho2026_notf/ep_blocks.py /tmp/ep_blocks.json   # ~4 s, chỉ đọc npz + printDone
```
Không tải dữ liệu mới, không gọi Binance API, không ssh 242. Artefact: `/tmp/ep_blocks.json` (xoá sau khi chép số vào doc).
