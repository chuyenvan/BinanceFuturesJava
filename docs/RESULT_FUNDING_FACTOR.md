# RESULT_FUNDING_FACTOR — funding rate như (a) FACTOR cross-section và (b) THÀNH PHẦN CHI PHÍ

Ngày: 2026-09-22. Pre-reg: `docs/PREREG_FUNDING_FACTOR.md` (**commit `17d600a`**, chốt TRƯỚC khi chạy;
sau đó **không sửa thiết kế**). Script: `research/analysis/funding_coverage.py` (Bước 0),
`funding_factor.py` (sinh mẫu + MOM15), `funding_factor_stats.py` (thống kê),
`funding_factor_diag.py` + `funding_factor_extra.py` (DESCRIPTIVE post-hoc).
**Thuần Python**, 0-sim, **không** chạy Java trên Oracle (job shadow), **không** `claude-run`, **không push**,
**không chạm HOLDOUT 2026**.

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 3 giả thuyết.** Chỉ **H1 (funding là khoản chi phí, biết trước và dai dẳng — Spearman
> `f_entry`→`f_cum` = 0,60 ở 24h) là ĐÚNG về cơ chế**: coin funding cao (D10) thật sự tốn hơn D1
> **+0,4795%/24h / +1,0576%/72h** và net 24h của D10−D1 = **−0,2525%** (CI72h×1.21 **[−0,3974%,
> −0,1076%]**, p<0,0001, vượt cả Bonferroni-3, MDE 0,20%) — **nhưng KHÔNG đạt cổng xác nhận đã khoá**
> (dấu chỉ đúng ở **54,9%** số phút / **56,9%** số block < mốc 60%). **H2 (factor cross-section long-only)
> = NULL**: decile funding thấp nhất (D1) net 24h **−0,1913%**, CI chứa 0 (p(>0)=0,05), IC trung bình
> **+0,0009** ≈ 0; **H3 (overlay lên MOM15) = NULL ở cổng khoá**: tại phút MOM15 fire, net(f_entry ≤ 0)
> − net(f_entry > 0) = **+0,9482%** nhưng CI72h×1.21 **[−0,0127%, +1,9090%]** chứa 0, p=0,0175 > 0,0167
> (Bonferroni-3), MDE **2,00%** > hiệu ứng, và ở 4h dấu **ngược** (−0,1492%). **Không đề xuất áp dụng gì.**

## 1. Tuân thủ + kiểm chứng tái tạo (harness còn lực)

| Kiểm chứng | Vòng này | Tham chiếu đã công bố | Khớp |
|---|---|---|---|
| `total_rows` cross-section `d15` | **619 073 711** | `RESULT_HARNESS_CONTROL.md` §1 | ✔ |
| Phút MOM15 (`rd15 < −0,028`, `cnt ≥ 50`) | **13 150** | `RESULT_LEVEL_SENSITIVITY.md` §0b | ✔ |
| M-LEVEL MOM15 `k=1` (ALL) | **11 367** | idem | ✔ |
| M-LEVEL MOM15 `k=1` (DEV) | **7 128** | idem | ✔ |
| MOM15 `k=1` DEV 24h phí 0,10% (net) | **+1,6690%** | **+1,6431%** | ✔ (lệch 0,026pp) |
| MOM15 `k=1` ALL 24h phí 0,10% (net) | **+2,2622%** | `RESULT_HARNESS_CONTROL.md` §2 "**+2,26%**" | ✔ |
| `N_blk` (block-72h) MOM15 DEV | **301** | idem | ✔ |

⇒ **Bộ đo tái tạo đúng neo MOM15** (sai khớp 0,026pp = 1 dòng short-delist + mép cửa sổ funding
`(m_e, m_x]`; pre-reg §7 ghi nhầm "+1,5931% @0,10%" — con số **1,5931% là ở phí 0,15%**, không đổi
thiết kế/cổng). **Không VOID.**

