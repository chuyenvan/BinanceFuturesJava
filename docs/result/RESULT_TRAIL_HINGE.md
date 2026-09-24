# RESULT_TRAIL_HINGE — bản lề trailing STRONG/WEAK (SIM_TS_MAX_GAP / SIM_TS_PNOPUMP_WEAK_THR) trên gate T170 / DEV 2021

Pre-reg: `docs/prereg/PREREG_TRAIL_HINGE.md` (chốt TRƯỚC khi chạy). Nền: dataset `wfo_ds_x1_2021` (18 fold
2021Q3..2025Q4), baseline `X1_GS_T170_2021` (profile `profiles/x1_gs_t170.properties`, md5 printDone
`efb793e2`, n=1089). Jar HEAD `9861132` (KHÔNG rebuild). SIM_END_DATE=20251231, holdout 2026 nguyên
vẹn. KHÔNG chạm 242, KHÔNG tune, KHÔNG push, KHÔNG đổi code Java.

## 0. Phán quyết (tóm trước)

- **REPRODUCTION T170: PASS.** Re-run `X1_GS_T170_2021_REPRO` → md5 printDone **`efb793e2`** trùng byte
  (n=1089, equity 111070, 788s).
- **V1 (`x1_th_gap05`, `SIM_TS_MAX_GAP` 0.08→0.05): NULL.** 0 rate chất lượng ngoài CI (toàn cửa sổ,
  k=3). PASS rào cứng MỚI mọi năm; PASS luôn rào cứng CŨ mọi năm (UW đỉnh 119 ≤ 120).
- **V2 (`x1_th_gap12`, `SIM_TS_MAX_GAP` 0.08→0.12): NULL.** 0 rate chất lượng ngoài CI (toàn cửa sổ,
  k=3). PASS rào cứng MỚI mọi năm; **FAIL rào cứng CŨ năm 2025** (UW=164 > 120, chỉ tham khảo — không
  phải tiêu chí quyết định). Ghi chú: riêng cửa sổ phụ năm 2024, 2/5 rate (mP\|SM, meanP) ngoài CI theo
  hướng xấu — không đủ để lật verdict vì luật dùng cửa sổ TOÀN BỘ, không cộng dồn theo năm.
- **V3 (`x1_th_weak17`, `SIM_TS_PNOPUMP_WEAK_THR` 0.29→0.17): NULL.** 0 rate chất lượng ngoài CI (toàn
  cửa sổ, k=3). PASS rào cứng MỚI và CŨ mọi năm.
- **Không có trường hợp "VÔ HIỆU"**: md5 V1 (`b3f995ab…`) và V2 (`ddcbb6b2…`) đều KHÁC `efb793e2` →
  xác nhận lại kết luận §0 pre-reg: cả hai key (`SIM_TS_MAX_GAP`, `SIM_TS_PNOPUMP_WEAK_THR`) đều bind
  thật trong đường sim.
- Khớp đúng dự đoán MASTER ghi trước (NULL cho cả 3; V3 hiệu ứng nằm trong CI dù dấu điểm-ước-lượng
  của TSloss%/meanP ngược chiều dự đoán chút ít — biên độ quá nhỏ để có ý nghĩa).

## 1. Cổng REPRODUCTION + cổng "chỉ đổi 1 key"

| cổng | kết quả |
|---|---|
| Key bind (Configs.java:659/662-663, rank-cap không kích hoạt) | PASS (đã xác nhận ở §0 pre-reg trước khi chạy) |
| Reproduction T170 → `X1_GS_T170_2021_REPRO` | PASS — md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, b:111070, 788s |
| diff `x1_th_gap05.properties` vs `x1_gs_t170.properties` | đúng 1 dòng thêm: `SIM_TS_MAX_GAP=0.05` |
| diff `x1_th_gap12.properties` vs `x1_gs_t170.properties` | đúng 1 dòng thêm: `SIM_TS_MAX_GAP=0.12` |
| diff `x1_th_weak17.properties` vs `x1_gs_t170.properties` | đúng 1 dòng thêm: `SIM_TS_PNOPUMP_WEAK_THR=0.17` |

