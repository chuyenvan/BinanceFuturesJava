# NUP3-S0: lệnh thêm A2 chạy sleeve riêng, dừng khi "sóng lớn" (kết quả)

Prereg: `docs/prereg/PREREG_NUP3_S0.md` (commit b7267738, sha256 4e45950f030def26…). Chỉ đo trên artefact sẵn có, không sim mới.
Code: `research/nup3_s0/{s0.py, validate.py, indep_check.py, causal_check.py}`. Số máy: `docs/result/nup3_s0/*.csv`.

## 0. Verdict (risk-first)
- **W_burst ĐẠT S0 (3/3), là W duy nhất đạt.** W_mkt, W_book, W_quiet TRƯỢT (đều trượt C2 = HO).
- Theo luật S0 ⇒ MASTER viết prereg NUP3 (sim sleeve thật) với W_burst. S0 KHÔNG phải GO tiền thật.
- **Cảnh báo, đọc trước khi tin W_burst:**
  1. Pass là **biên**. HO NGOÀI ROI_stress chỉ **+0,18 %/lệnh** (DEV +1,24 %; B0 HO +1,81 %). 6/8 seed > 0, nhưng 1 seed chỉ +618, 2 seed âm (−95, −3 508). Median HO bị kéo bởi 2 seed (+12 356, +11 607).
  2. **DEV không ủng hộ cơ chế "dừng khi burst".** Trên DEV, lệnh TRONG burst có ROI *cao hơn* NGOÀI (1,51 % so với 1,24 % stress). W_burst qua C2 chỉ vì lệnh burst ở HO 2026 âm (−2 007 median). Đây là hiệu ứng riêng HO, không được DEV xác nhận ⇒ nguy cơ may mắn cao.
  3. Ngay cả **không lọc** (toàn bộ lệnh thêm) cũng qua C1 và C3 (DEV ROI_stress 1,28 %, 3/4 năm). Chỉ trượt C2 (HO 4/8 seed, ROI_stress +0,05 %). ⇒ Mọi khác biệt pass/fail nằm ở HO.
  4. Edge lệnh thêm **suy rất mạnh ở HO** với mọi W: ROI_stress HO từ −0,05 % đến +0,18 % cho nhóm NGOÀI.
  5. Năm **2022 âm** ở mọi W và mọi nhóm (median).
  6. HO 2026 đã nhìn lần 2 (lần 1 ở NUP, cho A2 tổng). Ghi vào ledger.
  7. PnL đo trong sổ CHUNG A2 (size theo throttle U chung). Sleeve vốn riêng sẽ có size và đường đi khác.
- **Ngược tiền đề prereg:** "lệnh thêm vào trong sập ΣPnL ≈ 0" không đúng trên DEV. Với W_mkt, nhóm TRONG (ALT_EW 24h ≤ −8 %) là nhóm **tốt nhất**: DEV 2,35 %, HO 2,08 % stress, 8/8 seed HO > 0. Phần sau sóng mới là phần yếu.

## 1. Bảng chính (median 8 seed; DEV 2022–25, HO 2026-01→09; stress = −20 bps khứ hồi trên notional leg)
ROI = ΣPnL/Σnotional. Lệnh = cụm (sym, end), gán theo giờ vào leg đầu (+07).