**Hai lỗi cài đặt đã phát hiện và sửa TRƯỚC khi chốt số** (ghi lại để truy vết; không đổi thiết kế):
(i) vòng MOM15 dùng lẫn **phút tương đối vs phút epoch** ⇒ pool P-COIN/M-LEVEL rỗng; (ii) **lệch thứ tự
dòng** (metadata theo thời gian, returns theo symbol) ⇒ ghép sai cặp ⇒ T3/neo bị thổi lên. Bản chốt số
đã đồng bộ (`assert` căn dòng trong script) và chính **kiểm chứng neo ở bảng trên** là bằng chứng bản
chốt đúng.

## 2. BƯỚC 0 — coverage dữ liệu funding (đã xác minh TRƯỚC khi thiết kế)

Nguồn: Aerospike `test.funding_data` (chỉ đọc), bin `f_data` = **Snappy(JSON `{ts_ms: rate}`)**
(đúng `DataManagerAerospikeFloatSim.writeFundingMap`; `AEROSPIKE_SET_NAME_FUNDINGFEE = "funding_data"`).

| Mục | Kết quả |
|---|---|
| Symbol | **831** record, decode OK **831/831** |
| Event | **2 394 587** (median 2 754/symbol, max 9 040) |
| Khoảng | 2021-01-01 00:00 UTC → **2026-08-05** (chỉ dùng ≤ 2025-12-31) |
| Tần suất | **hỗn hợp**: 476 symbol cadence trung vị **4h** (00/04/08/12/16/20 UTC), 345 symbol **8h** (00/08/16); BTC/ETH/SOL 8h suốt 2021–2025 |
| Giao universe | 627 symbol có `raw/<sym>.f32` (subset) |
| Rác | 3 symbol có ts = 0/âm (`GAIBUSDT`, `GRAMUSDT`, `STPTUSDT`) ⇒ đã lọc `ts ≥ 2021-01-01` |

**Cách đặt vấn đề — không đếm hai lần:** `net = raw − phí exchange − slip − f_cum`.
`f_entry` = rate của event funding cuối cùng có `ts ≤ m_e` (rate **đã biết** lúc vào lệnh) = **predictor**;
`f_cum` chỉ cộng các event có `ts ∈ (m_e, m_x]` ⇒ **event tại `m_e` không nằm trong `f_cum`** ⇒ không
trùng với phí exchange và không tự tương quan với chính nó.

## 3. H1 — funding như THÀNH PHẦN CHI PHÍ

### 3.1 Grid A (mẫu = (symbol, event funding của chính nó))

**N = 1 747 993** (DEV 1 628 844); phút funding duy nhất **12 782**; phút đủ ≥50 symbol **7 685**
(median **184 symbol/phút**); **81,0%** `f_entry > 0`; mean `f_entry` = 0,0014%/kỳ (median 0,0050%).

### 3.2 Bảng decile (DEV, net CHƯA trừ phí) — HOLD 24h

| decile | N | `f_entry` mean | raw | slip | **f_cum** | net | net @0,10% |
|---|---|---|---|---|---|---|---|
| D1 (thấp nhất) | 169 012 | −0,0714% | −0,1877% | 0,2123% | **−0,4053%** | **+0,0053%** | −0,0947% |
| D2 | 161 582 | −0,0044% | −0,0733% | 0,1363% | −0,0419% | −0,1677% | −0,2677% |
| D3 | 163 579 | +0,0015% | −0,0664% | 0,1317% | −0,0132% | −0,1850% | −0,2850% |
| D4 | 162 004 | +0,0047% | −0,0612% | 0,1324% | +0,0069% | −0,2006% | −0,3006% |
| D5 | 161 280 | +0,0064% | −0,0429% | 0,1342% | +0,0132% | −0,1903% | −0,2903% |
| D6 | 164 641 | +0,0073% | −0,0108% | 0,1349% | +0,0147% | −0,1604% | −0,2604% |
| D7 | 163 500 | +0,0085% | −0,0537% | 0,1320% | +0,0214% | −0,2071% | −0,3071% |
| D8 | 162 083 | +0,0095% | −0,0899% | 0,1294% | +0,0246% | −0,2439% | −0,3439% |
| D9 | 163 078 | +0,0111% | −0,0529% | 0,1312% | +0,0286% | −0,2126% | −0,3126% |
| D10 (cao nhất) | 158 085 | +0,0223% | −0,0112% | 0,1665% | **+0,0742%** | **−0,2519%** | −0,3519% |
| **D10−D1** | | | **+0,1765%** | **−0,0457%** | **+0,4795%** | **−0,2572%** | −0,2572% |

