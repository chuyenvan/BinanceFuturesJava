# RESULT_HARNESS_CONTROL — hiệu chuẩn bộ đo: positive control (MOM15) · negative control (placebo) · MDE

Ngày: 2026-09-22. Pre-reg: `docs/PREREG_HARNESS_CONTROL.md` (commit `9611823`, chốt TRƯỚC khi chạy;
sau đó **không sửa thiết kế**). Script: `research/analysis/harness_control.py` (sinh tín hiệu) +
`research/analysis/harness_control_stats.py` (thống kê).
0-sim, **thuần Python** (không `claude-run`, không Java trên Oracle, không push, **không chạm 2026**).
Harness **tái sử dụng nguyên** 2 vòng trước: HOLD 1440′, fee 0.10% + slip 0.5×range + funding,
CI block-72h ×1.21 (2000 rep, seed 20260905), null block sign-flip, nguồn causal `raw/*.f32`
(= Aerospike `kline_1m_opt` đã extract) + funding Aerospike chỉ-đọc, DEV = 2022-01-01..2024-06-30.

## 0. KẾT LUẬN (một dòng + 3 phần)

> **Bộ đo ĐÁNG TIN: không có lỗi hệ thống và không có lỗi kiểm định** (A dương mạnh ở toàn dải
> 2021–2025, p(>0)=1.000, null p=0.0000, 5/5 năm dương; B false-positive = **0/200**).
> Nhưng **DEV THIẾU POWER**, không phải "cần": ở tín hiệu cụm kiểu capitulation với N≈3 200 (chính
> MOM15), **MDE = 2,00%/lệnh**; ở N≈100–1 000, **MDE = 4,00%/lệnh**. Mọi ứng viên đã NULL có hiệu
> ứng DEV đo được ≤ 1,84%/lệnh ⇒ **đều NẰM DƯỚI MDE** ⇒ các kết luận NULL trước đây là **"chưa đủ
> lực để phát hiện"**, KHÔNG phải "đã chứng minh không có edge". Ngoại lệ duy nhất: reversal-bounce
> (N=1 179 302, CI riêng half 0,43%) — NULL của nó **chặn được** mọi edge ≥ ~0,5%/lệnh.

| Phần | Kết quả | Đạt? |
|---|---|---|
| **A. Positive control (MOM15)** | toàn dải: net **+2,26%**/lệnh, CI72h×1.21 **[+0,93%, +3,59%]**, p(>0)=**1.000**, null p(**≥obs**)=0.0000, 5/5 năm dương | **ĐẠT ở toàn dải** |
| A. trên **riêng DEV** | net **+1,28%**, CI72h×1.21 **[−0,72%, +3,28%]** (chứa 0), p(>0)=0,939 | **KHÔNG ĐẠT** (cổng DEV chặt của pre-reg) |
| **B. Negative control (placebo)** | FP 1 phía (báo nhầm edge **dương**) = **0/200 = 0,0%**; 2 phía 43/200 = 21,5% (toàn bộ là chiều **âm do drag chi phí có thật**, không phải FP) | **SẠCH** |
| **C. MDE (DEV)** | **0,50%/lệnh** (basis pre-reg, N=3 167, cụm làm phẳng) · **2,00%/lệnh** (basis đúng cụm, N=3 167) · **4,00%/lệnh** (N=100–1 000) | — |

**Trả lời câu hỏi owner (1 câu):** bộ đo **đáng tin**; DEV **"thiếu power"** chứ không "cần" — các
NULL trước đây chỉ là **chưa đủ lực** để bác bỏ hiệu ứng cỡ ≤ ~2%/lệnh (trừ reversal-bounce có N
khổng lồ, đã chặn được hiệu ứng ≥ ~0,5%/lệnh).

Chi tiết A không đạt cổng DEV **không** phải lỗi harness (pre-reg §3 đã ghi trước 2 nhánh): tiêu
chuẩn để phân biệt "harness có vấn đề" vs "DEV thật sự thiếu hiệu ứng" đã báo đủ (i) số toàn dải +
theo năm, (ii) A-secondary, (iii) B-secondary — cả ba đều rơi vào nhánh **"DEV thiếu power"**
(xem §3.3 và §5). Bằng chứng trực tiếp: **chính MOM15 — tín hiệu đang chạy live — cũng KHÔNG được
chứng nhận trên riêng DEV** (CI chứa 0) dù nó dương ở 5/5 năm.

---

## 1. Kiểm chứng tái tạo (trước khi tin bất kỳ số nào)

