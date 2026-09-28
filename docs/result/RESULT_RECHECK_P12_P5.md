# RESULT — CHẤM LẠI **P12** (ngưỡng rào ĐÚNG) + **P5** (rate chuẩn `profit` % + MTM mốc phút)

- Pre-reg: `docs/prereg/PREREG_RECHECK_P12_P5.md` (commit `56af3cc`, **chốt trước** khi lập bảng đối chiếu).
- Nguồn: `Claude outputs/AUDIT_20260928_B_bugs.md` §5 P12/§1#25 và §5 P5/§1#31#32; §4.
- Offline Python, dùng lại output có sẵn. **0 train · 0 sim · 0 Java · 0 chạm 2026/242/ONNX/LIVE.**
- Script tái lập: `research/analysis/recheck_p12_appetite.py`, `research/analysis/recheck_p5_rates.py`.
  Số: `docs/result/RECHECK_P12_P5.json`.
- **Luật đã khóa:** chỉ báo **ĐỔI / KHÔNG ĐỔI**. Ngưỡng A=`current` 30/200/−15 · B=`latest` 40/250/−20.

## 0. TÓM TẮT (3 con số)

| việc | ô chấm lại | ĐỔI | chiều |
|---|---|---|---|
| **P12** — verdict rào in bằng `x1_rates` mặc định `current` (khung 09-24→09-26) | **37** (10 doc) | **16** (trong đó **12 chắc** + **4 điều kiện conc**) | **100 % FAIL→PASS** |
| **P5** — 4 vòng EXIT_STRUCT/SHAPE1/FAMILY2/SIZE_COUNT | **19 arm** | **0** | — |
| kết luận **cấp vòng** bị ĐẢO (PASS↔FAIL) | — | **0** | — |

> ⚠️ **CẢNH BÁO `conc` (đọc trước):** `x1_rates.py` **KHÔNG đo** ràng buộc "tập trung 1 coin ≤ 15 %"
> (chính doc các vòng ghi "coin≤15 % KHÔNG đo"). 16 ô dưới đây là theo **đúng tập ràng buộc `x1_rates` đo được**
> (`maxDD · UW · quý · năm âm`). **4 ô thuộc họ `T100/gate-1.0`** có conc đã biết **27,23 % > 15 %**
> (`RESULT_CONC_CAP_HIGHN.md:127-143`) ⇒ **vẫn FAIL** nếu không bật `CONC_CAP_PERCOIN=15 %`
> (bật ⇒ `cc-t100` conc 10,83 % ⇒ PASS). Vậy **12 ô đổi CHẮC**, **4 ô đổi CÓ ĐIỀU KIỆN**.

---

## 1. VIỆC 1 — P12: chấm lại bằng ngưỡng ĐÚNG

### 1.1 Phạm vi, và một đính chính về cửa sổ

`research/analysis/x1_rates.py:24-40` (fix `beaccba`, 26/09 23:23) ghi: **trước fix, mặc định khẩu vị là
`current` = 30/200/−15**, trong khi khẩu vị owner đã chốt là `latest` = 40/250/−20 ⇒ **mọi verdict rào in ra
bị chặt hơn ngưỡng owner**.

