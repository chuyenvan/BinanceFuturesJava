# RESULT_FUNDING_SIGN — truy lại & chốt QUY ƯỚC DẤU funding (đo lại 2 tầng độc lập)

Ngày: 2026-09-23. Pre-reg: `docs/PREREG_LIMIT_ENTRY.md` (**commit `493c02f`, TRƯỚC khi đo**).
Script: `research/analysis/funding_sign_reconcile.py`. Trung gian: `/home/ubuntu/claudedata/funding_sign/`
(`report.txt`, `summary.json`, `fund_cache.npz`, `orders_funding.csv`) — ngoài repo, **dọn sau khi commit**.

**Tuân thủ:** thuần Python (0-sim) · **không** Java trên Oracle (shadow đang chạy) · **không** `claude-run`/Claude Code
· **không push** · **không chạm 2026** (mọi mốc `< 2026-01-01`; 579.924 cặp `(symbol,T)` có `T ≥ 2026` đã **loại**).
Nguồn: Aerospike `test.funding_data` (read-only, 831 symbol, 2.394.587 cặp) + 1089 lệnh canonical
`X1_GS_T170_2021/storage/printDone.csv` (md5 `efb793e2468ca3a7318da0f0ad23d4fc`, **khớp**).

---

## 0. KẾT LUẬN NGẮN (đọc cái này là đủ)

1. **Quy ước ĐÚNG (khoá, = Binance thật): `rate > 0` ⇒ LONG TRẢ, `rate < 0` ⇒ LONG NHẬN.**
   Aerospike lưu **nguyên** `fundingRate` của Binance (crawler `HistoricalFundingCrawlerLocal.java:75`,
   **không đổi dấu**) ⇒ **không có lỗi dấu ở nguồn dữ liệu**. Kiểm chứng chéo: BTCUSDT mean rate **dương**
   ở **85,6%** số kỳ (chuẩn crypto long-crowding) — nếu dấu bị đảo thì con số này phải ~15%.

2. **HAI PHÉP ĐO KHÔNG MÂU THUẪN — chúng đúng cả hai, vì là 2 thống kê KHÁC NHAU của cùng một phân bố:**
   - **"Đa số lệnh TRẢ"** = số liệu **MODE/modal** (đếm lệnh): **459/673 = 68,2%** lệnh TRẢ — **ĐÚNG**.
   - **"Được NHẬN về"** = số liệu **TỔNG (mean)**: **`mean f_pp = −0,2518 %/lệnh`** = **THU ròng 0,2518 %/lệnh** — **ĐÚNG**.
   Hai điều này cùng tồn tại được vì **đuôi THU rất nặng**: |f_pp| trung bình khi TRẢ chỉ **0,0888 %/lệnh**,
   còn khi THU là **0,9825 %/lệnh** — **gấp 11,1 lần**. Đa số trả *một chút*, thiểu số nhận *rất nhiều*.

3. **Nguồn gây "lẫn dấu" thật sự là HAI QUY ƯỚC, không phải hai sự thật:** tài liệu cũ báo theo **dấu PnL
   (`dương = ĐƯỢC thu`)**; `RESULT_COST_REAL_AUDIT` báo theo **dấu CHI PHÍ (`âm = THU`)**. **Cùng một con số
   sim**: `RESULT_COST_LIQUIDITY.md:197` = **`funding_pct = −funding/margin` → +0,1209%** ("âm = ĐƯỢC thu"),
   còn audit §2.3 = **`funding_sim_pp` → −0,1209%** ("âm = THU"). **|giá trị| trùng khít, dấu ngược** — 100%
   do quy ước. Thêm nữa, headline của audit chọn **số liệu modal** ("đa số lệnh TRẢ") đứng cạnh **mean âm**,
   nên đọc như mâu thuẫn, dù **chính audit §0(3) đã ghi rõ** "khoản thu ròng chỉ đến từ một thiểu số lệnh".