| Kiểm chứng | Vòng này | Số tham chiếu đã công bố | Khớp |
|---|---|---|---|
| `total_rows` cross-section d15 | **619 073 711** | `PREREG_REVERSAL_BOUNCE.md` §3 "619M dòng" | ✔ |
| `rateDown15MAvg < −0,028` | **13 164 phút = 0,5006%** số phút | `RESULT_BIGUP_MEDIUPDOWN.md` §2 "0,50% số phút" | ✔ |
| Fire MOM15 | **13 164 phút** → 11 381 event (k=1) / 19 992 (k=2) | — | — |

`rateDown15MAvg` tái tạo **đúng chuỗi causal** mà repo dùng (cùng hàm `calRateChangeAvg` k=min(100,
⌊n·4/5⌋), n≥50; cùng nguồn `kline_1m_opt` đã extract), nên phép đo đứng trên đúng chuỗi hệ thống
dùng. Causal: chỉ dùng nến **đã đóng**, scan thời gian tăng dần, không nhìn tương lai.

## 2. A — POSITIVE CONTROL: MOM15 (`rateDown15MAvg < −0,028`)

Định nghĩa đã grep trong repo trước khi đăng ký (`PREREG_HARNESS_CONTROL.md` §3):
dạng (1) gate HEAD trên `predReturn15M` là **output model** ⇒ không tính được thuần Python;
dạng (2) **market-level `SMALL_DOWN_15M` = `rateDown15MAvg < −0,028`** ("= MOM15 live",
`SURVEY_OLDCODE_SIGNALS.md` §2) ⇒ **A dùng dạng (2)**.

### 2.1 A-PRIMARY (`k=1`, đúng `SMALL_DOWN_15M` live)

| Mẫu | N | meanNet | meanRaw | win | CI72h | p(>0) | **CI72h ×1.21** |
|---|---|---|---|---|---|---|---|
| **ALL 2021–2025** | 11 381 | **+2,2598%** | +3,3639% | 55,6% | [+1,1344%, +3,3250%] | **1,000** | **[+0,9345%, +3,5851%]** |
| **DEV 2022-01..2024-06** | 3 167 | +1,2793% | +2,3479% | 57,2% | [−0,3400%, +2,9643%] | 0,939 | **[−0,7197%, +3,2784%]** |
| NON-DEV | 8 214 | +2,6378% | +3,7557% | 55,1% | [+1,1046%, +3,9698%] | 1,000 | [+0,9043%, +4,3712%] |

Theo năm (net, CI72h×1.21):

| Năm | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| N | 4 239 | 1 692 | 777 | 1 650 | 3 023 |
| net | **+3,26%** | +0,07% | **+1,88%** | **+3,13%** | +1,71% |
| CI72h×1.21 | [+0,77%, +5,75%] | [−3,38%, +3,52%] | [+0,34%, +3,42%] | [+1,23%, +5,02%] | [−1,48%, +4,90%] |

Khác: `%coin+` 67,5% (≥1 lệnh, 607 sym) / 71,3% (≥5) / 79,5% (≥10); `short_delist` N=8 (+0,62%);
null block sign-flip: ALL `obs=+2,2598%, p(≥obs)=0,0000` / DEV `obs=+1,2793%, p=0,0770`;
ICC: ALL ICC(day)=0,164 ICC(72h)=0,070 | **DEV ICC(day)=0,497** ICC(72h)=0,137.

### 2.2 A-SECONDARY (`k=2`, so táo-với-táo với vòng trước)

| Mẫu | N | meanNet | CI72h ×1.21 | p(>0) |
|---|---|---|---|---|
| ALL | 19 992 | +1,8483% | [+0,8201%, +2,8766%] | 1,000 |
| DEV | 5 837 | +1,0797% | [−0,5044%, +2,6638%] | 0,948 |
| NON-DEV | 14 155 | +2,1653% | [+0,8390%, +3,4916%] | 1,000 |

Theo năm: 2021 +2,48% / 2022 **−0,33%** / 2023 +1,67% / 2024 +3,04% / 2025 +1,61%.

### 2.3 Cổng A (pre-reg §3): kết quả