## 2. Bảng chính (equity/CAGR KHÔNG phải tiêu chí, chỉ báo cáo)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X1_GS_T170_2021 (baseline) | 1089 | 88.25 | 9.73 | 7.642 | -16.992 | 5.244 | 1851 | -11.84 | 92 | 111070 | 29.27 |
| X1_TH_GAP05_2021 (V1) | 1095 | 88.31 | 9.68 | 7.468 | -17.014 | 5.098 | 1843 | -11.82 | 119 | 107313 | 28.28 |
| X1_TH_GAP12_2021 (V2) | 1091 | 88.45 | 9.53 | 7.665 | -16.999 | 5.314 | 1851 | -11.84 | 164 | 112465 | 29.63 |
| X1_TH_WEAK17_2021 (V3) | 1095 | 88.22 | 9.77 | 7.723 | -16.998 | 5.308 | 1893 | -11.67 | 119 | 114287 | 30.09 |

## 3. CI hiệu (variant − baseline), khối-72h, `inflate(k=3)=sqrt(2 ln 3)=1.482304`, TOÀN CỬA SỔ

`python3 research/analysis/x1_rates.py --k 3 X1_GS_T170_2021 <variant>` — script tự in thêm 5 cửa sổ
phụ theo năm (2021..2025); theo pre-reg §3(i) luật THẮNG/NULL/THUA áp trên cửa sổ TOÀN BỘ, các cửa sổ
năm chỉ tham khảo chẩn đoán.

### V1 GAP05 (n_A=1095, n_B=1089)
| rate | hiệu | lo | hi | ngoàiCI |
|---|---|---|---|---|
| win% | +0.064 | -0.054 | +0.209 | - |
| TSloss% | -0.053 | -0.172 | +0.045 | - |
| mP\|SM | -0.174 | -0.467 | +0.078 | - |
| mP\|SL | -0.022 | -0.068 | +0.013 | - |
| meanP | -0.146 | -0.418 | +0.083 | - |
| n (control) | +6 | -5.1 | +20.1 | - |
| mMargin (control) | -8.3 | -23.9 | +6.8 | - |
=> **0 rate ngoài CI** (bỏ n, mMargin) → NULL.

### V2 GAP12 (n_A=1091, n_B=1089)
| rate | hiệu | lo | hi | ngoàiCI |
|---|---|---|---|---|
| win% | +0.205 | -0.152 | +0.782 | - |
| TSloss% | -0.201 | -0.770 | +0.150 | - |
| mP\|SM | +0.023 | -0.239 | +0.294 | - |
| mP\|SL | -0.008 | -0.153 | +0.117 | - |
| meanP | +0.070 | -0.175 | +0.308 | - |
| n (control) | +2 | -1.4 | +7.4 | - |
| mMargin (control) | -0.4 | -8.0 | +7.0 | - |
=> **0 rate ngoài CI** (bỏ n, mMargin) → NULL. (Riêng cửa sổ phụ 2024: mP\|SM -0.151 [YES, xấu],
meanP -0.135 [YES, xấu] — 2 rate ngoài CI xấu trong NĂM ĐÓ, nhưng không quyết định vì luật dùng cửa
sổ toàn bộ.)

### V3 WEAK17 (n_A=1095, n_B=1089)
| rate | hiệu | lo | hi | ngoàiCI |
|---|---|---|---|---|
| win% | -0.027 | -0.308 | +0.184 | - |
| TSloss% | +0.038 | -0.164 | +0.316 | - |
| mP\|SM | +0.082 | -0.132 | +0.290 | - |
| mP\|SL | -0.006 | -0.069 | +0.054 | - |
| meanP | +0.064 | -0.129 | +0.257 | - |
| n (control) | +6 | -1.9 | +15.9 | - |
| mMargin (control) | +41.4 | +20.6 | +62.2 | YES (control, không tính) |
=> **0 rate ngoài CI** (bỏ n, mMargin) → NULL.