4. **SỐ ĐÚNG (chốt, dùng về sau)** — cửa sổ `(t_entry, t_exit]`, đơn vị **%/notional**:

   | Tập mẫu | n | %TRẢ | %THU | **mean `f_pp`** | median | Kết luận |
   |---|---|---|---|---|---|---|
   | Lệnh có ≥1 kỳ settle | **673** | **68,2%** | **31,8%** | **−0,2518** (THU ròng) | **+0,0109** (TRẢ nhỏ) | **THU ròng 0,2518 %/lệnh** |
   | Cả 1089 lệnh (0 kỳ ⇒ 0) | 1089 | 42,1% | 19,7% | −0,1556 (THU ròng) | — | THU ròng 0,1556 %/lệnh |
   | Sim (cột `funding`) | 1089 | 62,0% | 38,0% | −0,1209 (THU ròng) | +0,0000 | sim **bảo thủ** (thu ít hơn thật 0,0347pp) |

   **Độ bền của "THU ròng"** (B6–B8): clip `|rate| ≤ 0,75%/kỳ` (trần Binance chuẩn) ⇒ **−0,1724**; bỏ cửa sổ
   FTX (2022-11-08..13) ⇒ **−0,1271**; bỏ 10 lệnh THU lớn nhất ⇒ **−0,0911** — **vẫn THU ròng** ở cả 3 phép.
   **NHƯNG theo năm thì ĐỔI DẤU**: 2021 −0,054 | 2022 **−0,835** | 2023 −0,210 | **2024 +0,038 (TRẢ)** | 2025 −0,279.
   ⇒ "THU ròng" **không phải hằng số của hệ thống**, nó là **sự kiện của vài episode** (FTX chiếm **−0,1300**
   trên tổng −0,2518 = **51,6%** giá trị mean).

5. **Một tầng nữa (unconditional, không lọc lệnh):** trên **1,81 M kỳ settle** toàn universe, **81,3% kỳ có `rate>0`**
   (DEV: **80,6%**), mean rate **+0,1588 bp/kỳ** (ALL) và **−0,0621 bp/kỳ** (DEV) ⇒ **một long "generic" TRẢ nhưng
   rất nhỏ** (≈ 0 đến +0,05 %/ngày với 3 kỳ/ngày). Cửa sổ lệnh thật lệch hẳn sang **âm**: **−3,442 bp/kỳ**
   (mean per-settle) trên cùng 358 symbol/DEV có mean **−0,0028 bp/kỳ** ⇒ **chọn mẫu (mua-đáy) dịch funding
   về phía THU**, không phải dữ liệu sai.

6. **Hệ quả cho mô hình:** sửa funding **không tạo alpha** (audit §2.5: E−S = **+0,0347 pp/lệnh**, đổi *độ lớn*,
   **không đổi dấu**, win% 88,0 → 88,0). Việc cần làm chỉ là **kế toán đúng dấu** (sim đang **bảo thủ**, thu ít
   hơn thực ~0,03–0,06 pp/lệnh). **Không** có cơ sở "lật" kết quả nào từ nhánh funding.

---

## 1. Quy ước KHOÁ + nguồn

| Đại lượng | Công thức | Dấu |
|---|---|---|
| `f_pp` (%/notional) | `100 × Σ_{T ∈ (t_in,t_out]} rate(T)` | `>0` = **TRẢ**, `<0` = **THU** (quy ước **CHI PHÍ**) |
| `pnl_fund_pp` | `−f_pp` | `>0` = **được NHẬN** (quy ước **PnL**) |

Nguồn rate: Aerospike `test.funding_data`, key = symbol, bin `f_data` = Snappy(JSON `{fundingTime_ms: fundingRate}`),
cadence 8h (BTCUSDT: 6.042 kỳ, 2021-01-01 → 2026-07-07, **median 8,000000h**, min/max lệch < 0,001 s).