**A-PRIMARY: `DEV mean > 0` ✔ NHƯNG `CI72h×1.21 lo > 0` ✘ ⇒ KHÔNG ĐẠT cổng DEV.**
A-SECONDARY: cùng kết luận (DEV +1,08%, CI [−0,50%, +2,66%]).
**Toàn dải 2021–2025: A dương rất mạnh và CI loại 0** (k=1: +2,26%, p=1.000, null p=0.0000; k=2:
+1,85%, p=1.000) — tức bộ đo **có** phát hiện được tín hiệu đã biết là thật khi có đủ dữ liệu độc
lập. Điểm chết nằm ở **DEV**: N nhỏ hơn (3 167) + **cụm cực mạnh** (ICC(day)=0,50) ⇒ half-width
×1.21 = **±1,65%**, rộng hơn chính hiệu ứng.

## 3. B — NEGATIVE CONTROL (placebo, 200 rep)

**B-PRIMARY (day-permute):** giữ nguyên symbol + giữ **chính xác phút-trong-ngày**, **ngày ngẫu
nhiên đều trên DEV**, cùng HOLD/chi phí; mỗi rep đúng N = N_A_PRIMARY_DEV. Seed rep r = 20260905+r.

| Chỉ số | ALL event | **DEV event (headline)** |
|---|---|---|
| mean(net) qua 200 rep | −0,2258% (sd 0,0707%) | **−0,1863%** (sd 0,1150%; min −0,464%, max +0,204%) |
| half-width CI72h×1.21 (median / p80 / p95) | 0,1590% / 0,1686% / 0,1802% | **0,2752% / 0,3002% / 0,3311%** |
| **FP 1 phía (CI lo > 0 ⇒ báo nhầm edge dương)** | **0/200 = 0,0%** | **0/200 = 0,0%** |
| CI loại 0 (2 phía) | 163/200 = 81,5% | 43/200 = 21,5% |
| trong đó chiều **âm** (CI hi < 0) | 163/200 = 81,5% | 43/200 = 21,5% |

**Đọc đúng:** placebo có **mean thật ≈ −0,19%** (đúng bằng drag chi phí 0,10% + slip + funding —
không phải 0). Vì vậy "CI loại 0" 21,5% ở DEV **không phải false-positive**: đó là việc test **phát
hiện đúng** một hiệu ứng âm có thật. **Tỉ lệ báo nhầm edge DƯƠNG = 0/200 = 0,0%** (cận trên 95%
theo luật 3: ≤ 1,5%) ⇒ **≤ 5% như kỳ vọng** ⇒ **không có vấn đề về kiểm định**.

**B-SECONDARY (same-minute random symbol, 2 708 437 dòng pool):** thay symbol bằng symbol ngẫu
nhiên đều **tại đúng phút** MOM15 fire (giữ thời điểm, bỏ chọn symbol):

| Chỉ số | ALL | DEV |
|---|---|---|
| mean(net) qua 200 rep | **+2,0044%** (sd 0,079%) | **+1,0405%** (sd 0,114%) |
| half-width CI72h×1.21 (median) | 1,0612% | **1,8272%** |
| FP 1 phía | 200/200 = 100% (edge **có thật**, không phải FP) | 0/200 = 0,0% (không đủ lực) |

**Ý nghĩa (rất quan trọng):** tại các phút MOM15 fire, **một symbol ngẫu nhiên** đã ăn +2,00%
(toàn dải) / +1,04% (DEV) sau phí. ⇒ **edge của MOM15 chủ yếu là hiệu ứng THỜI ĐIỂM (market
timing / bounce sau capitulation diện rộng)**, không phải do "chọn coin rớt sâu nhất": A-PRIMARY
trừ B-SECONDARY chỉ còn **+0,26 điểm %** (ALL) / **+0,24 điểm %** (DEV) cho phần chọn symbol. Đây
là **hiệu ứng có thật trong dữ liệu**, harness tái tạo được — thêm một bằng chứng bộ đo không hỏng.

## 4. C — POWER / MDE (đơn vị **%/lệnh**)

Cách đo: trên chuỗi placebo, dựng chuỗi có **mean đúng bằng X** (`(net − mean) + X`); **phát hiện**
= `CI72h×1.21 lo > 0` (đúng cổng GO). Với phép dịch hằng số, half-width không đổi và obs = X, nên
`phát hiện ⟺ X > half-width(centered)` — đẳng thức **đã kiểm chứng** trên 3 rep (sai khớp 0).

**C-1 (basis pre-reg = B-PRIMARY day-permute), N = N_A_PRIMARY_DEV = 3 167:**

| X (%/lệnh) | 0,25% | 0,50% | 1,00% | 2,00% | 4,00% |
|---|---|---|---|---|---|
| power | 16,0% | **100%** | 100% | 100% | 100% |

