# RESULT_OI_STUDY — OPEN INTEREST (OI) như trục dữ liệu CHƯA TỪNG dùng

Ngày đo: 2026-09-23. Pre-reg: `docs/PREREG_OI_STUDY.md` (**commit `7c5f025`**, chốt **TRƯỚC** khi đo;
sau đó **không sửa thiết kế**). Script: `research/analysis/oi_study_build.py` (dựng ma trận),
`research/analysis/oi_study.py` (đo), `research/analysis/oi_study_posthoc.py`,
`research/analysis/oi_study_posthoc2.py` (2 script sau = **POST-HOC/KHAI PHÁ**, có dán nhãn).

Ràng buộc đã tuân: **thuần Python** — **không** Java trên Oracle (shadow đang chạy), **không**
`claude-run`/Claude Code, **không push**, **không chạm HOLDOUT 2026** (mọi cửa sổ `< 2026-01-01`;
ma trận chỉ chứa `≤ 2025-12-31`). Trung gian `/tmp/oi_study/`.

---

## 0. KẾT LUẬN (một dòng mỗi giả thuyết)

> **H1 — ΔOI như factor cross-section: NO-GO (long-only BẤT KHẢ).** Cả 10 decile đều **net âm** ở cả 3
> horizon (1h/4h/24h); decile ΔOI **cao nhất (Q9) là decile TỆ NHẤT**: 24h `-0,4165%`/lệnh
> CI72h_x1.21 `[-0,7044%, -0,1287%]` so với universe EW `-0,2699%` `[-0,5352%, -0,0046%]`.
> Hướng thông tin là **"ΔOI cao ⇒ forward return XẤU"** (chỉ dùng được ở phía short/avoid) — mà
> long-only thì **không có hướng nào khả thi**. **Không đề xuất short, không đề xuất lọc coin.**
>
> **H2 — OI + giá phân kỳ: NO-GO / NULL.** Ô dự đoán (ΔOI cao × P24 thấp) `-0,3021%` **KHÔNG tệ hơn**
> ô (ΔOI cao × P24 cao) `-0,3679%`; tương phản `+0,0658%` **ngược dấu dự đoán** và CI chứa 0
> `[-0,3261%, +0,4576%]`. Ô tệ nhất thực tế là **(ΔOI cao × giá ĐÃ tăng mạnh)**, không phải ô phân kỳ.
>
> **H3 — OI overlay lên MOM15: tách ĐƯỢC (thông tin có thật) nhưng KHÔNG phải GO để lọc coin.**
> Tại entry MOM15 (M-LEVEL k=1, 7 128 sự kiện DEV), tercile **ΔOI cao** `-0,4901%` vs tercile **ΔOI thấp**
> `+5,0174%`; tương phản `-5,5075%` CI72h_x1.21 `[-9,4773%, -1,5376%]`, pNull `0,001`, AUC `0,4011`.
> Đúng hướng ở **cả 3 biến thể** (d24, oiz, rank cross-section). **Nhưng** (a) đây là **split cấp-coin**
> — pre-reg §1.H3 + bài học repo **đã biết mọi filter cấp-coin VÔ HIỆU**; (b) cỡ hiệu ứng chỉ **vừa trên
> MDE** (đo `+5,02%` vs MDE `4,96%`; tương phản `-5,51%` vs MDE `5,15%`). ⇒ **thông tin, KHÔNG lọc coin.**

---

## 1. Cổng tự-kiểm (chạy TRƯỚC khi đọc số)

| Cổng | Kỳ vọng | Vòng này | Đạt |
|---|---|---|---|
| **G1** sha256 `oi_percoin_full.bin` | `e3887f63…b305ec` (`OI_FIX_LOG` §3) | `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` | ✔ |
| **G1b** kích thước = N × 30B, dư 0 | 140 924 110 × 30 | 4 227 723 300 = 140 924 110 × 30, dư **0** | ✔ |
| **G1c** lưới 5m | `ts % 300000 != 0` = 0 dòng | **0** (đo lại trên toàn file) | ✔ |
| **G2** giao symbol raw ∩ OI | — | **627/627** symbol có file `.f32` đều có mặt trong OI | ✔ |
| **G3** neo MOM15 (pre-reg §3b) | `net@0,10% = +1,6690%` ±0,05pp, n = **7 128** | **+1,6690%**, n = **7 128** | ✔ |
| **G4** không có dòng ≥ 2026 trong cửa sổ đo | 0 | **0** (ma trận dừng ở `2025-12-31 23:00`, OI bị lọc `< 2026-01-01`) | ✔ |
| **G5** đối chứng universe EW cùng kỳ | phải có, dùng làm mốc | có (hàng `EW` **mọi** bảng) | ✔ |