### 1.1 Kiểm tra toàn vẹn dữ liệu (để không kết luận trên rác)
- `rate` ∈ [**−0,04; +0,04**]; chỉ **2.701/1.814.663 = 0,149%** kỳ có `|rate| > 0,0075` (trần Binance chuẩn),
  **128** kỳ `|rate| > 2%`, **4** kỳ `> 3%`. Top symbol có đuôi cực trị: `TRBUSDT(18)`, `LOOMUSDT(9)`,
  `FTTUSDT(9)`, `LPTUSDT(7)`, `BLZUSDT(7)` — **toàn symbol có sự kiện thật** (pump/squeeze/sụp).
- **Kiểm chứng thô bằng giá trị gốc:** FTTUSDT 2022-11-08..09 = `{−0,0970%, −0,7500%, −0,2444%, −0,6365%, −1,0749%}`
  — khớp sự kiện FTX (perp chiết khấu cực mạnh, long được trả dày). ⇒ **đuôi THU là thật**, không phải lỗi parse.
- 0 cặp `(symbol,T)` trùng; mọi symbol đã sắp theo `ts`; 0 lỗi đọc khi scan.

---

## 2. TẦNG A — phân bố FUNDING RATE (unconditional)

### 2.1 Toàn universe, theo năm (%/kỳ; `bp` = 0,01%)

| Tập | N kỳ | **%rate>0** | %rate<0 | mean (bp) | median (bp) | p01 | p99 |
|---|---|---|---|---|---|---|---|
| ALL 2021..2025 | 1.814.663 | **81,3** | 18,6 | **+0,1588** | +0,5000 | −14,307 | +9,662 |
| **DEV 2022..2025** | **1.690.866** | **80,6** | 19,2 | **−0,0621** | +0,5000 | −14,630 | +6,266 |
| DEV & 627 symbol `raw/*.f32` | 1.671.421 | 80,6 | 19,2 | −0,0638 | +0,5000 | −14,691 | +6,278 |
| 2021 | 123.793 | 90,0 | 9,7 | **+3,1762** | +1,0000 | −10,651 | +31,030 |
| 2022 | 156.926 | 67,5 | 32,1 | **−0,4895** | +1,0000 | −14,854 | +1,000 |
| 2023 | 223.592 | 87,0 | 12,7 | +0,3608 | +1,0000 | −11,151 | +5,383 |
| 2024 | 431.598 | 90,4 | 9,5 | **+0,8107** | +0,7609 | −5,703 | +7,869 |
| 2025 | 878.750 | 76,6 | 23,3 | **−0,5221** | +0,5000 | −19,860 | +5,275 |

**Đọc:** funding **dương ở ~4/5 số kỳ** ở **mọi** năm ⇒ **long thường TRẢ**, nhưng biên độ rất nhỏ
(median +0,5 bp = **+0,005%/kỳ**). Năm **2022 và 2025** là 2 năm **mean âm** (long được trả ròng).

### 2.2 Cross-sectional (mean rate qua symbol tại từng mốc `T`, `≥20 symbol/mốc`)

| | n mốc | mean (bp) | % mốc có mean>0 |
|---|---|---|---|
| ALL | 12.983 | **+0,2897** | **55,7%** |
| 2021 | 1.095 | +3,5572 | 81,6% |
| 2022 | 1.095 | −0,4347 | 40,4% |
| 2023 | 1.322 | +0,3368 | 69,8% |
| 2024 | 2.196 | +0,7732 | 80,6% |
| 2025 | 2.875 | **−1,0700** | **26,1%** |

⇒ Ở tầng cross-section, **2025 gần như đảo hẳn về phía long-được-trả** (74% số mốc có mean âm).

---

## 3. TẦNG B — PnL funding của LONG trên cửa sổ giữ lệnh THẬT (1089 lệnh)