## 4. Rào cứng theo năm — 2 bộ ngưỡng

### 4a. Rào cứng MỚI (`docs/runbooks/RISK_APPETITE.md`: maxDD≤30%, UW≤200 ngày, quý≥-15%, tập trung 1 coin≤15%) — CỔNG QUYẾT ĐỊNH

| tag | năm | maxDD% | UW | ret_năm% | quý min% | tập trung 1 coin (overall) | PASS |
|---|---|---|---|---|---|---|---|
| T170 | 2021..2025 | -2.46..-11.84 | 37..92 | 12.2..35.0 (mọi năm dương) | -0.92 | 9.77% | **PASS cả 5 năm** |
| V1 GAP05 | 2021..2025 | -2.46..-11.82 | 30..119 | 12.5..35.0 (mọi năm dương) | -2.54 | 9.77% | **PASS cả 5 năm** |
| V2 GAP12 | 2021..2025 | -2.47..-11.84 | 37..164 | 12.1..35.6 (mọi năm dương) | -1.13 | 9.76% | **PASS cả 5 năm** |
| V3 WEAK17 | 2021..2025 | -2.47..-11.67 | 37..119 | 11.8..35.5 (mọi năm dương) | -1.97 | 9.77% | **PASS cả 5 năm** |

Tất cả 4 tag đều PASS rào cứng MỚI ở mọi năm — UW cao nhất (V2/2025 = 164 ngày) vẫn dưới trần 200; tập
trung 1 coin ~9.76-9.77% cho cả 4 tag, dưới trần 15% với biên khá rộng.

### 4b. Rào cứng CŨ (maxDD≤15%, UW≤120, không năm âm, quý≥-5%) — chỉ tham khảo, KHÔNG phải tiêu chí

| tag | năm | maxDD% | UW | quý min% | PASS/FAIL |
|---|---|---|---|---|---|
| T170 | 2021 | -2.46 | 37 | 4.44 | PASS |
| T170 | 2022 | -11.84 | 72 | 2.90 | PASS |
| T170 | 2023 | -2.73 | 63 | -0.37 | PASS |
| T170 | 2024 | -6.60 | 92 | -0.92 | PASS |
| T170 | 2025 | -4.23 | 52 | 1.27 | PASS |
| V1 GAP05 | 2024 | -6.60 | 119 | -2.54 | PASS (UW sát trần) |
| V1 GAP05 | khác | — | ≤73 | ≥-0.37 | PASS |
| V2 GAP12 | 2025 | -4.34 | **164** | 1.14 | **FAIL** (UW>120) |
| V2 GAP12 | khác | — | ≤88 | ≥-1.1 | PASS |
| V3 WEAK17 | 2024 | -6.54 | 119 | -1.97 | PASS (UW sát trần) |
| V3 WEAK17 | khác | — | ≤63 | ≥-0.37 | PASS |

## 5. Đối chiếu dự đoán ghi trước (§4 pre-reg)

> "MASTER dự đoán NULL cho cả 3 (P≥1 thắng ≈ 25%); nếu V1/V2 ra byte-identical với T170 ⇒ key không
> bind ⇒ VÔ HIỆU; V3 kỳ vọng TSloss% giảm nhưng meanP giảm (cắt sớm), nhiều khả năng trong CI."

- Cả 3 variant: **NULL** — đúng dự đoán.
- V1/V2 KHÔNG byte-identical với T170 (md5 khác) — key bind thật, không phải trường hợp VÔ HIỆU —
  đúng với kết luận §0 pre-reg (đã xác nhận bind trước khi chạy), và phủ định giả thuyết dự phòng.