- **Persistency (cơ chế chính, ĐÚNG):** `Spearman(f_entry, f_cum)` = **0,5970** (24h) / 0,3936 (4h) /
  0,5649 (72h) ⇒ funding tại entry dự báo được funding phải trả. D10 trả **+0,0742%**/24h và
  **+0,1695%**/72h; D1 **thu** **−0,4053%**/24h và **−0,8881%**/72h.
- **Net spread (minute-chain, equal-weight trong decile, DEV):**

| test | HOLD | phí | N_phút | N_blk | net | CI72h×1.21 | p | Bonf3 CI |
|---|---|---|---|---|---|---|---|---|
| T1 spread D10−D1 | 4h | 0,10% | 6 590 | 487 | **−0,1494%** | [−0,1841%, −0,1148%] | 0,0000 | [−0,1833%, −0,1117%] |
| **T1 spread D10−D1** | **24h** | **0,10%** | 6 585 | 487 | **−0,2525%** | **[−0,3974%, −0,1076%]** | **0,0000** | **[−0,3952%, −0,0967%]** |
| T1 spread D10−D1 | 72h | 0,10% | 6 573 | 486 | −0,2517% | [−0,6029%, +0,0994%] | 0,0505 | [−0,6025%, +0,1063%] |

- **Kết luận H1:** cơ chế **ĐÚNG và đo được** (chi phí funding **biết trước**, dai dẳng, chênh
  D10−D1 ≈ **0,48%/24h, 1,06%/72h**), và net spread 24h **âm có ý nghĩa** (vượt cả Bonferroni-3, MDE
  0,20%). **Nhưng KHÔNG đạt cổng xác nhận đã khoá** vì **kỷ luật dấu**: chỉ **54,9%** số phút (DEV) /
  **56,9%** số block-72h / **56,4%** số ngày có dấu đúng (< mốc 60% của pre-reg §6). Theo luật §6 ⇒
  **NO-GO / UNCONFIRMED**: hiệu ứng có thật về **trung bình** nhưng **không ổn định theo từng lát cắt
  thời gian**, và biên độ (0,25%/24h) **nhỏ hơn sai số chi phí ước lượng**.

### 3.3 Định lượng (b) — funding chiếm bao nhiêu trong chi phí?

| HOLD | mean `f_cum` toàn universe (DEV) | D1 | D10 | so sánh |
|---|---|---|---|---|
| 4h | **−0,0062%** (thu nhập) | −0,0870% | +0,0153% | slip 0,13–0,21% > fee 0,05–0,15% ≫ funding |
| 24h | **−0,0294%** (thu nhập) | −0,4053% | +0,0742% | funding vẫn **nhỏ hơn** slip/fee cho D1–D9 |
| 72h | **−0,0743%** (thu nhập) | −0,8881% | +0,1695% | ở 72h funding **bắt đầu so được** với fee |

⇒ **Kết luận (b): funding là số hạng chi phí BẬC HAI ở HOLD 24h** (|mean| ≤ 0,03%/lệnh; chỉ decile cực
đoan mới tới ~0,07–0,17%); **KHÔNG phải nguồn drag đáng kể** như slip (0,13–0,21%) hay fee (0,10%).
Số này **nhất quán** với `reversal-bounce` (funding −0,019%/lệnh ở hold ngắn, `rvb_1m/POWER_WALL.md`).