### 3.1 Tái lập số của audit (gate) + phân rã
`673/1089` lệnh có ≥1 kỳ settle (`n_settle`: mean **8,89**/lệnh trong 673; **5,49** nếu tính trên cả 1089; max **169**).

| | n | % | **|f_pp| trung bình** |
|---|---|---|---|
| **TRẢ** (`f_pp>0`) | 459 | **68,2%** | **0,0888 %**/lệnh |
| **THU** (`f_pp<0`) | 214 | **31,8%** | **0,9825 %**/lệnh |

`mean f_pp = −0,2518 %/lệnh` (**THU ròng**), `median = +0,0109 %` (**TRẢ nhỏ**).
Phân rã số học: `P(trả)·E[|f|,trả] = +0,0606` và `−P(thu)·E[|f|,thu] = −0,3124` → tổng **−0,2518** ✔
⇒ **toàn bộ độ lớn của "THU ròng" đến từ 31,8% lệnh THU**, không phải từ việc "đa số trả ít".
Per-settle: mean **−3,442 bp/kỳ**, median **+0,500 bp/kỳ**.

**Đối chiếu sim (cùng quy ước, cùng đơn vị):** sim TRẢ 62,0% / THU 38,0%, mean **−0,1209 %/lệnh**, median 0,0000%;
lệch `real − sim`: mean **−0,0562 pp**, median −0,0003 pp, **corr 0,805** ⇒ sim **cùng dấu, hơi bảo thủ**.

### 3.2 Tập trung đuôi (vì sao mean bị chi phối)
| | giá trị |
|---|---|
| Top-5 THU lớn nhất | SOLUSDT 2022-11-09 (**−16,25%**, 9 kỳ) · RAREUSDT 2025-03-10 (**−12,57%**, 42 kỳ) · FTTUSDT 2022-11-08 (**−12,35%**, 11 kỳ) · FTTUSDT 2022-11-08 (−12,35%) · SOLUSDT 2022-11-09 (−12,00%) |
| 10 lệnh THU lớn nhất | đóng góp **−0,1621 %/lệnh** vào mean; chiếm **43,5%** tổng `Σ|f_pp|` |
| Bỏ 10 lệnh THU lớn nhất | mean còn **−0,0911 %/lệnh** (n=663) → **vẫn THU ròng** |
| Cửa sổ FTX (2022-11-08..13) | n=28 lệnh, `Σf_pp = −87,5%` ⇒ đóng góp **−0,1300 %/lệnh** (= **51,6%** của mean!). Bỏ ra: **−0,1271%** (n=645) |

Theo số kỳ settle: `[1,2)` mean −0,0410 | `[2,4)` −0,0469 | `[4,8)` −0,1475 | `[8,16)` **−0,7693** | `[16,32)` −0,2607 | `[32,∞)` −1,2950
(%TRẢ 58–75% ở mọi band) ⇒ **lệnh giữ lâu (8–16 kỳ) là nơi dồn khoản THU**.

### 3.3 Theo năm vào lệnh (cửa sổ gốc)
| năm | n | %TRẢ | mean `f_pp` | Kết luận |
|---|---|---|---|---|
| 2021 | 78 | 71,8 | −0,0539 | THU |
| 2022 | 124 | 42,7 | **−0,8347** | THU mạnh |
| 2023 | 88 | 60,2 | −0,2097 | THU |
| **2024** | 200 | **80,0** | **+0,0382** | **TRẢ** |
| 2025 | 183 | 74,9 | −0,2786 | THU |

### 3.4 Đối chứng unconditional trên CHÍNH 358 symbol / DEV
`N = 1.135.325` kỳ, %rate>0 = **80,8%**, mean rate **−0,0028 bp/kỳ** — so với **−3,442 bp/kỳ** trong cửa sổ lệnh
⇒ **dịch −3,44 bp/kỳ là do CHỌN MẪU (mua-đáy), không do dữ liệu**. (Vẫn cùng dấu: cửa sổ lệnh âm hơn mặt bằng.)