Cửa sổ "09-24 → 09-26" theo `git log` (last-commit) **gồm cả commit tổ chức lại `docs/` `37fd502`
(09-24 20:55, 881 file)** ⇒ nó **kéo theo cả ~9 doc cũ (09-14 → 09-22)** đang mang verdict `--appetite current`.
Đó chính là các doc bị ảnh hưởng. **Đính chính:** 7 doc *mới sinh* trong 09-24→09-26 có verdict rào
(`RESULT_GATESCALE_KEEPLEG0` `:100-127`, `RESULT_GATESCALE_SWEEP` `:96-121`, `RESULT_CONC_CAP_HIGHN` `:127-143`,
`RESULT_ARM44`, `RESULT_STAGE3_SIM`, `RESULT_SIM_CADENCE_MATCH`, `RESULT_GATE_RECAL`) **đã tự chấm lại dưới
ngưỡng MỚI** trong chính vòng đó (#14/#15 đã được xử lý tại chỗ) ⇒ **0 đổi** ở nhóm này.

### 1.2 Bảng `verdict cũ → verdict mới`

| doc:line | ô chấm | verdict CŨ (`current`) | verdict MỚI (`latest`) | ĐỔI | do đâu |
|---|---|---|---|---|---|
| `RESULT_REGIME_GATE.md:40` | gate-1.0/T100 | FAIL | PASS | ✔ | UW-2025 **227** ≤ 250 |
| `RESULT_REGIME_GATE.md:40` | R | FAIL | PASS | ✔ | UW-2025 **223** ≤ 250 |
| `RESULT_REGIME_UPDOWN.md:45` | T100 / gate-1.0 | FAIL | PASS | ✔ | UW-2025 227 |
| `RESULT_REGIME_UPDOWN.md:45` | R | FAIL | PASS | ✔ | UW-2025 223 |
| `RESULT_REGIME_UPDOWN.md:45` | **RA12** | FAIL | PASS | ✔ | UW-2024 **205** *và* UW-2025 **221** |
| `RESULT_BREADTH_GATE_SIM.md:77` | T100 / gate-1.0 | FAIL | PASS | ✔ | UW-2025 227 |
| `RESULT_BREADTH_GATE_SIM.md:77` | BR0 | FAIL | PASS | ✔ | UW-2025 221 |
| `RESULT_DD_THROTTLE.md:61` | DT | FAIL | PASS | ✔ | UW-2025 223 |
| `RESULT_PACING_BIGDOWN.md:39` | T100 | FAIL | PASS | ✔ | UW-2025 227 |
| `RESULT_PACING_BIGDOWN.md:39` | P0 | FAIL | PASS | ✔ | UW-2025 221 |
| `RESULT_PACING_BIGDOWN.md:39` | P3 | FAIL | PASS | ✔ | UW-2025 232 |
| `RESULT_BREADTH_CONT.md:49` | BRC | FAIL | PASS | ✔ | UW-2025 221 |
| `RESULT_BREADTH_CONT_T50.md:57` | BRC | FAIL | PASS | ✔ | UW-2025 221 |
| `RESULT_BREADTH_CONT_T50.md:57` | BRCT50 | FAIL | PASS | ✔ | UW-2025 223 |
| `RESULT_GATE_CALIB.md:56` | T130 | FAIL | PASS | ✔ | UW **221** |
| `RESULT_EXIT_HIGH_N.md:192` | GD92+LADDER L1 | FAIL | PASS | ✔ | UW 245 ≤ 250, conc 14,44 ≤ 15 |
| `RESULT_EXIT_HIGH_N.md:192` | T100 base | FAIL | **FAIL** | ✗ | **conc 27,23 > 15 (CỨNG)** |
| `RESULT_EXIT_HIGH_N.md:192` | GD92 base / +HINGE V3 | FAIL | **FAIL** | ✗ | UW **278** > 250 |
| `RESULT_HEDGE_OVERLAY_A.md:117` | GỐC + HEDGED | PASS / PASS | PASS / PASS | ✗ | đã PASS dưới `current` |
| (đã tự sửa tại chỗ) `RESULT_GATESCALE_KEEPLEG0.md:100-127`, `RESULT_GATESCALE_SWEEP.md:96-121`, `RESULT_CONC_CAP_HIGHN.md:127-143` | 6 + 6 + 4 | (đã in R-MOI/S3) | y nguyên | ✗ | ngưỡng mới đã áp trong vòng |

**Tổng: 37 ô / 16 ĐỔI / 0 ĐỔI chiều ngược** (12 chắc + 4 điều kiện `conc`).
Sàng toàn bộ tag có `sim.out` (2 base, 460 tag): **85 tag đổi verdict**, **tất cả** `FAIL→PASS`, **tất cả** chỉ vì
`UW ∈ (200,250]` (`docs/result/RECHECK_P12_P5.json → p12.tag_current_fail`). **Không** ô nào đổi vì
`maxDD ∈ (30,40]` hay `quy ∈ [−20,−15)`. *(85 tag này cũng CHƯA trừ `conc`.)*

---

## 2. VIỆC 2 — P5: chấm lại 4 vòng bằng rate `profit` % + rào/(a)/(b′)

### 2.1 Rate (cột `profit` %, chuẩn `c3_rates.rates`) — 4 vòng, 16 tag
(bản CŨ trên `pnl` USDT chạy song song **khớp số đã công bố** ⇒ ống đo tái lập đúng; chỉ **đơn vị** khác.)

| arm | n | win% | TSloss% | mP\|SM | mP\|SL | mMargin | (CŨ) win% / mP\|SM / mP\|SL |
|---|---|---|---|---|---|---|---|
| A0=S0=N0=B0 `cd-sel15` | 744 | 88,71 | 9,81 | **+7,70** | **−16,64** | 1490,6 | 88,44 / +89,37 / −318,48 |
| A1 `xs-a1` | 780 | 91,41 | 0,00 | +8,47 | — (suy biến) | 760,7 | 91,28 / +44,89 / — |
| A2 `xs-a2` | 935 | 85,13 | 0,00 | +7,07 | — | 262,5 | 84,71 / +15,28 / — |
| A3 `xs-a3` | 877 | 83,12 | 7,41 | +7,08 | −14,11 | 264,2 | 82,67 / +15,60 / −42,32 |
| S1 `sh1-s1-sl05` | 1285 | 47,94 | 52,06 | +7,23 | −5,82 | 1100,5 | 47,86 / +70,54 / −73,34 |
| S2 `sh1-s2-sl03k16` | 2510 | 37,17 | 62,83 | +7,20 | −3,58 | 798,0 | 37,13 / +50,42 / −35,92 |
| S3 `sh1-s3-ts8` | 833 | 72,99 | 35,29 | +7,98 | −5,23 | 1275,8 | **70,83** / +78,61 / −80,52 |
| S4 `sh1-s4-sl03` | 1506 | 35,99 | 64,01 | +7,15 | −3,71 | 1030,0 | 35,92 / +65,29 / −46,87 |
| N1 `tp-n1` | 2563 | 31,14 | 68,86 | 0,00 | −1,50 | 754,0 | 31,25 / 0,00 / −17,58 |
| N2 `tp-n2` | 2734 | 41,73 | 58,27 | 0,00 | −1,51 | 725,7 | 41,84 / 0,00 / −16,95 |
| N3 `tp-n3` | 2270 | 31,37 | 68,63 | +1,18 | −2,02 | 780,3 | 31,37 / +2,94 / −22,19 |
| N4 `tp-n4` | 2563 | 31,14 | 68,86 | 0,00 | −1,50 | 754,0 | (≡N1) |
| B1 `sc-b1` | 745 | 88,46 | 9,66 | +7,33 | −16,64 | 791,8 | 88,19 / +48,57 / −155,62 |
| B2 `sc-b2` | 1152 | 88,98 | 9,81 | +7,33 | −15,73 | 728,5 | 88,80 / +44,61 / −137,72 |
| B3 `sc-b3` | 1885 | 88,22 | 10,56 | +7,19 | −14,61 | 356,2 | 87,85 / +21,73 / −59,42 |
| B4 `sc-b4` | 1878 | 88,23 | 10,86 | +7,45 | −14,12 | 605,5 | 87,86 / +36,85 / −106,69 |

**Đổi đơn vị (lỗi #31) làm gì?** `TSloss%`/`mMargin` **y nguyên**; `win%` lệch **≤ 2,16 pp**
(S3: 70,83 → 72,99 — do `pnl` có funding, dấu khác `profit`); `mP|SM`, `mP|SL` đổi **đơn vị hoàn toàn**
(vd A0 `+7,70 %` vs `+89,37 USDT`). **Không** đổi chiều dấu nào ⇒ **0 verdict lật vì #31** ở 4 vòng này;
bằng chứng "≥2 rate ngoài CI" của các vòng vẫn **0–1 rate** như doc đã ghi.

### 2.2 Rào (a) · (b′) · rào cứng `latest` — `verdict cũ → verdict mới`

Định nghĩa (a)/(b′)/`tf_5`/`conc_5`/`wl_ratio`/`loss_mean`/`q*` = **nguyên văn `ofi_reorient_rulers.point()`**
(`net = pnl`); `maxDD/UW` = chuỗi **NGÀY** (như doc vòng đã in) **+ cột ước lượng MTM phút**.

| vòng | arm | (a) `%top-1≤15` | (b′) bỏ-50 % > 0 | **CẢ HAI** | rào `latest` (NGÀY) | `maxDD` ngày / **ước MTM phút** | UW ngày | qmin | năm âm | rào (ƯỚC MTM) | **ĐỔI?** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXIT_STRUCT | A0 `cd-sel15` | FAIL 19,13 | FAIL −17.551 | FAIL | **PASS** | −6,27 / −14,97 | 166 | −3,36 | – | PASS | ✗ |
| EXIT_STRUCT | A1 `xs-a1` | FAIL 37,35 | FAIL −21.073 | FAIL | FAIL | −12,38 / −21,08 | 318 | −5,88 | 2022,2025 | FAIL | ✗ |
| EXIT_STRUCT | A2 `xs-a2` | FAIL 16,10 | FAIL −4.622 | FAIL | **PASS** | −4,76 / −13,46 | 92 | −0,18 | – | PASS | ✗ |
| EXIT_STRUCT | A3 `xs-a3` | FAIL 16,68 | FAIL −3.541 | FAIL | FAIL | −1,59 / −10,29 | **276** | −0,05 | – | FAIL | ✗ |
| SHAPE1 | S0 = A0 | FAIL 19,13 | FAIL −17.551 | FAIL | PASS | −6,27 / −14,97 | 166 | −3,36 | – | PASS | ✗ |
| SHAPE1 | S1 `sl05` | FAIL (LỖ) | FAIL −48.012 | FAIL | FAIL | −21,40 / −30,10 | 1487 | −9,00 | 3 năm | FAIL | ✗ |
| SHAPE1 | S2 `sl03k16` | FAIL (LỖ) | FAIL −50.893 | FAIL | FAIL | −28,84 / −37,54 | 1487 | −16,10 | 4 năm | FAIL | ✗ |
| SHAPE1 | S3 `ts8` | FAIL 32,30 | FAIL −24.032 | FAIL | **PASS** | −4,56 / −13,26 | 233 | −0,89 | – | PASS | ✗ |
| SHAPE1 | S4 `sl03` | FAIL (LỖ) | FAIL −39.057 | FAIL | FAIL | −28,57 / −37,27 | 1487 | −13,06 | 4 năm | FAIL | ✗ |
| FAMILY2 | N0 = A0 | FAIL 19,13 | FAIL −17.551 | FAIL | PASS | −6,27 / −14,97 | 166 | −3,36 | – | PASS | ✗ |
| FAMILY2 | N1 `tp-n1` | FAIL (LỖ) | FAIL −26.940 | FAIL | FAIL | −68,27 / −76,97 | 1575 | −26,45 | 5 năm | FAIL | ✗ |
| FAMILY2 | N2 `tp-n2` | FAIL (LỖ) | FAIL −25.566 | FAIL | FAIL | −67,14 / −75,84 | 1538 | −20,99 | 5 năm | FAIL | ✗ |
| FAMILY2 | N3 `tp-n3` | FAIL (LỖ) | FAIL −29.669 | FAIL | FAIL | −64,39 / −73,09 | 1618 | −23,36 | 5 năm | FAIL | ✗ |
| FAMILY2 | N4 `tp-n4` | ≡ N1 | ≡ N1 | FAIL | FAIL | ≡ N1 | 1575 | −26,45 | 5 năm | FAIL | ✗ |
| SIZE_COUNT | B0 = A0 | FAIL 19,13 | FAIL −17.551 | FAIL | PASS | −6,27 / −14,97 | 166 | −3,36 | – | PASS | ✗ |
| SIZE_COUNT | B1 `sc-b1` | FAIL 18,69 | FAIL −7.657 | FAIL | **PASS** | −3,90 / −12,60 | 164 | −1,56 | – | PASS | ✗ |
| SIZE_COUNT | B2 `sc-b2` | FAIL 15,83 | FAIL −10.396 | FAIL | **PASS** | −5,48 / −14,18 | 164 | −1,36 | – | PASS | ✗ |
| SIZE_COUNT | B3 `sc-b3` | FAIL 15,23 | FAIL −8.098 | FAIL | FAIL | −5,00 / −13,70 | **278** | −0,78 | – | FAIL | ✗ |
| SIZE_COUNT | B4 `sc-b4` | FAIL 16,80 | FAIL −16.679 | FAIL | FAIL | −7,04 / −15,74 | **277** | −2,27 | – | FAIL | ✗ |

**Kết quả: 19/19 arm GIỮ NGUYÊN verdict** (rào · (a) · (b′)) — **0 ĐỔI**.
- **MTM mốc phút:** `intradaydd/series.npz` **chỉ có 4 nền** (T170/KEEPLEG0/T100/GD92); dữ liệu ticker 1 phút
  trên Oracle **đã mất** (`kaggle_data_hpo` chỉ còn `daily`) ⇒ **KHÔNG tính được MTM phút cho 16 tag**.
  Ước lượng dịch **−8,7 pp** (trung bình 4 nền: −8,12 / −8,75 / −10,13 / −7,76). Với dịch này maxDD năm xấu nhất
  là **S2/S4 ≈ −37,5 %** và **N1/N3 ≈ −77 %** ⇒ **không** arm nào bị đẩy qua trần 40 % **và** không arm nào được cứu.
- **conc 1 coin:** lấy theo doc đã công bố (mọi arm ≤ 15 %; B3 2,12 % … A1 12,62 %) ⇒ **không bind** ở vòng nào.
- **`q*`** (bỏ bao nhiêu % thì PnL = 0; bước quét 0,5 % nên giá trị thật ≤ số in): A0 **21,5 %** · A1 6,5 · A2 22,0 ·
  A3 24,0 · S1 ≤0,5 · S2 ≤0,5 · S3 8,5 · S4 ≤0,5 · B1 25,0 · B2 25,5 · B3 26,0 · B4 22,5 —
  lãi vẫn **tập trung ở 0,1–26 % lệnh đầu** (doc vòng in S1/S4 ≈ 0,1 %).

---

## 3. TRẢ LỜI (khóa)

**(1) P12 — bao nhiêu verdict ĐỔI?** **16 / 37 ô** (10 doc), **tất cả FAIL→PASS**, **0 PASS→FAIL**.
Trong đó **12 ô CHẮC** và **4 ô ĐIỀU KIỆN** (họ `T100/gate-1.0`, chỉ PASS nếu bật `CONC_CAP_PERCOIN=15 %`
— `x1_rates` không đo conc). Liệt kê ở §1.2. Nguyên nhân **duy nhất**: `UW ∈ (200, 250]`.
⚠️ Đính chính: **7 doc mới sinh** trong 09-24→09-26 (**GATESCALE_KEEPLEG0 / GATESCALE_SWEEP / CONC_CAP_HIGHN /
ARM44 / STAGE3_SIM / SIM_CADENCE_MATCH / GATE_RECAL**) **đã** tự chấm dưới ngưỡng mới ⇒ **0 đổi**; 16 ô đổi nằm ở
**9 doc cũ 09-14 → 09-22** bị kéo vào cửa sổ bởi commit tổ chức lại `docs/` **`37fd502` (09-24 20:55)**.

**(2) P5 — bao nhiêu arm ĐỔI verdict?** **0 / 19** (16 tag, 4 vòng: EXIT_STRUCT · SHAPE1 · FAMILY2 · SIZE_COUNT).
- Sửa đơn vị rate (#31, `pnl` USDT → `profit` %) **không** lật ô nào; chỉ đổi **độ lớn** (`mP|SM` `+89,37 → +7,70`,
  `win%` lệch ≤ 2,16 pp).
- MTM mốc phút: **không đo được** cho 16 tag; ước lượng −8,7 pp **không** đẩy arm nào qua trần 40 %
  (S2/S4 ≈ −37,5 % là sát nhất) ⇒ cũng **0 lật**.
- `(a)` **0/19 PASS** · `(b′)` **0/19 PASS** · **CẢ HAI 0/19** — như doc đã ghi.

**(3) Có kết luận nào bị ĐẢO (PASS↔FAIL) không?**
- **Cấp VÒNG: KHÔNG.** Cả 10 vòng P12 vẫn **NULL** trên tiêu chí bằng chứng (u1–u5 / 0 rate ngoài CI) —
  rào chỉ là **một** trong các điều kiện, không phải điều kiện duy nhất.
- **Cấp LÝ DO: CÓ, và đây là cái bị đảo thật.** 3 chỗ nghiêm trọng nhất:
  1. **`RESULT_BREADTH_GATE_SIM.md:77`** — câu "**BR là biến thể ĐẦU TIÊN (trong 7 vòng) đưa UW-2025
     xuống dưới ngưỡng 200**" **mất tính duy nhất**: dưới ngưỡng owner (250), **T100/gate-1.0 (227)** và
     **BR0 (221)** cũng PASS ⇒ "UW>200" **không còn** là cái phân biệt BR với phần còn lại.
  2. **`RESULT_DD_THROTTLE.md:61`** + **`RESULT_PACING_BIGDOWN.md:39`** — kết luận "P0/P3/DT **không** đưa gate 1.0
     về đạt khẩu vị" (vỡ ở 2025) **hết đúng**: cả 3 PASS dưới `latest`.
  3. **`RESULT_REGIME_UPDOWN.md:45`** — RA12 bị kết luận "**còn làm HỎNG THÊM năm 2024** (UW 205)";
     dưới ngưỡng owner 2024 (205 ≤ 250) **không hỏng** ⇒ "phát hiện quan trọng nhất" của vòng **không còn đứng**.
- **Cấp EDGE ("cạn"): KHÔNG đảo** — P12 đổi **lý do**, không đổi **kết luận**; P5 đổi **0**.

**(4) Khối NULL hiện tại còn vững không? Đề xuất chạy lại?**
- **Còn vững về kết luận "cạn edge"** — nhưng **KHÔNG còn vững về lý do**. 16 ô đổi nghĩa là câu
  "đóng vì vỡ khẩu vị (UW>200)" đã **hết hiệu lực** ở các trục **breadth / regime / pacing / dd-throttle /
  gate-calib / exit-high-n**; các vòng đó phải được **đóng bằng lý do khác** (0 rate ngoài CI / u1–u5).
- **Ưu tiên chạy lại (1–3):**
  1. **P8-rút gọn (cao nhất, 0 compute):** đóng lại **breadth / regime / pacing / dd-throttle** dưới
     `--appetite latest` + MTM mốc phút, để mỗi NULL có **lý do đúng** (đây là hệ quả trực tiếp của 16 ô đổi).
  2. **P4 (0 compute):** tái xét **incumbent T170/KEEPLEG0 vs `cc-t100` (T100 **kèm** `CONC_CAP_PERCOIN=15 %`)**
     dưới luật §10.2 + `latest` — vì T100 trần UW 227 chỉ PASS rào **khi có cap conc** (`cc-t100` conc 10,83 %),
     và T100 là nền của nhiều NULL.
  3. **P6 (1 chân Kaggle ~20′):** EXIT_STRUCT **arm A2 khớp size** (`F_BASE`×~6) — confound #30 là lỗ hổng
     **chưa** khử được (P5 không khử được nó vì dùng lại output có sẵn).

## 4. MỤC BỎ + GIỚI HẠN

- **BỎ `meanP`** (đồng nhất thức, 408/408) · **BỎ rate trên cột `pnl` để ra verdict** (chỉ dùng đối chiếu) ·
  **BỎ `win%` riêng lẻ** (ρ −0,99 với `TSloss%`).
- **KHÔNG ĐO ĐƯỢC MTM mốc phút cho 16 tag** (thiếu ticker 1 phút offline) ⇒ cột "ước MTM phút" là `[SUY LUẬN]`
  (dịch −8,7 pp), **không** phải số đo; muốn số thật phải chạy `s3_intraday.py` **trên Kaggle** (cần ticker 1m).
- `gross ≤ 70 %` (định nghĩa LEDGER) **không** chấm ở đây (ngoài phạm vi; xem `RESULT_GROSS_ASYMMAP`).
- Không chấm lại tier MODEL / money-ruler (ngoài P12/P5). Không mở lại ứng viên. Không chạm 2026/242/ONNX/LIVE.