## 4. H2 — funding như FACTOR cross-section (hướng long-only)

| test | HOLD | phí | N_phút | N_blk | net (D1) | CI72h×1.21 | p(>0) | Bonf3 CI |
|---|---|---|---|---|---|---|---|---|
| T2 long-only D1 | 4h | 0,10% | 6 590 | 487 | **−0,2487%** | [−0,3039%, −0,1935%] | 0,000 | [−0,3029%, −0,1878%] |
| **T2 long-only D1** | **24h** | **0,10%** | 6 585 | 487 | **−0,1913%** | **[−0,4683%, +0,0857%]** | **0,050** | [−0,4722%, +0,0980%] |
| T2 long-only D1 | 72h | 0,10% | 6 573 | 486 | −0,1753% | [−0,8387%, +0,4882%] | 0,283 | [−0,8542%, +0,5284%] |

- **NULL.** D1 (funding thấp/âm nhất) **đúng là tốt nhất** trong bảng decile (net trước phí 24h
  **+0,0053%** so với −0,16…−0,25% các decile khác; 72h **+0,2335%** vs âm) **nhưng KHÔNG tự sống qua
  chi phí** (24h sau phí **−0,0947%**, CI chứa 0).
- **IC cross-section (Spearman `f_entry` vs net, từng phút, 24h):** DEV **+0,0009**, CI72h×1.21
  [−0,0041, +0,0060] ⇒ gần như **không có thông tin tuyến tính**; p50 = +0,0029, p10/p90 = ∓0,125.
- `%coin+` của D1 (DEV, ≥10 trade): **33,2%** — tức **66,8% symbol thua lỗ** khi chỉ mua funding thấp.
- Theo năm (net 24h @0,10%): Y2022 −0,35% / Y2023 +0,09% / Y2024 −0,17% / Y2025 −0,06% ⇒ **không có năm
  nào dương đáng kể**; 2021 (ngoài DEV) +0,86%.
⇒ **NO-GO.** Funding **không** dùng được như factor long-only (chỉ chứa thông tin "tránh" chứ không
chứa thông tin "mua").

## 5. H3 — overlay lên MOM15 (câu hỏi quyết định)

**T3 (pool P-COIN MOM15: mọi coin trong cross-section tại phút fire; DEV 2 346 349 dòng, 621 symbol).**
Tại phút MOM15 fire (= phút dump), **76,7%** coin có `f_entry > 0`.

| HOLD | phí | N(≤0) | N(>0) | net(≤0) | net(>0) | **diff** | CI72h×1.21 | p | Bonf3 CI |
|---|---|---|---|---|---|---|---|---|---|
| 4h | 0,10% | 578 035 | 1 760 414 | +0,2096% | +0,2588% | **−0,1492%** | [−0,8063%, +0,5078%] | 0,5650 | [−0,7716%, +0,4695%] |
| **24h** | **0,10%** | 578 035 | 1 760 414 | +2,3712% | +1,3231% | **+0,9482%** | **[−0,0127%, +1,9090%]** | **0,0175** | [−0,0022%, +2,0539%] |
| 24h | 0,05% | 578 035 | 1 760 414 | +2,4212% | +1,3731% | +0,9982% | [+0,0373%, +1,9590%] | — | [+0,0478%, +2,1039%] |
| 72h | 0,10% | 578 035 | 1 760 414 | +4,7777% | +3,2499% | +1,4277% | [−0,1695%, +3,0250%] | 0,0895 | [−0,3642%, +2,8816%] |