| W | nhóm | lệnh/năm DEV | ROI DEV % | ROI_stress DEV % | ΣPnL_stress DEV | năm + (/4) | lệnh/năm HO | ROI_stress HO % | ΣPnL_stress HO | seed HO > 0 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 (ref) | tất cả | 719,5 | 3,78 | 3,58 | 107 407 | 4 | 589,6 | 1,81 | 16 377 | 8/8 |
| thêm (không lọc) | tất cả | 1 612,4 | 1,48 | 1,28 | 75 547 | 3 | 1 155,2 | 0,05 | 920 | 4/8 |
| **W_burst** | **NGOÀI** | **1 353,3** | 1,44 | **1,24** | 65 615 | **3** | 1 016,8 | 0,18 | **3 008** | **6/8** |
| W_burst | TRONG | 256,0 | 1,71 | 1,51 | 9 760 | 3 | 138,4 | −1,12 | −2 007 | 3/8 |
| W_mkt | NGOÀI | 1 114,9 | 1,14 | 0,94 | 41 961 | 3 | 1 069,6 | −0,04 | −873 | 4/8 |
| W_mkt | TRONG | 494,0 | 2,55 | 2,35 | 32 847 | 3 | 85,6 | 2,08 | 1 908 | 8/8 |
| W_book | NGOÀI | 1 298,3 | 1,47 | 1,27 | 69 168 | 3 | 973,3 | 0,03 | 494 | 4/8 |
| W_book | TRONG | 311,0 | 1,78 | 1,58 | 6 966 | 2 | 176,5 | 0,11 | 207 | 4/8 |
| W_quiet | NGOÀI (B0 im 24h) | 1 116,5 | 1,39 | 1,19 | 57 136 | 3 | 860,4 | −0,05 | −667 | 3/8 |
| W_quiet | TRONG | 492,4 | 1,86 | 1,66 | 18 388 | 3 | 298,2 | 0,91 | 3 183 | 6/8 |

- "năm +" = số năm 2022–25 có median ΣPnL_stress > 0. Năm 2022 âm ở mọi dòng, trừ B0.
- Từng năm, từng seed: `groups_by_seed.csv`, `groups_median.csv`.

HO W_burst NGOÀI theo seed (ΣPnL_stress):
| seed | 42 | 7 | 13 | 21 | 99 | 123 | 777 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ΣPnL_stress | −95 | 5 235 | 4 282 | 618 | −3 508 | 1 734 | 11 607 | 12 356 |

## 2. Luật S0 (chốt)
- C1 = DEV ROI_stress ≥ 1,0 % VÀ ≥ 3/4 năm dương.
- C2 = HO median > 0 VÀ ≥ 5/8 seed.
- C3 = NGOÀI/năm ≥ 0,5 × B0/năm. B0 = 719,5/năm ⇒ ngưỡng 359,8.

| W | C1 | C2 | C3 (×B0) | Kết luận |
|---|---|---|---|---|
| W_burst | ✓ (1,24 %; 3/4) | ✓ (+3 008; 6/8) | ✓ (1,88×) | **ĐẠT** (biên, xem §0) |
| W_mkt | ✗ (0,94 %) | ✗ (−873; 4/8) | ✓ (1,55×) | TRƯỢT |
| W_book | ✓ (1,27 %; 3/4) | ✗ (+494; 4/8) | ✓ (1,80×) | TRƯỢT |
| W_quiet | ✓ (1,19 %; 3/4) | ✗ (−667; 3/8) | ✓ (1,55×) | TRƯỢT |

Kết luận: chỉ 1 W đạt ⇒ chọn W_burst. Bước tiếp theo theo prereg: prereg NUP3 (sim sleeve vốn riêng), không phải GO tiền thật. Khuyến nghị agent: NUP3 nên pre-register ngưỡng HO chặt hơn "> 0", vì edge HO ở mức ≈ phí.

## 3. Phân bố theo ngày (tập thêm, không lọc; median seed)
Gán theo ngày UTC của giờ vào. "Ngày B0" = ngày UTC có ≥ 1 cụm B0 mở.