- V3: điểm-ước-lượng thực tế TSloss% **+0.038** (tăng nhẹ, không giảm như dự đoán) và meanP **+0.064**
  (tăng nhẹ, không giảm như dự đoán) — ngược dấu so với kỳ vọng định tính, nhưng đúng phần cốt lõi của
  dự đoán: biên độ rất nhỏ, cả hai đều **nằm trong CI** (không có ý nghĩa thống kê).

## 6. Ghi chú vận hành

- **Bối cảnh trước khi bắt đầu (13:32 giờ Oracle):** sim REPRO trước đó (PID 1169539) bị OOM-kill
  (anon-rss 14.2G) do chạy đồng thời với job xgboost. Trước khi bắt đầu vòng này: `free -g` available
  16G, `pgrep -af "Simulator|ExportWfo|WFORunner|s1_hpo|xgboost"` rỗng — box rảnh, chỉ còn
  `BinanceOrderTradingManager` (-Xmx4g, không đụng).
- **Dọn đĩa (bước 1):** `df -h /home/ubuntu` trước: `194G, used 185G, avail 9.0G (96%)`. Đã kiểm
  `lsof +D` trên 4 thư mục — không process nào đang dùng — rồi `rm -rf wfo_ds_clean` (1.8G),
  `wfo_ds_x1` (4.0G), `wfo_ds_x1_base_now` (4.3G), `wfo_ds_x1_oi12_2021` (4.3G); GIỮ nguyên
  `wfo_ds_x1_2021`. Truncate log container `aerospike-wfo`
  (`/var/lib/docker/containers/0a8dd9b529cc…/…-json.log`, 4.52G → 0) bằng `sudo truncate -s 0`, không
  xoá file, không restart container — `docker ps` xác nhận container vẫn `Up` sau đó. `df -h` sau:
  `194G, used 169G, avail 26G (87%)`.
- **4 sim chạy TUẦN TỰ, mỗi lần chờ `pgrep` rỗng mới launch** (nohup + disown, poll `logs/sim.out` qua
  bridge desktop-commander mỗi ~3-4 phút):
  | run | PID | thời lượng | RAM đỉnh | kết thúc (giờ Oracle) |
  |---|---|---|---|---|
  | REPRO (T170) | 1172105 | 788s (~13.1 phút) | 10301 MB | 14:08:38 |
  | V1 GAP05 | 1173076 | 794s (~13.2 phút) | 9398 MB | 14:25:15 |
  | V2 GAP12 | 1173938 | 786s (~13.1 phút) | 8623 MB | 14:40:22 |
  | V3 WEAK17 | 1174679 | 783s (~13.1 phút) | 10372 MB | 14:56:09 |

  Không lần nào chạy đồng thời với job khác; RAM đỉnh mỗi lần ≤ 10.4GB, xa dưới `-Xmx14g` — không lặp
  lại OOM. Free RAM available trong suốt phiên: 14-16G.
- Không tune tham số sau khi thấy số. Không đụng 242 / holdout 2026. Không git push, không ssh 242.
- Dataset dùng chung `wfo_ds_x1_2021` cho cả 4 run (2 key exit-param áp ở SIM-time, không bake vào
  `ExportWfoDataset`, không rebuild dataset).

## 7. Kết luận cho MASTER

**Cả 3 variant TRAIL_HINGE đều NULL** — không đủ bằng chứng thắng, không đủ bằng chứng thua so với
baseline T170 (gate mặc định `SIM_TS_MAX_GAP=0.08` / `SIM_TS_PNOPUMP_WEAK_THR=0.29` giữ nguyên là lựa
chọn tốt nhất hiện có). Cả 3 đều PASS rào cứng rủi ro MỚI ở mọi năm. Khuyến nghị: giữ nguyên T170,
không áp dụng biến thể nào; không cần thí nghiệm thêm quanh 2 tham số này trong phạm vi đã pre-reg (mở
nhánh mới nếu muốn thử vùng giá trị khác, không tune trong vòng này).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