---

## 4. TRUY VẾT VĂN BẢN CŨ — "chỗ nào kết luận funding dương/nhận được"

| # | File (dòng) | Số | **Quy ước dấu của nó** | Kết luận |
|---|---|---|---|---|
| 1 | `docs/RESULT_COST_LIQUIDITY.md:197` | `funding_pct = −funding/margin` mean **+0,1209%** | **PnL (`dương` = ĐƯỢC thu)** | **Được THU** 0,1209%/lệnh (sim) |
| 2 | `archive/.../reports/funding_fee_audit.md` (TASK-131, 2026-07-05) §D | `Σfunding ON = −918` ⇒ PnL **+1,8%** | **Chi phí (`âm` = nhận)**; `feeTotal=Σ rate×notional` | **Được NHẬN ròng** (+1,8% PnL) |
| 3 | `archive/.../FINDINGS.md:222-223` | `Σfunding ON = −918` | như trên | như trên ("KHÔNG lỗi dấu") |
| 4 | `archive/.../reports/EXIT_SWEEP_20260731_rate_ratchet.md:429` | `funding = −30 → −112` (~0,3% PnL) | **Chi phí (`âm` = `ta NHẬN`)** | **Nhận** (gió xuôi, không phải chi phí) |
| 5 | `docs/RESULT_FUNDING_TOPK_ROTATE.md:13-14,176` | `f_cum = −0,256%/chu kỳ` (K=5) | **Chi phí (`âm` = THU)** | **Thu** +0,77%/ngày |
| 6 | `docs/RESULT_FUNDING_TOPK_K13.md:298-299` | `f_cum = −0,5755% (K=1)` | như trên | Thu (+1,73%/ngày ở K=1) |
| 7 | `docs/RESULT_FUNDING_FACTOR.md:87,108-110,194` | D1 −0,0294%/24h; **D10 +0,0742%/24h** | **Chi phí (`+` = TRẢ)** | D1 (funding thấp nhất) **thu**; D10 **trả** |
| 8 | `docs/RESULT_COST_REAL_AUDIT.md` §0(3), §2.3 | THU 31,8% / TRẢ 68,2%; **mean −0,2518%/lệnh** | **Chi phí (`âm` = THU)** | **THU ròng** (luận điểm của vòng 2026-09-23) |
| 9 | `docs/DESIGN_HEDGED_BOOK.md:46-57` | — | phát biểu quy ước | "Funding BTC perp **dương phần lớn thời gian** ⇒ **short BTC NHẬN**"; cảnh báo **dấu cho `SELL` trong code là SAI** (mô hình bảo thủ) |
| 10 | `docs/PREREG_LEVEL_SENSITIVITY.md:51`, `docs/PREREG_REVERSAL_BOUNCE.md:81`, `docs/PREREG_BIGUP_MEDIUPDOWN.md:189` | — | phát biểu quy ước | "long **trả** funding dương" |
| 11 | `docs/DATA_EXTENT_SURVEY.md:192-213` | BTCUSDT funding p50 **+1,00 bp**; p99 +6,5..+15,9 bp (2020-21) | rate thô | funding **dương phần lớn thời gian**; "funding dương kéo dài cực mạnh không tồn tại trong DEV" |
| 12 | `docs/DIAG_ALT_IDIOSYNCRATIC_RISK.md:17` | cột `funding` = funding FEE **USDT** (đã nhân) | Chi phí (`+` = trả) | kế toán USDT, không nêu dấu tổng |