⇒ **MDE (day-permute, N=3 167) = 0,50%/lệnh.** Đường MDE theo N (cùng basis):

| N | 100 | 200 | 500 | 1 000 | 2 000 |
|---|---|---|---|---|---|
| MDE(80%) | 2,00% | 2,00% | 1,00% | 1,00% | 0,50% |
| half-width median | 1,4991% | 1,0396% | 0,6642% | 0,4793% | 0,3526% |

**C-2 (C-SENSITIVITY — bắt buộc đọc kèm, nhãn POST-HOC ngoài pre-reg):** B-PRIMARY **làm phẳng cụm
thời gian** (ngày ngẫu nhiên) nên half-width **nhỏ giả tạo**. Nền đúng cho tín hiệu kiểu
capitulation là **B-SECONDARY (giữ đúng thời điểm)**:

| N (DEV) | 100 | 200 | 500 | 1 000 | 2 000 | **3 167** |
|---|---|---|---|---|---|---|
| MDE(80%) | 4,00% | 4,00% | 4,00% | 4,00% | 2,00% | **2,00%** |
| half-width median | 2,7691% | 2,3735% | 2,0187% | 1,9367% | 1,8492% | **1,8272%** |
| power @ X=1% | 0% | 0% | 0% | 0% | 0% | 0% |
| power @ X=2% | 10% | 22% | 48% | 60% | 81% | 96% |

⇒ **MDE của DEV cho tín hiệu cụm capitulation: ≈ 2%/lệnh ở N≈3,2k, ≈ 4%/lệnh ở N≈100–1 000.**
(Đây là con số phải dùng để phán "đủ lực hay không" cho các ứng viên đã NULL, vì tất cả chúng đều
fire theo cụm capitulation.)

### 4.1 So sánh với các ứng viên đã NULL

| Ứng viên | N (DEV) | net DEV đo được | MDE(day-permute)@N | **MDE(cụm)@N** | Kết luận |
|---|---|---|---|---|---|
| **reversal-bounce long** | 1 179 302 | **−0,080%** | 0,43% (CI riêng của nó: half 0,36% ×1,21) | n/a (không cụm) | **DƯỚI MDE** (0,08% < ~0,5%) |
| BIG_UP (code cũ) | ~89 | +0,87% | 2,00% | **4,00%** | **DƯỚI MDE** |
| MEDIUM_UP (code cũ) | ~316 | +1,84% | 2,00% | **4,00%** | **DƯỚI MDE** |
| MEDIUM_DOWN (code cũ) | ~158 | +1,25% | 2,00% | **4,00%** | **DƯỚI MDE** |
| *(tham chiếu)* **MOM15 (A)** | 3 167 | +1,28% | 0,50% | **2,00%** | **DƯỚI MDE** ⇒ chính nó cũng chưa chứng nhận được trên DEV |

N_DEV của BIG_UP/MEDIUM_UP/MEDIUM_DOWN = tổng N theo năm 2022+2023+2024 trong
`RESULT_BIGUP_MEDIUPDOWN.md` §3.2 (**cận trên**, 2024 chỉ tính 6 tháng); net DEV lấy từ chính doc
đó. reversal-bounce: N và net DEV lấy từ `RESULT_REVERSAL_BOUNCE.md`.

⇒ **Trả lời trực tiếp:** các hiệu ứng đo được của ứng viên đã NULL **đều NẰM DƯỚI MDE** ⇒ DEV
**thiếu power**, không phải "cần". Riêng reversal-bounce có N khổng lồ (1,18M) nên **NULL của nó
có nghĩa**: nó **bác bỏ được** mọi edge ≥ ~0,5%/lệnh cho tín hiệu đó (hiệu ứng thật lớn hơn ngưỡng
này đã bị nhìn thấy).

## 5. Vì sao DEV yếu (cơ chế, không phải suy đoán)

MOM15/reversal-bounce/BIG_UP… đều là tín hiệu **cấp thị trường**, fire theo **cụm** trong vài đợt
capitulation: MOM15 DEV có **ICC(day)=0,50** (ALL 0,16) và 3 167 event rơi vào rất ít đợt ⇒ số khối
72h "độc lập" hiệu dụng nhỏ ⇒ CI block-bootstrap rộng (half ±1,65% ở DEV so với ±1,10% ở ALL với N
gấp 3,6 lần). Bộ đo **không sai**; nó chỉ **không thể tạo thêm thông tin độc lập từ một mẫu bị
cụm**. Đây là lý do kỹ thuật khiến chuỗi NULL trên DEV không kết luận được gì về các hiệu ứng nhỏ.