| kỳ | % lệnh thêm vào ngày không có B0 | ngày có lệnh thêm/năm (ngày B0 / ngày không B0) | ngày B0/năm | Gini tháng | top-10 tháng % lệnh | corr PnL ngày thêm–B0 | top-10 ngày % ΣPnL thêm | đợt thêm/năm | đợt B0/năm | đợt thêm không giao B0/năm (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 42,3 | 62,0 (26,0 / 35,0) | 30,5 | 0,44 | – | 0,61 | n/a (ΣPnL < 0) | 70,5 | 34,5 | 50,0 (71 %) |
| 2023 | 33,4 | 87,0 (38,0 / 48,5) | 42,5 | 0,30 | – | 0,30 | 51 | 94,0 | 43,5 | 62,0 (66 %) |
| 2024 | 43,4 | 109,7 (40,4 / 70,8) | 40,4 | 0,35 | – | 0,35 | 58 | 127,7 | 43,4 | 95,7 (75 %) |
| 2025 | 54,3 | 91,0 (27,5 / 64,0) | 27,5 | 0,35 | – | 0,23 | 103 | 104,5 | 27,5 | 79,0 (77 %) |
| DEV 22–25 | 44,6 | 87,4 (32,8 / 54,8) | 35,0 | 0,39 | 43,3 (đều = 20,8) | 0,31 | 34 | 99,1 | 37,0 | 71,6 (72 %) |
| HO 2026 | 47,4 | 94,3 (32,8 / 60,8) | 35,4 | 0,26 | (9 tháng, vô nghĩa) | 0,19 | **526** | 102,9 | 36,1 | 70,2 (69 %) |

Đọc bảng:
- **Có rải ra ngày khác.** Khoảng 45 % lệnh thêm rơi vào ngày B0 không có lệnh. Số ngày có lệnh thêm khoảng 87–94/năm, so với 35 ngày/năm của B0. Khoảng 70 % số đợt lệnh thêm không giao đợt B0 nào.
- **Nhưng không đều:**
  - Theo tháng: Gini 0,39; 10/48 tháng chứa 43 % số lệnh.
  - Theo PnL: tập trung mạnh. DEV top-10 ngày chiếm 34 % ΣPnL. HO top-10 ngày = 526 % ΣPnL, tức phần còn lại lỗ ròng; tập thêm HO sống nhờ vài ngày.
- Tương quan PnL ngày với B0: 0,31 (DEV), 0,19 (HO). Năm 2022 là 0,61, nghĩa là năm sập thì lệnh thêm đi cùng B0.
- Mọi ngày trùng B0 gần như luôn có lệnh thêm: ngày B0 có lệnh thêm ≈ ngày B0/năm.

## 4. Validate
| kiểm | kết quả |
|---|---|
| V1 số lệnh thêm + chung = số cụm A2 trong kỳ; chung + mất = số cụm B0 (16 seed×kỳ) | ✓ 51/51 dòng (`validate.csv`) |
| V2 tái lập match NUP mức leg A2-a1 | ✓ 998 / 6 434 / 1 936, khớp cả `score.match_groups` gốc lẫn hàm `match` của S0 |
| Match mức cụm (đơn vị S0) A2-a1 | chung 957 / thêm 6 362 / mất 1 914 (cụm A2 7 319, B0 2 871) |
| V3 kiểm tay độc lập (`indep_check.py`, chỉ csv/datetime, brute force, không import pipeline): seed a1 DEV × W_book + W_quiet, 5 kỳ × 2 nhóm | ✓ 20/20 dòng khớp n và ΣPnL_stress tuyệt đối (`indep_check.txt`) |
| V4 nhân quả: 20 lệnh thêm ngẫu nhiên (a1, rng 20261026) | ✓ 20/20 (`causal_sample.csv`). In t, W_burst, danh sách t0 được đếm (đều < t). Kiểm thêm: max start leg B0 mở < t; max end leg realized < t; cụm B0 24h < t; bar ALT_EW cuối = t−1′ UTC |
| V5 TRONG + NGOÀI = tập thêm (n, PnL, PnL_stress), mọi W×seed×kỳ | ✓ max lệch 0 / 2,9e-11; Σ năm = DEV_T ✓ |
| ALT_EW 2026 | Trùng 2025-10..12 với `edge_attr/index.npz`: 132 477 phút, lệch 0. 2026: 393 111/393 120 phút, thiếu đúng 9 phút đầu tháng, cùng quy ước với DEV. W_mkt NaN = 0; số bar tối thiểu trong cửa sổ 24h = 1 420 (DEV), 1 439 (HO) |
| ts | int64 ms toàn bộ; UTC = +07 − 7h |

## 5. Lệch thiết kế / chi tiết kỹ thuật bổ sung
1. **Đơn vị "lệnh" = cụm (sym, end), giờ vào = leg đầu.** PnL và notional = tổng các leg trong cụm (DCA gộp, ~1,3 % cụm A2 có > 1 leg).
   - NUP match ở mức MỌI leg. S0 match ở mức leg đầu cụm, đúng chữ prereg, CÙNG thuật toán: greedy, cùng sym, |Δt| ≤ 60 s, hoà thì lấy B0 sớm hơn.
   - Vì vậy số "thêm" ở S0 (≈ 6 400/seed DEV) nhỏ hơn số "mới" của NUP (≈ 6 500).
2. **W_burst đếm MỌI cụm A2** (chung + thêm) có t0 ∈ [t−60′, t), không chỉ lệnh thêm. Đọc theo câu "leg đầu cụm mới mà CHÍNH A2 mở".
   - Lệnh cùng phút t không được đếm (strict < t). Hệ quả: các lệnh ở phút đầu của một burst luôn rơi vào NGOÀI.
   - Phân loại "leg đầu cụm" biết được tại t: tại t0 chưa có vị thế cùng sym.
3. **ALT_EW 2026 không chạy kernel mới.** Dùng output có sẵn của kernel PRIVATE `chuyendinh/tsx-ew2026` (TSX HO addendum 737d9faa, 10-20).
   - Kernel đó dùng code `read_month/logret/build_index` trích nguyên văn (ast) từ `edge_attr_build.py`, trên dataset `chuyendinh/vz-kline1m-2026`.
   - File `~/claude_master/tsx/ho/ew_out/ew_2026.npz`, md5 e2e24027…, 10 MB. Kiểm khớp ở §4.
4. **W_mkt:** r24 = exp(Σ ew_r các bar mở trong [t−1440′, t−1′] UTC) − 1, tức close(t−1′)/close(t−1441′) − 1. Phút thiếu thì r = 0.
5. **W_book:**
   - U = Σ notional leg B0 có start < t ≤ end, chia (35 000 + Σ pnl leg B0 end < t).
   - CAP0 = 35 000 cho cả DEV và HO; sim HO cũng chạy liên tục từ 2021-07.
6. **Năm hoá:**
   - DEV tổng chia 4; năm 2024 nhân 365/366.
   - HO nhân 365/273.
   - C3 xét trên DEV. Tỷ lệ HO chỉ mô tả: W_burst 1,72×, W_mkt 1,81×, W_book 1,65×, W_quiet 1,46× B0 HO.
7. **ROI/lệnh** = ΣPnL/Σnotional, như `roi_new` của NUP, không phải trung bình ROI từng lệnh. ROI_stress = ROI − 0,20 pp.
8. **Phân bố ngày:**
   - Tập ngày B0 và các đợt B0 dựng trên toàn lịch sử B0, để không sai ở biên kỳ.
   - Corr và top-10 ngày tính trên mọi ngày UTC của kỳ; ngày không lệnh = 0.
   - Đợt = các t0 liên tiếp cách nhau < 6h. "Không giao" = khoảng đóng [đầu, cuối] của đợt thêm không cắt đợt B0 nào.
   - Top-10 tháng chỉ có nghĩa cho DEV 22–25 (48 tháng).
9. **B0 tham chiếu** = mọi cụm B0 trong kỳ, không chia theo W.

## 6. Ledger
HO 2026: lần dùng thứ 2. Lần 1 ở NUP cho A2 tổng; lần này cho tập con lệnh thêm × 4 định nghĩa W. Không dùng 2026 để chọn ngưỡng: ngưỡng chốt trong prereg.