**Đọc bảng này:** **KHÔNG có tài liệu nào kết luận "long TRẢ ròng"** cho sổ long. Mọi phép đo (1–8) — kể cả
phép đo cũ mà owner nhớ (#2/#4: "được NHẬN/thưởng") — đều **CÙNG một sự thật: hệ THU ròng funding**, chỉ khác
**dấu trình bày**. Vậy "chỗ cũ sai" **không nằm ở số hay ở dấu của phép đo**, mà ở **cách phát biểu**:
(a) **trộn 2 quy ước** (PnL `+` vs Chi phí `−`) giữa các tài liệu ⇒ cùng con số 0,1209% bị đọc thành 2 chiều;
(b) audit chọn **số liệu modal** làm headline ⇒ nghe như "chi phí" dù kết luận là "thu".

---

## 5. TRẢ LỜI TRỰC TIẾP

| Câu hỏi | Trả lời (bằng số) |
|---|---|
| Quy ước nào ĐÚNG? | `rate>0` ⇒ **long TRẢ**. Đúng ở nguồn (Binance `fundingRate` nguyên bản), đúng ở code sim (`computeFundingOnClose`: `feeTotal += rate*notional`, `tp -= calFundingFee()`), và đúng ở phép đo lại độc lập. |
| Vì sao 2 vòng "lệch"? | Không lệch về **dấu của sự thật**. "68,2% TRẢ" là **modal**; "−0,2518%/lệnh" là **mean** (đuôi THU nặng gấp **11,1×**). Thêm: tài liệu cũ dùng **dấu PnL**, audit dùng **dấu chi phí**. |
| **Số ĐÚNG** | **%lệnh**: TRẢ **68,2%** / THU **31,8%** (trên 673 lệnh có settle); **mean = THU ròng 0,2518 %/notional/lệnh**; **median = TRẢ 0,0109%**; trên cả 1089 lệnh: mean THU ròng **0,1556%**, (TRẢ 42,1% / THU 19,7% / 0 kỳ 38,2%). **Unconditional**: **80,6%** kỳ có `rate>0` (DEV), mean rate **−0,0621 bp/kỳ** (≈0). |
| Có phải "đa số được thu" không? | **KHÔNG.** Đa số lệnh (68,2%) **TRẢ**; **khoản THU ròng đến từ 31,8% lệnh** (chủ yếu các episode sụp: FTX/LUNA/squeeze). |
| Có phải "funding là chi phí lớn" không? | **KHÔNG.** Median ≈ 0 (0,01%/lệnh), và tổng hợp là **thu**. Độ lớn tuyệt đối nhỏ so với fee+slip (audit §2.5). |
| Cần sửa gì? | Chỉ **kế toán dấu** (sim thu ít hơn thực 0,03–0,06 pp/lệnh ⇒ **bảo thủ**). **Không** alpha, **không** đề xuất overlay. |

**Giới hạn (nói rõ):** (i) kết luận "THU ròng" **phụ thuộc episode** (FTX = 51,6% giá trị mean; 2024 **TRẢ**);
(ii) đuôi cực trị có thật nhưng hiếm (**0,149%** kỳ vượt trần 0,75%) ⇒ **clip về trần chuẩn vẫn THU nhưng nhỏ hơn**
(0,1724 vs 0,2518); (iii) 1089 lệnh là **một run** (`X1_GS_T170_2021`) ⇒ không suy ra universe;
(iv) không có dữ liệu fill thật nên mọi kết luận funding chỉ là **kế toán**, không phải PnL khớp lệnh.

---

## 6. SẢN PHẨM

| File | Nội dung |
|---|---|
| `docs/PREREG_LIMIT_ENTRY.md` | chốt trước (commit `493c02f`) |
| `docs/RESULT_FUNDING_SIGN.md` | file này — truy vết + đo 2 tầng + chốt quy ước + số đúng |
| `research/analysis/funding_sign_reconcile.py` | script tái tạo (thuần Python, chỉ đọc) |
| `/home/ubuntu/claudedata/funding_sign/` | `report.txt`, `summary.json`, `fund_cache.npz`, `orders_funding.csv` (ngoài repo, dọn sau commit) |