## 6. Hạn chế (trung thực)

1. **MOM15 trong phép đo này là dạng market-level** `rateDown15MAvg < −0,028` (dạng (2) đã được
   repo thiết lập, "= MOM15 live"), **không phải** gate HEAD trên `predReturn15M` (output model,
   không tính được thuần Python). Vậy A xác nhận harness trên **alias market-level** của tín hiệu
   momentum 15m đang dùng, không phải trên đúng lệnh live của gate model.
2. Harness là **0-sim, HOLD cứng 24h**, không TP/SL/DCA/gate/sizing — cố ý giống 2 vòng trước để so
   táo-với-táo; **không** phải P&L của leg live.
3. Cổng A của pre-reg yêu cầu **DEV**; A **không đạt** cổng đó (CI chứa 0) dù dương ở mọi năm và
   đạt rất mạnh ở toàn dải. Báo cáo này **giữ nguyên** phán quyết cổng (KHÔNG nới cổng sau khi thấy
   số) và dùng đúng các tiêu chí phân biệt đã ghi trước để kết luận nhánh "DEV thiếu power".
4. **C-2 (MDE theo cụm) là POST-HOC**, ngoài thiết kế pre-reg (pre-reg lấy B-PRIMARY làm nền MDE).
   Nó được báo cáo vì nền pre-reg **làm phẳng cụm** nên đưa ra MDE lạc quan sai (0,50% thay vì
   ~2,00%) cho tín hiệu kiểu capitulation. Con số 0,50% vẫn báo nguyên như pre-reg.
5. N_DEV của BIG_UP/MEDIUM_UP/MEDIUM_DOWN là **xấp xỉ** (cận trên) từ bảng theo năm của doc cũ,
   không đo lại (đo lại sẽ cần chạy lại 2 vòng cũ).
6. Không mô hình thanh lý; `min net` có thể −100% (coin về 0/delist trong 24h); universe = 627
   symbol có file 1M (gồm coin delist, không lọc survivorship).

## 7. Artifact + tuân thủ

- Pre-reg `docs/PREREG_HARNESS_CONTROL.md` (commit **9611823**) có **TRƯỚC** mọi phép đo.
- Script trong repo: `research/analysis/harness_control.py`, `research/analysis/harness_control_stats.py`.
- Không `claude-run`/Claude Code; **không Java**; thuần Python (đọc `raw/*.f32` + Aerospike
  `funding_data` chỉ-đọc); **không push**; **không chạm 2026** (dữ liệu ≤ 2025-12-31).
- File tạm `/tmp/harness_ctl/` đã dọn sau khi chốt số; toàn bộ số nằm ở **Phụ lục A** dưới đây.

---

## Phụ lục A — report thô (nguyên văn, `report_A.txt`)