---

## 2. Coverage dữ liệu OI (Bước 0 — in trực tiếp từ file)

| mục | giá trị |
|---|---|
| đường dẫn | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` (+ `symbol_map.csv` 863 dòng `symId,symbol`) |
| bản ghi | **140 924 110** × 30 byte (`>i8 ts_ms`, `>i2 symId`, `>f4 ×5`) |
| nhịp | **5 phút**, `ts % 300000 == 0` ở **100%** dòng; **0** ts trùng lặp; file **không** sort theo ts (block theo symbol) |
| khoảng | **2021-01-01 00:00 → 2026-06-30 23:55 UTC** |
| symbol | **779** symId (id 1..828) |
| 5 cột | `oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`, `taker_buy` (`OI_NAMES`) |
| 2 cột **thực sự** là OI | `oi_delta24h(t) = oi[t]/oi[t−24h] − 1` (guard STALE 1h); `oi_z(t)` = z-score **expanding** của **mức** OI. `ls_*`/`taker_buy` **không** phải OI ⇒ **ngoài phạm vi** |
| chiều thời gian | cửa sổ ĐÃ ĐÓNG `[t−5m, t)` ⇒ **CAUSAL** (dấu vết `+5m` đã áp khi build; `OI_FIX_LOG` §2) |
| **đã dùng vào đo** | 109 952 150 dòng OI trong `[2021-12-20, 2026-01-01)` cho **627** symbol |

Giá: `/home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32` — **627** symbol, 619 082 489 dòng,
`2021-01-01 → 2025-12-31 16:59 UTC` (không có 2026). Funding: Aerospike `test/funding_data`, **627/627
symbol đọc được, 0 miss** (chỉ ĐỌC).

**Cửa sổ đo (chốt trước):** DEV = **2022-01-01 → 2025-12-31** = 4,00 năm = 420 768 bước 5m;
lưới cross-section **1 giờ** = **35 064** mốc (`:00` UTC); universe trung bình **257,4** symbol/mốc
(MIN_SYM = 50). IS = 2022-2023, **OOS = 2024-2025** (phán quyết trên OOS).

---

## 3. H1 — ΔOI (`oi_delta24h`) như FACTOR cross-section

Lưới 1h, decile rank tất định, **Q9 = ΔOI cao nhất**. Chi phí CHÍNH = harness (0,10% round-trip +
slip `0,5×range` + funding). DEV, net %/lệnh:

| Q | 24h net | CI72h_x1.21 | 4h net | CI72h_x1.21 | 1h net | CI72h_x1.21 |
|---|---|---|---|---|---|---|
| Q0 | −0,2653% | [−0,5267, −0,0038] | −0,2507% | [−0,3008, −0,2006] | −0,2446% | [−0,2588, −0,2303] |
| Q1 | −0,2299% | [−0,4939, +0,0342] | −0,2149% | [−0,2641, −0,1657] | −0,2156% | [−0,2296, −0,2017] |
| Q2 | **−0,2144%** | [−0,4742, +0,0455] | **−0,2060%** | [−0,2554, −0,1566] | −0,2076% | [−0,2214, −0,1938] |
| Q3 | −0,2225% | [−0,4879, +0,0428] | −0,2074% | [−0,2565, −0,1582] | −0,2067% | [−0,2207, −0,1927] |
| Q4 | −0,2419% | [−0,5055, +0,0217] | −0,2108% | [−0,2605, −0,1611] | −0,2080% | [−0,2215, −0,1946] |
| Q5 | −0,2458% | [−0,5148, +0,0233] | −0,2131% | [−0,2635, −0,1628] | −0,2089% | [−0,2225, −0,1952] |
| Q6 | −0,2691% | [−0,5377, −0,0004] | −0,2172% | [−0,2664, −0,1681] | −0,2106% | [−0,2244, −0,1967] |
| Q7 | −0,2895% | [−0,5537, −0,0253] | −0,2232% | [−0,2726, −0,1737] | −0,2157% | [−0,2294, −0,2020] |
| Q8 | −0,3064% | [−0,5715, −0,0413] | −0,2367% | [−0,2857, −0,1877] | −0,2279% | [−0,2410, −0,2149] |
| **Q9** | **−0,4165%** | **[−0,7044, −0,1287]** | **−0,3402%** | **[−0,3954, −0,2850]** | **−0,3191%** | **[−0,3341, −0,3041]** |
| **EW (universe)** | −0,2699% | [−0,5352, −0,0046] | −0,2319% | [−0,2811, −0,1827] | −0,2264% | [−0,2399, −0,2128] |
| N (Q9) | 884 377 | N_eff **9 545** | 886 255 | N_eff **49 562** | 886 612 | N_eff **169 944** |

- **Chênh Q_d − EW (24h, pp/lệnh):** Q0 +0,005 · Q1 +0,040 · Q2 **+0,056** · Q3 +0,047 · Q4 +0,028 ·
  Q5 +0,024 · Q6 +0,001 · Q7 −0,020 · Q8 −0,037 · **Q9 −0,147**. Pattern đơn điệu ở **nửa trên**
  (ΔOI càng cao ⇒ càng tệ).
- **OOS (2024-2025):** EW −0,2948%; Q9 −0,150pp; Q0 +0,011 · Q1 +0,041 · Q2 +0,060 · Q3 +0,045.
- **Không decile nào net > 0** ở bất kỳ horizon nào ⇒ **long-only không có hướng khả thi**.
- **Biến thể đã đăng ký (24h, Q9):** `d24` −0,4165% `[−0,7044,−0,1287]`; `dd24_1h` −0,3561%
  `[−0,6329,−0,0794]`; `dd24_4h` −0,3651% `[−0,6508,−0,0794]`; `oiz` −0,3010% `[−0,5498,−0,0522]`.
  **4/4 biến thể cùng dấu** (Q9 âm) và **4/4 Q9−EW âm** ⇒ không có mâu thuẫn biến thể.
  Riêng `Q9 − EW` của từng biến thể **CI đều chứa 0** (d24 `[−0,5388,+0,2455]`; dd24_1h
  `[−0,4725,+0,2990]`; dd24_4h `[−0,4824,+0,2911]`; oiz `[−0,3857,+0,3239]`) — tức **hiệu ứng TƯƠNG ĐỐI
  nằm dưới MDE**, chỉ **mức tuyệt đối của Q9** là CI ngoài 0.
- **Nhất quán quý (Q9, 24h):** q+ OOS **25%** (2/8), y+ ALL **0%** (0/4) ⇒ **không đạt** ngưỡng ≥60%.
- **`%coin+` (chỉ số pre-reg §2 khai báo sẽ báo; POST-HOC #3):** H1 24h — **Q9: 25,0%** (155/620 symbol),
  **EW: 13,7%** (85/620). Cả hai **≪ 60%**. Đáng chú ý: Q9 có **TỈ LỆ coin lãi CAO HƠN** EW (25% vs 13,7%)
  nhưng **mean vẫn tệ hơn** — vì đuôi thua dài hơn (coin biến động cao); điều này củng cố kết luận
  "EW net âm là **hiện tượng CHI PHÍ**, không phải market".

**Loại trừ nhầm lẫn (POST-HOC, mô tả — `oi_study_posthoc.py`):** phân ra chi phí (24h, DEV) thấy
phần lớn "hình phạt Q9" **đến từ SLIP**, không phải từ alpha:

| nhóm | gross (raw) | −fee | −slip | −funding | = net |
|---|---|---|---|---|---|
| Q9 | −0,1068% | −0,1000% | **−0,2097%** | −0,0000% | −0,4165% |
| Q0 | −0,0207% | −0,1000% | −0,1446% | −0,0000% | −0,2653% |
| EW | −0,0453% | −0,1000% | −0,1246% | −0,0000% | −0,2699% |

Q9−EW = −0,1466pp ⇒ **−0,0615pp từ gross** (thông tin thật, **dưới MDE 0,2933%**) và **−0,0851pp từ
slip** (Q9 = nhóm coin **biến động cao**: med `rg5/c5` Q9 = **0,307%** vs Q5 = 0,179%). Bản thân
universe EW cũng đã net âm vì fee+slip (0,225%) lớn hơn drift gross (−0,045%).

---

## 4. H2 — OI + GIÁ PHÂN KỲ (tercile 3×3, 24h)

Net %/lệnh, `[hàng = tercile ΔOI (0 thấp → 2 cao), cột = tercile P24 = giá 24h qua (0 thấp → 2 cao)]`:

| | P24_ter0 | P24_ter1 | P24_ter2 |
|---|---|---|---|
| **ΔOI_ter0** | −0,2574% (N 1 634 429) | −0,1888% (N 914 154) | −0,2373% (N 455 528) |
| **ΔOI_ter1** | −0,2087% (N 873 729) | −0,2402% (N 1 317 390) | −0,2893% (N 801 024) |
| **ΔOI_ter2** | −0,3021% (N 495 953) | −0,2563% (N 760 599) | **−0,3679%** (N 1 724 597) |

- Tương phản chính: **(ter2,ter0) − (ter2,ter2) = +0,0658%** CI72h_x1.21 `[−0,3261%, +0,4576%]`,
  p(diff>0) `0,646` ⇒ **ngược dấu dự đoán và không có ý nghĩa** ⇒ **giả thuyết KHÔNG được ủng hộ**.
- (ter2,ter0) − EW = −0,0335% `[−0,4215, +0,3544]`; (ter2,ter2) − EW = −0,0993% `[−0,4813, +0,2827]`;
  (0,0) − EW = +0,0112% `[−0,3650, +0,3873]`. **Mọi ô đều net âm**; ô CI ngoài 0 (âm) là
  (2,0) `[−0,5951,−0,0091]` và (2,2) `[−0,6446,−0,0912]` — tức **ΔOI cao thì tệ, bất kể giá**.
- ⇒ **NO-GO / NULL** cho cơ chế "phân kỳ OI-giá".

---

## 5. H3 — OI OVERLAY LÊN MOM15 (M-LEVEL k=1)

Bộ sự kiện: MOM15 đang chạy live (`ml_min`/`ml_sym`, 11 367 ALL / **7 128 DEV**), HOLD 24h.
**Coverage tra OI causal: 7 128/7 128 = 100%** (tolerance 15 phút; `d24` finite 98,7%, `oiz` 99,9%,
rank cross-section 98,7%, 1 012 mốc giờ).

| tách theo | ter0 (OI thấp) | ter1 | ter2 (OI cao) | ter2 − ter0 | AUC(win) |
|---|---|---|---|---|---|
| **`d24` (mức)** | **+5,0174%** `[+1,2218,+8,8130]` pNull 0,001 | +0,5225% `[−0,8710,+1,9160]` | **−0,4901%** `[−1,8440,+0,8639]` | **−5,5075%** `[−9,4773,−1,5376]` p(diff>0)=**0,001** | **0,4011** |
| **`oiz` (mức)** | +3,4522% `[+0,9340,+5,9705]` pNull 0,000 | +0,7253% `[−0,7539,+2,2044]` | +0,8378% `[−0,8776,+2,5533]` | −2,6144% `[−5,6265,+0,3977]` p=0,015 | 0,4362 |
| **`rank_d24` (cs)** | +2,4836% `[+0,8872,+4,0799]` pNull 0,000 | +1,8192% `[−0,0769,+3,7153]` | +0,7666% `[−1,3888,+2,9221]` | −1,7169% `[−4,3103,+0,8764]` p=0,059 | 0,4520 |

- **Tách ĐƯỢC**: đúng hướng ở **cả 3 biến thể**; `d24` cho tương phản CI **ngoài 0** (âm).
  AUC < 0,5 ⇒ OI **dự báo NGƯỢC** (ΔOI cao ⇒ xác suất thắng thấp).
- **OOS & nhất quán ter0:** `d24` ter0 OOS **+7,2290%**, q+OOS **88%** (7/8), y+ALL **100%** (4/4);
  `oiz` ter0 OOS +4,5806%, q+OOS 88%; `rank` ter0 OOS +3,0119%, q+OOS 88%. N (ter0) = 2 345 mỗi biến thể;
  **N_eff ≈ N** (ICC72 ≈ −0,01 … +0,0 ⇒ **không cum theo block 72h**; ter0 `d24`: N_eff 2 604 / nblk 201).
- **NHƯNG cỡ hiệu ứng chỉ VỪA trên MDE** (`oi_study_posthoc.py` §1): MDE(p80) ter0 `d24` = **4,9624%**
  vs đo **+5,0174%**; tương phản ter2−ter0 MDE (ước lượng đường chéo) = **5,1496%** vs đo **−5,5075%**;
  ter2 `d24` MDE 1,3744% vs đo −0,4901% ⇒ **ter2 một mình KHÔNG tách khỏi 0**.
- **Kiểm tra nhầm lẫn (POST-HOC #2, KHAI PHÁ — không thuộc pre-reg):** OI có thể chỉ là proxy cho
  **độ sâu cú rơ** (biến MOM15 dùng để chọn coin, `d15`). Đo được:
  `spearman(d24_entry, d15_entry) = −0,171` (yếu). Bảng 3×3 [d15 × ΔOI]: trong **từng** tercile d15,
  ΔOI **vẫn tách** (chenh ter2−ter0 = **−10,43%** / −1,24% / −3,43%). Vậy OI **không** thuần là proxy
  của độ sâu cú rơ — nhưng quan hệ **nhiễu** và tương tác mạnh.

---

## 6. Null test + MDE

| chuỗi | N | half-width ×1,21 | **MDE(p80)** | 2,8×SD(null) | p_perm (block sign-flip 72h) |
|---|---|---|---|---|---|
| H1 24h Q9 | 884 377 | 0,2878% | **0,2933%** | 0,3452% | 1,0000 (null ≥ obs ⇒ đúng dấu âm cực trị) |
| H1 24h EW | 8 987 683 | 0,2653% | 0,2682% | 0,3116% | 0,9930 |
| H1 4h Q9 | 886 255 | 0,0552% | 0,0694% | 0,0806% | 1,0000 |
| H1 1h Q9 | 886 612 | 0,0150% | 0,0427% | 0,0501% | 1,0000 |
| H3 `d24` ter0 (ΔOI thấp) | 2 345 | 3,7956% | **4,9624%** | — | 0,0010 |

- **H1:** hiệu ứng **tương đối** Q9−EW (−0,1466pp) **< MDE 0,2933%** ⇒ **dưới ngưỡng phát hiện**;
  hiệu ứng **tuyệt đối** Q9 (−0,4165%) **> MDE** nhưng đó là *mức* của một nhóm (bị slip chi phối).
- **H3:** ter0 `d24` (+5,0174%) **> MDE 4,9624%** — **vừa qua**; tương phản (−5,5075%) > MDE 5,1496% — **vừa qua**.
- Null (block sign-flip 72h) **không** sinh giá trị ≥ obs ở mọi chuỗi âm (p_perm ≈ 1,0) ⇒ kiểm định
  permutation **khớp** với CI; các hiệu ứng **DƯƠNG** của H3 ter0 có pNull 0,000-0,001.

**N / N_eff (đơn vị OI event cum theo thời gian):** H1 lưới 1h ⇒ mỗi giờ là một event cho ~257 coin,
nên **N cực lớn nhưng cum mạnh**: ví dụ Q9 24h có N = 884 377 trong khi **N_eff = 9 545** (ICC72 = 0,050,
nblk = 487); EW 24h N = 8 987 683 → **N_eff = 4 623** (ICC72 = 0,105). Đây là **kỳ vọng**, không phải lỗi.
H3 thì ngược lại: **không cum** (ICC72 ≈ 0 ⇒ N_eff ≈ N).

---

## 7. Đối chứng

- **(a) Universe equal-weight cùng kỳ:** có, in ở **mọi** bảng (`EW`). Là mốc bắt buộc — và chính EW
  cũng **net âm** (−0,2699% ở 24h) vì fee 0,10% + slip 0,1246% > drift gross −0,0453%. Mọi so sánh
  decile/tercile đều là **chênh so với EW của đúng mốc đó**.
- **(b) Neo MOM15:** **TÁI LẬP ĐÚNG** — `net@0,10% = +1,6690%`, n = **7 128** (kỳ vọng +1,6690%,
  `RESULT_COST_LIQUIDITY` G4) ⇒ bộ đo **còn lực**, mọi số ở trên **không bị VOID**.
  Nguồn: ledger M-LEVEL `m_raw/m_slip/m_fund` của vòng trước (`/tmp/funding_factor/pools.npz`,
  `holds = [240, 1440, 4320]`), tức **đúng bộ số đã sinh ra con số neo**; đã đối chiếu `n = 7 128` và
  `base = +1,7690%` trước khi trừ phí.
- **Mô hình chi phí ghi rõ:** CHÍNH = harness (`fee 0,10%` round-trip = taker 0,05% × 2 chân;
  `slip = 0,5·(high−low)/close` nến 1m lúc vào; `funding` = tổng rate event trong `(t, t+H]`) — **đúng
  bằng** mô hình đã dùng cho neo MOM15 và `harness_control.py`. BIẾN THỂ = mô hình sim **0,80%** phẳng
  (`RESULT_COST_LIQUIDITY` §1 nói mô hình này **đắt 4-20×** thực tế). Vì phí CHÍNH đã cao hơn thực tế,
  một kết quả âm ở phí CHÍNH **không** có nghĩa "sẽ dương nếu phí thật rẻ hơn": riêng ở H1, phần
  **gross** đã âm/không đáng kể (Q9−EW gross = −0,0615pp, dưới MDE).

---

## 8. KẾT LUẬN GO / NO-GO

| # | Giả thuyết | GO? | Lý do (theo luật pre-reg §4) |
|---|---|---|---|
| **H1** | ΔOI factor cross-section, long-only | **NO-GO (long-only bất khả)** | Fail (1) mọi decile OOS < 0 sau phí; fail (3) q+OOS Q9 = 25% < 60%; hiệu ứng tương đối < MDE. Hướng thông tin "ΔOI cao ⇒ xấu" **chỉ dùng được phía short/avoid** — **không đề xuất**. |
| **H2** | OI + giá phân kỳ | **NO-GO / NULL** | Tương phản dự đoán **ngược dấu** (+0,0658%) và CI chứa 0; ô tệ nhất là (ΔOI cao × giá đã tăng). |
| **H3** | OI overlay lên MOM15 | **TÁCH ĐƯỢC (thông tin) — KHÔNG GO để lọc coin** | Đạt (1)(2)(3)(4) cho nhóm ter0 (`+5,02%`, CI ngoài 0, q+OOS 88%, 3/3 biến thể cùng dấu) **nhưng** đây là **split cấp-coin**: pre-reg §1.H3 + bài học repo ⇒ **mọi filter cấp-coin VÔ HIỆU**; và cỡ hiệu ứng **vừa trên MDE**. |

**Điều KHÔNG được làm (chốt):** **không** đề xuất áp dụng/tích hợp; **không** đề xuất short H1;
**không** đề xuất lọc/exclude coin (kể cả "loại Q9" hay "chỉ vào MOM15 khi ΔOI thấp") — đã biết vô
hiệu ở tầng hệ thống; **không** tune tham số nào từ các số trên. Các quan hệ **dương** của H3 ter0
được ghi lại như **thông tin** (có thể dùng làm **đặc trưng** cho model ở vòng sau, nếu muốn), **không**
phải như một luật vào lệnh.

---

## 9. Phụ lục — điểm cần theo dõi / giới hạn đã biết

- File OI **không chứa mức OI thô** và **không chứa ΔOI cửa sổ ngắn** (1h/4h) ⇒ "ΔOI causal" khả dụng
  chỉ là `oi_delta24h` và các **sai phân** của nó, cộng `oi_z`. Giới hạn này **chốt trước** ở pre-reg §0.1.
- Q9 (ΔOI cao) = nhóm **biến động cao** (med `rg5/c5` 0,307% vs 0,179%) ⇒ "hình phạt Q9" **~58% là slip**.
  Đây là **post-hoc/khai phá**, không đổi kết luận.
- 2021 (warm-up) và **2026 (HOLDOUT) không được đọc vào thống kê**; kiểm bằng G4 (= 0 dòng ≥ 2026).
- Trung gian `/tmp/oi_study/` (5 ma trận + report) **đã dọn** sau khi commit.