- **NULL ở cổng khoá:** ở phí 0,10% CI **chứa 0**; `p = 0,0175` **> 0,0167** (Bonferroni-3); **MDE 2,00%**
  > hiệu ứng 0,95% ⇒ **không phân giải được**; và ở **4h dấu NGƯỢC** (−0,1492%) ⇒ không nhất quán
  theo HOLD. (Ghi nhận trung thực, **không** dùng để tuyên bố: ở phí 0,05% CI **vừa** ra khỏi 0 —
  đây là biên độ fee-sensitivity, không phải bằng chứng.)
- **Descriptive — T3 phân tầng (post-hoc, `funding_factor_extra.py`)**: sau khi điều kiện hoá theo
  **(phút fire × decile `d15`)**, diff tụt còn **+0,1967%** (CI [−0,1168%, +0,5103%], p=0,938);
  cell dương 51,5%; theo decile `d15`: D1–D3 **âm**, D4–D9 +0,15…+0,28%, **D10 (dump sâu nhất) +1,27%**.
  `Spearman(f_entry, d15)` tại phút fire = **−0,0019** (≈0) ⇒ funding **không** phải proxy tuyến tính
  của độ sâu dump. ⇒ Phần lớn "+0,95%" của T3 là **hiệu ứng thành phần theo độ sâu dump**, không phải
  tín hiệu funding độc lập; chỉ nhóm dump sâu nhất còn dư địa (và nhóm đó **nhỏ, nhiễu nhất**).
- **H3b (M-LEVEL MOM15 `k=1`, đúng live — THIẾU LỰC, chỉ descriptive):** `f_entry ≤ 0` N=1 726 net
  **+1,9794%** vs `f_entry > 0` N=5 356 net **+1,5749%**; diff **+0,4045%**, CI [−2,03%, +2,83%],
  p=0,415. Bản "lọc bỏ `f_entry > 0`" = **+1,9794%** (CI [−0,002%, +3,961%]) so với gốc **+1,6690%**
  ⇒ **không xác nhận được** (N≈1,7k, **MDE 2,00%**).
⇒ **NO-GO.** Không có bằng chứng đủ mạnh rằng funding tại entry **tách được** lệnh thắng/thua của
MOM15; hiệu ứng thô có vẻ dương ở 24h/72h nhưng **không vượt MDE**, **không qua Bonferroni-3**,
**ngược dấu ở 4h**, và **biến mất khi kiểm soát độ sâu dump**. Điều này **nhất quán với phát hiện
"edge nằm ở TIMING"**: phần dương của MOM15 đến từ **thời điểm** (cả cross-section cùng bật), không
đến từ việc lọc theo funding.

## 6. MDE / power (DEV, HOLD 24h, chuỗi đã trừ phí — phí là dịch hằng số nên MDE bất biến)

| test | N | N_blk | h_r p50 | h_r p80 | power@0,5% | @1% | @2% | **MDE(80%)** |
|---|---|---|---|---|---|---|---|---|
| T1 spread D10−D1 | 6 585 phút | 487 | 0,1400% | 0,1510% | 1,00 | 1,00 | 1,00 | **0,20%** |
| T2 long-only D1 | 6 585 phút | 487 | 0,2689% | 0,2884% | 1,00 | 1,00 | 1,00 | **0,50%** |
| T3 diff (≤0 − >0) | 578 035 / 1 760 414 | 301 | 0,9105% | 1,1511% | 0,01 | 0,63 | 1,00 | **2,00%** |
| H3b MOM15 `k=1` | 7 128 | 301 | — | 1,8027% | — | — | — | **2,00%** |

**Đọc MDE cho đúng:** T1/T2 phân giải được hiệu ứng **≤ 0,5%** — nghĩa là **NULL của T2 là NULL THẬT**
(không phải thiếu lực) **trong phạm vi ≤ ~0,5%/lệnh**. Ngược lại **T3/H3b chỉ phân giải ≥ 2%/lệnh** ⇒
NULL của chúng là **"chưa đủ lực"** cho hiệu ứng ≲2% — ghi rõ, không đổi thành kết luận dương.
(`MDE theo N` và `MDE cửa sổ DEV` nằm trong `/tmp/funding_factor/report.txt` §4b.)