```text
=== HARNESS CONTROL: A positive (MOM15) / B placebo / C MDE ===
pre-reg docs/PREREG_HARNESS_CONTROL.md (commit 9611823); harness nguyen ban: HOLD 1440,
fee 0.10% + slip 0.5x range + funding; CI block-72h 2000 rep seed 20260905 x1.21; DEV=2022-01-01..2024-06-30

################ A. POSITIVE CONTROL — MOM15 (rateDown15MAvg < -0.028) ################

---- A-PRIMARY (k=1, = SMALL_DOWN_15M live) ----
ALL 2021-2025: N=11381 meanNet=2.2598% meanRaw=3.3639% win=55.6% t(iid)=12.82 CI72h=[1.1344%,3.3250%] p(>0)=1.000 half=1.0953% | CI72h_x1.21=[0.9345%,3.5851%]
DEV 2022-01..2024-06: N=3167 meanNet=1.2793% meanRaw=2.3479% win=57.2% t(iid)=5.17 CI72h=[-0.3400%,2.9643%] p(>0)=0.939 half=1.6521% | CI72h_x1.21=[-0.7197%,3.2784%]
NON-DEV: N=8214 meanNet=2.6378% meanRaw=3.7557% win=55.1% t(iid)=11.74 CI72h=[1.1046%,3.9698%] p(>0)=1.000 half=1.4326% | CI72h_x1.21=[0.9043%,4.3712%]
-- by year --
  Y2021: N=4239 meanNet=3.2597% meanRaw=4.2449% win=58.6% t(iid)=15.67 CI72h=[1.1064%,5.2221%] p(>0)=0.999 half=2.0578% | CI72h_x1.21=[0.7697%,5.7497%]
  Y2022: N=1692 meanNet=0.0706% meanRaw=0.8388% win=54.1% t(iid)=0.18 CI72h=[-2.7207%,2.9823%] p(>0)=0.543 half=2.8515% | CI72h_x1.21=[-3.3797%,3.5209%]
  Y2023: N=777 meanNet=1.8774% meanRaw=3.2466% win=58.0% t(iid)=4.98 CI72h=[0.6160%,3.1587%] p(>0)=1.000 half=1.2714% | CI72h_x1.21=[0.3391%,3.4158%]
  Y2024: N=1650 meanNet=3.1264% meanRaw=4.3191% win=59.6% t(iid)=10.06 CI72h=[1.4262%,4.5544%] p(>0)=1.000 half=1.5641% | CI72h_x1.21=[1.2339%,5.0190%]
  Y2025: N=3023 meanNet=1.7082% meanRaw=3.0508% win=49.6% t(iid)=3.30 CI72h=[-1.2162%,4.0514%] p(>0)=0.864 half=2.6338% | CI72h_x1.21=[-1.4787%,4.8952%]
-- %coin+ / delist / null / ICC --
  min_trades>=1: nsym=607 %coin+=67.5%
  min_trades>=5: nsym=471 %coin+=71.3%
  min_trades>=10: nsym=293 %coin+=79.5%
  completed N=11373 meanNet=2.2609% | short_delist N=8 meanNet=0.6152%
  null(block sign-flip 72h) ALL: obs=2.25977% nullMean=-0.00518% sd=0.65512% p(>=obs)=0.0000
  ICC ALL: ICC(day)=0.1639 ICC(72h)=0.0704
  null(block sign-flip 72h) DEV: obs=1.27933% nullMean=-0.00475% sd=0.87574% p(>=obs)=0.0770
  ICC DEV: ICC(day)=0.4973 ICC(72h)=0.1372
  ** CỔNG A (PREREG §3) k=1: DEV mean=+1.2793% ; CI72h_x1.21=[-0.7197%,3.2784%] ; p(>0)=0.939 => KHONG DAT **

---- A-SECONDARY (k=2, so vong truoc) ----
ALL 2021-2025: N=19992 meanNet=1.8483% meanRaw=2.8465% win=54.8% t(iid)=15.88 CI72h=[0.9619%,2.6615%] p(>0)=1.000 half=0.8498% | CI72h_x1.21=[0.8201%,2.8766%]
DEV 2022-01..2024-06: N=5837 meanNet=1.0797% meanRaw=2.0784% win=56.0% t(iid)=6.82 CI72h=[-0.2868%,2.3315%] p(>0)=0.948 half=1.3092% | CI72h_x1.21=[-0.5044%,2.6638%]
NON-DEV: N=14155 meanNet=2.1653% meanRaw=3.1633% win=54.3% t(iid)=14.36 CI72h=[1.0234%,3.2156%] p(>0)=1.000 half=1.0961% | CI72h_x1.21=[0.8390%,3.4916%]
-- by year --
  Y2021: N=6441 meanNet=2.4768% meanRaw=3.3996% win=56.0% t(iid)=15.00 CI72h=[0.8185%,4.0263%] p(>0)=0.998 half=1.6039% | CI72h_x1.21=[0.5360%,4.4175%]
  Y2022: N=2887 meanNet=-0.3323% meanRaw=0.3770% win=52.4% t(iid)=-1.31 CI72h=[-2.6375%,1.8842%] p(>0)=0.428 half=2.2609% | CI72h_x1.21=[-3.0680%,2.4033%]
  Y2023: N=1554 meanNet=1.6710% meanRaw=2.9106% win=57.3% t(iid)=6.96 CI72h=[0.5299%,2.8336%] p(>0)=0.998 half=1.1519% | CI72h_x1.21=[0.2772%,3.0647%]
  Y2024: N=3300 meanNet=3.0407% meanRaw=4.1126% win=60.2% t(iid)=15.41 CI72h=[1.3255%,4.5761%] p(>0)=1.000 half=1.6253% | CI72h_x1.21=[1.0740%,5.0073%]
  Y2025: N=5810 meanNet=1.6055% meanRaw=2.7243% win=51.0% t(iid)=5.25 CI72h=[-0.3787%,3.2566%] p(>0)=0.944 half=1.8177% | CI72h_x1.21=[-0.5939%,3.8048%]
-- %coin+ / delist / null / ICC --
  min_trades>=1: nsym=615 %coin+=70.7%
  min_trades>=5: nsym=561 %coin+=72.0%
  min_trades>=10: nsym=448 %coin+=77.2%
  completed N=19983 meanNet=1.8506% | short_delist N=9 meanNet=-3.2428%
  null(block sign-flip 72h) ALL: obs=1.84835% nullMean=-0.00925% sd=0.49730% p(>=obs)=0.0000
  ICC ALL: ICC(day)=0.2023 ICC(72h)=0.0863
  null(block sign-flip 72h) DEV: obs=1.07971% nullMean=-0.00563% sd=0.68155% p(>=obs)=0.0600
  ICC DEV: ICC(day)=0.4786 ICC(72h)=0.1651
  ** CỔNG A (PREREG §3) k=2: DEV mean=+1.0797% ; CI72h_x1.21=[-0.5044%,2.6638%] ; p(>0)=0.948 => KHONG DAT **

################ B. NEGATIVE CONTROL (placebo) ################
placebo events=11381 (day-permute, giu symbol + gio:phut, ngay ngau nhien tren DEV); rep=1..200 seed=20260905+r
  B-PRIMARY (day-permute) — ALL event: reps=200
    mean(net) qua cac rep: mean=-0.22579% sd=0.07073% min=-0.4276% max=-0.0237%
    CI72h_x1.21 half-width: median=0.1590% p80=0.1686% p95=0.1802%
    ** FP_1side (CI lo > 0, bao nham edge DUONG) = 0/200 = 0.0% **
    FP_2side (CI loai 0) = 163/200 = 81.5% | CI hi < 0 (drag chi phi, KHONG phai FP) = 163/200 = 81.5%
  B-PRIMARY (day-permute) — DEV event (headline): reps=200
    mean(net) qua cac rep: mean=-0.18630% sd=0.11500% min=-0.4640% max=+0.2039%
    CI72h_x1.21 half-width: median=0.2752% p80=0.3002% p95=0.3311%
    ** FP_1side (CI lo > 0, bao nham edge DUONG) = 0/200 = 0.0% **
    FP_2side (CI loai 0) = 43/200 = 21.5% | CI hi < 0 (drag chi phi, KHONG phai FP) = 43/200 = 21.5%

B-SECONDARY (same-minute random symbol): pool rows=2708437 ; event co pool=11381/11381
  B-SECONDARY (same-minute random symbol) — ALL: reps=200
    mean(net) qua cac rep: mean=+2.00436% sd=0.07853% min=+1.7677% max=+2.1812%
    CI72h_x1.21 half-width: median=1.0612% p80=1.0820% p95=1.0957%
    ** FP_1side (CI lo > 0, bao nham edge DUONG) = 200/200 = 100.0% **
    FP_2side (CI loai 0) = 200/200 = 100.0% | CI hi < 0 (drag chi phi, KHONG phai FP) = 0/200 = 0.0%
  B-SECONDARY — DEV: reps=200
    mean(net) qua cac rep: mean=+1.04052% sd=0.11364% min=+0.6639% max=+1.3704%
    CI72h_x1.21 half-width: median=1.8272% p80=1.9022% p95=1.9781%
    ** FP_1side (CI lo > 0, bao nham edge DUONG) = 0/200 = 0.0% **
    FP_2side (CI loai 0) = 0/200 = 0.0% | CI hi < 0 (drag chi phi, KHONG phai FP) = 0/200 = 0.0%
  (B-SECONDARY giu THOI DIEM, bo CHON SYMBOL: neu dong duong manh => edge la hieu ung
   thoi diem/market-timing co that trong du lieu, khong phai loi harness.)

################ C. POWER / MDE (don vi %/lenh) ################
Chuoi nen = placebo B-PRIMARY. Detection = CI72h_x1.21 lo > 0 (cung cong GO).
Voi chuoi net -> (net - mean) + X thi half-width KHONG doi va obs = X, nen
detection <=> X > half-width(centered) — dung dan, khong xap xi (kiem chung o duoi).
  kiem chung danh tinh (3 rep): rep0: X=1% -> ci_lo=0.700582% (X-half=0.700582%) | rep50: X=1% -> ci_lo=0.690929% (X-half=0.690929%) | rep100: X=1% -> ci_lo=0.746019% (X-half=0.746019%)
  MDE @ N = N_A_PRIMARY_DEV: n_rep=200 | half-width(centered) median=0.2752% p80=0.3002% p95=0.3311%
    X= 0.25% -> power=16.0%
    X= 0.50% -> power=100.0%
    X= 1.00% -> power=100.0%
    X= 2.00% -> power=100.0%
    X= 4.00% -> power=100.0%
    => MDE (X nho nhat power>=80%) = 0.50%/lenh
  (N_A_PRIMARY_DEV = 3167 event; N_placebo/dev/rep = 1)

-- MDE theo N (lay mau con chuoi placebo DEV, 200 rep/N) --
  N        n_rep  half_med   MDE(80%)
  100      200     1.4991%   2.00%
     X= 0.25% -> power=0.0%
     X= 0.50% -> power=0.0%
     X= 1.00% -> power=2.5%
     X= 2.00% -> power=91.5%
     X= 4.00% -> power=100.0%
  200      200     1.0396%   2.00%
     X= 0.25% -> power=0.0%
     X= 0.50% -> power=0.0%
     X= 1.00% -> power=42.0%
     X= 2.00% -> power=98.5%
     X= 4.00% -> power=100.0%
  500      200     0.6642%   1.00%
     X= 0.25% -> power=0.0%
     X= 0.50% -> power=0.5%
     X= 1.00% -> power=98.5%
     X= 2.00% -> power=100.0%
     X= 4.00% -> power=100.0%
  1000     200     0.4793%   1.00%
     X= 0.25% -> power=0.0%
     X= 0.50% -> power=63.0%
     X= 1.00% -> power=100.0%
     X= 2.00% -> power=100.0%
     X= 4.00% -> power=100.0%
  2000     200     0.3526%   0.50%
     X= 0.25% -> power=0.0%
     X= 0.50% -> power=100.0%
     X= 1.00% -> power=100.0%
     X= 2.00% -> power=100.0%
     X= 4.00% -> power=100.0%

---- C-SENSITIVITY (exploratory, POST-HOC, khong thuoc thiet ke pre-reg) ----
B-PRIMARY (day-permute) lam PHANG cum thoi gian (ngay ngau nhien) => half-width nho gia tao.
Nen B-SECONDARY (same-minute random symbol) giu DUNG thoi diem MOM15 => half-width that cua
mot tin hieu kieu capitulation voi cung N:
  N=3167   half_med=1.8272% -> power 0.25/0.5/1/2/4% = 0/0/0/96/100 ; MDE(80%)=2.00%
  N=100    half_med=2.7691% -> power 0.25/0.5/1/2/4% = 0/0/0/10/91 ; MDE(80%)=4.00%
  N=200    half_med=2.3735% -> power 0.25/0.5/1/2/4% = 0/0/0/22/99 ; MDE(80%)=4.00%
  N=500    half_med=2.0187% -> power 0.25/0.5/1/2/4% = 0/0/0/48/100 ; MDE(80%)=4.00%
  N=1000   half_med=1.9367% -> power 0.25/0.5/1/2/4% = 0/0/0/60/100 ; MDE(80%)=4.00%
  N=2000   half_med=1.8492% -> power 0.25/0.5/1/2/4% = 0/0/0/81/100 ; MDE(80%)=2.00%

---- SO SANH: hieu ung DEV do duoc cua cac ung vien da NULL vs MDE ----
| ung vien | N_DEV | net DEV do duoc | MDE(day-permute)@N | MDE(clustered)@N | ket luan |
| reversal-bounce long | 1179302 | -0.080% | 0.43% (CI rieng) | n/a (khong cum) | DƯỚI MDE: |net|=0.08% < MDE~0.5% (CI rieng cua chinh no: half 0.36% -> x1.21 = 0.43%) |
| BIG_UP (cu) | ~89 | +0.87% | 2.00% | 4.00% | DƯỚI MDE |
| MEDIUM_UP (cu) | ~316 | +1.84% | 2.00% | 4.00% | DƯỚI MDE |
| MEDIUM_DOWN (cu) | ~158 | +1.25% | 2.00% | 4.00% | DƯỚI MDE |

Ghi chu: N_DEV cua BIG_UP/MEDIUM_UP/MEDIUM_DOWN = tong N theo nam 2022+2023+2024 trong
docs/RESULT_BIGUP_MEDIUPDOWN.md §3.2 (can tren, 2024 chi tinh 6 thang); reversal-bounce N=1 179 302
va net DEV -0.080% lay tu docs/RESULT_REVERSAL_BOUNCE.md (CI rieng cua no: half x1.21=0.43%).
```