## 7. Bảng quyết định (đối chiếu cổng §6 PREREG đã khoá)

| test | HOLD | net | CI72h×1.21 | x1.21 | Bonf3 | ≥ MDE | dấu 4h/72h | ≥60% dấu | ⇒ |
|---|---|---|---|---|---|---|---|---|---|
| T1 spread D10−D1 | 24h | −0,2525% | [−0,3974%, −0,1076%] | CÓ | CÓ | CÓ (0,20%) | CÓ (−0,149%/−0,252%) | **KHÔNG** (54,9%) | **NO-GO** |
| T2 long-only D1 | 24h | −0,1913% | [−0,4683%, +0,0857%] | – | – | – | – | – | **NO-GO** |
| T3 diff (≤0−>0) | 24h | +0,9482% | [−0,0127%, +1,9090%] | – | – | KHÔNG (2,00%) | **KHÔNG** (−0,149%/+1,428%) | 55,5% block | **NO-GO** |

## 8. Cách áp dụng nếu có GO — **KHÔNG có GO ⇒ không đề xuất áp dụng**

Không đề xuất lọc/sizing/feature nào từ vòng này. **Nếu** sau này có quyết định theo đuổi tiếp, hai
hướng **có cơ sở dữ liệu** (đều cần **pre-reg riêng**, cờ default OFF, parity gate Python↔Java) là:
(i) **bổ sung `f_cum` như số hạng chi phí trong mô phỏng** — không phải alpha, chỉ để **đúng kế toán**
(D10 trả 0,074%/24h, 0,169%/72h; hệ thống long-only nên biết); (ii) **nhánh "dump sâu × funding âm"**
(T3 phân tầng D10 `d15` = +1,27%, N nhỏ, nhiễu) — phải pre-reg riêng, dùng **forward episode** để có
lực, không chạy lại dữ liệu cũ (đúng `INVENTORY_RECENT_MEASURES.md` §4: power chỉ đến từ **episode
độc lập**).

## 9. Dẫn chiếu tiền lệ

`docs/SURVEY_OLDCODE_SIGNALS.md` §3: **"Funding cross-section — độc lập symbol nhưng ĐÃ ĐO (WFO leakfree
v2 = FAIL/REVIEW, WFE med 0,098)"**; rule cũ `FUNDING_FEE_BUY` đã chuyển sang ML `funding_selector` và
**ĐÃ ĐO → FAIL**. Kết quả vòng này **NHẤT QUÁN với tiền lệ** (không có factor cross-section dùng được),
và **bổ sung được thứ mà tiền lệ chưa có**: (a) định lượng **chi phí funding** theo decile/HOLD
(0,0062%/4h → 0,4795%/24h spread D10−D1), (b) chứng minh **persistency** `f_entry→f_cum` = 0,60,
(c) chỉ ra **cơ chế nhiễu** của hướng "overlay": ở phút MOM15 fire, dấu của split **ngược ở 4h** và
**biến mất khi kiểm soát độ sâu dump** ⇒ cùng một kết luận (KHÔNG dùng funding như alpha) nhưng vì
**lý do khác** ("funding không mang thông tin timing ngoài cái d15 đã có").

## 10. Artifacts

- Pre-reg: `docs/PREREG_FUNDING_FACTOR.md` — commit **`17d600a`**.
- Script: `research/analysis/funding_coverage.py`, `funding_factor.py`, `funding_factor_stats.py`,
  `funding_factor_diag.py`, `funding_factor_extra.py`.
- Trung gian (ngoài repo): `/tmp/funding_factor/{pools.npz, d15.npz, cache2.npz, coverage.csv,
  report.txt, report_extra.txt, factor.log, stats.log}` — đã dọn `partial.npz`/`*.out` sau khi chốt số.
- **KHÔNG push** (commit trên nhánh `module`, để owner push).
