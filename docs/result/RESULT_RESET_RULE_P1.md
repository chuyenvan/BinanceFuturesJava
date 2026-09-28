# RESULT_RESET_RULE_P1 — CHẤM LẠI HẬU KIỂM 20 ARTIFACT theo LUẬT 4 TẦNG @`base 0,112` và @`stress 0,150` (%/vòng)

Ngày: **2026-09-28** (D2, `PLAN_OPENCLAW_ADDENDUM_20260928.md` §D2). Pre-reg: **`docs/prereg/PREREG_RESET_RULE_P1.md`**
(**commit `f9ea849`**, chốt **TRƯỚC**; sau đó **không sửa thiết kế**). Công cụ: `research/analysis/reset_rule_score.py`.
JSON: `docs/result/reset_rule_p1.json`.

**Tuân thủ:** thuần Python **offline** · **0 sim / 0 train** · box Oracle **nhẹ** (4 worker, 1 lượt duyệt 1.631 ngày ticker) ·
**KHÔNG** chạm production/`242`/ONNX/LIVE · **KHÔNG** push dữ liệu · **DEV ≤ 2025-12-31** (mốc cuối 2025-12-25) · không ghi file lớn.

---

## 0. KẾT LUẬN (4 dòng)

1. **Công cụ chấm ĐÚNG**: tự kiểm 12/12 khoản của `KEEPLEG0`/`cd-sel15` khớp số đã công bố **và**
   tái tạo **maxDD MTM phút `KEEPLEG0` = `−19,96 %` / UW `147,2` ngày** — khớp **chính xác** `RESULT_INTRADAY_DD`.
   MTM phút **chấm được cho cả 20 đối tượng** (thiếu ticker: **1 leg-ngày** duy nhất — `rc-a-q995` — coi như ~0).
2. Ở `base`/`stress`: **T1 15/20 · T2 12/20 · T3 13/20 · T4 0/20** PASS. `B*` (`kg0-g170`) **qua T1–T3**;
   **KHÔNG ứng viên nào qua T4** ⇒ theo luật **giữ `B*`** — nhưng xem §6 (ngưỡng `n ≥ 1,3×B*` đang loại trước các arm
   chất lượng cao hơn `B*` về Calmar).
3. **Hạ phí 0,8 → 0,112 CÓ lật một phần**: **6 đối tượng** đổi trạng thái **T1** (đều FAIL→PASS, *do UW co lại*),
   **2 đối tượng** đổi **T2** (do `q*` vượt 15 %), **0** ở T3/T4. **Nhưng verdict "nới gate/nhiều lệnh = RÁC" KHÔNG lật**:
   `kg0-g125`, `gs2-t125`, `cc-t100`, `rc-a-*` vẫn FAIL ở T2 và/hoặc T3.
4. Tầng 3 (`win%`/`TSloss%`/`mP|SM`/`mP|SL` trên **`profit` %**) **bất biến theo chi phí** (đã khai trước ở pre-reg §2)
   ⇒ hạ phí **không thể** cứu arm kém chất lượng; nó chỉ mở lại **rào rủi ro (T1)** và **bền PnL (T2)**.

---

## 1. TỰ KIỂM (cổng DỪNG — PASS 12/12 + cổng MTM)

| đối tượng | n | equity | CAGR % | maxDD daily % | q* % | %top-1 % | md5 | kết |
|---|---|---|---|---|---|---|---|---|
| `FG_KEEPLEG0` (`kg0-g170`) | 1 085 | 103 083 | +27,14 | −11,21 | 19,0 | 23,74 | `99e42b75` | **12/12 OK** |
| `cd-sel15` | 744 | 71 718 | +17,29 | −6,27 | 21,2 | 19,13 | `13171916` | **12/12 OK** |
| **cổng MTM** `KEEPLEG0` | — | — | — | — | — | — | — | maxDD phút **−19,96 %** (cb −19,96) · UW **147,2 ngày** (cb 147,2) ⇒ **OK** |

Các số công bố có làm tròn (dung sai ≤ 0,15 pp). *Ghi chú minh bạch:* đã vấp **2 bug ở lượt chạy đầu** —
(i) `np.searchsorted` với `np.datetime64('YYYYMMDD')` bị hiểu là **NĂM** (không phải ngày) ⇒ nhánh realized sai;
(ii) suy tên symbol ticker thiếu hậu tố `USDT`. Cả hai đã sửa, **đã kiểm V2** `equity_mtm(mốc 0)` vs `b+unP` in ra:
`|lệch| ≤ 0,8 USDT` trên 6 ngày × 3 tag. Kết quả dưới đây là của bản **đã sửa**.

---

## 2. BẢNG 4 TẦNG @`base` = 0,112 %/vòng

Chi phí hậu kiểm: `net = pnl + (0,008 − c)·notional`, `c = 0,00112` (**xấp xỉ tuyến tính, bỏ qua compounding**).
`ddPhut` = maxDD **MTM phút năm xấu nhất**; `UW` = ngày dài nhất dưới đỉnh chạy (chuỗi phút).

| tag | n | equity | CAGR % | ddPhut % (năm) | UW ngày | q* % | top-1 % | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kg0-g170` = **`B*`** | 1085 | 116141 | +30.56 | **-17.84** (2025) | 147.2 | 25.3 | 20.15 | PASS | PASS | PASS | ref |
| `cd-sel15` | 744 | 79348 | +19.96 | **-15.81** (2025) | 167.7 | 27.8 | 15.99 | PASS | PASS | PASS | FAIL |
| `sc-b1` | 745 | 60539 | +12.95 | **-10.77** (2025) | 167.7 | 32.5 | 15.86 | PASS | PASS | PASS | FAIL |
| `sc-b2` | 1152 | 71565 | +17.23 | **-13.63** (2025) | 167.7 | 32.8 | 13.47 | PASS | PASS | PASS | FAIL |
| `sc-b3` | 1885 | 64434 | +14.53 | **-10.98** (2025) | 230.7 | 33.5 | 12.99 | PASS | PASS | PASS | FAIL |
| `sc-b4` | 1878 | 82742 | +21.08 | **-15.88** (2025) | 186.3 | 28.6 | 14.24 | PASS | PASS | PASS | FAIL |
| `kg0-g155` | 1245 | 112708 | +29.69 | **-17.24** (2025) | 164.7 | 19.8 | 21.05 | PASS | PASS | PASS | FAIL |
| `kg0-g140` | 1411 | 117793 | +30.97 | **-17.02** (2022) | 164.9 | 17.2 | 20.89 | PASS | PASS | FAIL | FAIL |
| `kg0-g125` | 1701 | 113841 | +29.98 | **-17.37** (2022) | 126.8 | 12.3 | 24.94 | PASS | FAIL | FAIL | FAIL |
| `gs2-t155` | 1249 | 127612 | +33.32 | **-17.25** (2025) | 164.7 | 19.9 | 26.30 | PASS | FAIL | PASS | FAIL |
| `gs2-t140` | 1416 | 135090 | +35.02 | **-16.96** (2025) | 164.9 | 17.2 | 26.82 | PASS | FAIL | PASS | FAIL |
| `gs2-t125` | 1708 | 117063 | +30.79 | **-17.16** (2022) | 126.8 | 10.8 | 29.14 | FAIL | FAIL | FAIL | FAIL |
| `cc-t100` | 2557 | 164314 | +41.03 | **-19.25** (2022) | 210.1 | 10.0 | 30.96 | PASS | FAIL | FAIL | FAIL |
| `gr-kg0-q995` | 1021 | 112076 | +29.53 | **-17.87** (2025) | 147.2 | 27.1 | 18.28 | PASS | PASS | PASS | FAIL |
| `gr-kg0-q998` | 954 | 109435 | +28.84 | **-17.89** (2025) | 147.2 | 29.9 | 17.62 | PASS | PASS | PASS | FAIL |
| `gr-kg0-q999` | 868 | 101190 | +26.62 | **-17.96** (2025) | 145.3 | 29.0 | 17.86 | PASS | PASS | PASS | FAIL |
| `gr-kg0-q998-15m` | 420 | 60216 | +12.82 | **-11.59** (2025) | 279.3 | 45.0 | 10.98 | FAIL | PASS | PASS | FAIL |
| `rc-a-q995` | 3256 | 98515 | +25.87 | **-30.85** (2022) | 475.2 | 6.3 | 30.35 | FAIL | FAIL | FAIL | FAIL |
| `rc-a-q998` | 1875 | 80857 | +20.46 | **-20.77** (2022) | 356.3 | 9.0 | 23.44 | FAIL | FAIL | FAIL | FAIL |
| `rc-a-q999` | 1297 | 63078 | +13.99 | **-20.00** (2022) | 568.6 | 8.9 | 23.69 | FAIL | FAIL | FAIL | FAIL |

**Lý do FAIL (bám theo rào, không diễn giải thêm):**
- **T1**: `gr-kg0-q998-15m` (UW **279,3** > 250); `gs2-t125` (**conc 33,7 %** > 15 %); `rc-a-q99x` (UW **356–569** > 250
  **và** năm **2022 âm**). Mọi tag khác: `maxDD phút ≤ 19,25 %` (≪ 40), `qmin ≥ −3,73` (≥ −20), `gross ≤ 52,7 %` (≤ 70),
  `conc ≤ 14,5 %`.
- **T2**: `kg0-g125` (`q* 12,3` < 15); `gs2-t155/t140`, `cc-t100`, `rc-a-q99x` (**top-1 % > 25**);
  riêng "bỏ top-3 episode > 0": **20/20 PASS** (không bind).
- **T3** (CI block-72h paired, 2000 rep, seed `20260905`, `inflate(19) = 2,4267`): `kg0-g140`
  (`TSloss% +2,58 pp` > +2,5); `kg0-g125` (`win% −2,90 pp`, `TSloss% +4,08 pp`); `gs2-t125` (−2,84 / +3,67);
  `cc-t100` (−3,77 / +4,77); `rc-a-q99x` (−7,5…−8,8 / +9,0…+11,0). **`mP|SM%` và `mP|SL%`: 0/20 FAIL** (không rate nào kém *ngoài CI*).
- **T4**: **0/20 PASS**. Ngưỡng `n ≥ 1,3×n(B*) = 1 410,5` chỉ **5 tag** vượt được; trong đó `kg0-g140` (Calmar 1,819 ≥ 1,713;
  n 1 411 ≥ 1 410,5) **chỉ chết ở `conc`** (7,57 % > 6,73 %); `gs2-t140` (Calmar 2,065) + `cc-t100` (2,039) chết ở `conc`;
  `rc-a-q995` chết ở Calmar (0,82). `cd-sel15`/`sc-b*` **Calmar thấp hơn `B*`** (1,20–1,33 vs 1,713) **và** `n < 1,3×`.

## 3. BẢNG 4 TẦNG @`stress` = 0,150 %/vòng — **KHÁC `base` ở đâu?**

| tag | n | equity | CAGR % | ddPhut % (năm) | UW ngày | q* % | top-1 % | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kg0-g170` = **`B*`** | 1085 | 115420 | +30.38 | **-17.95** (2025) | 147.2 | 25.0 | 20.32 | PASS | PASS | PASS | ref |
| `cd-sel15` | 744 | 78926 | +19.81 | **-15.88** (2025) | 167.7 | 27.6 | 16.13 | PASS | PASS | PASS | FAIL |
| `sc-b1` | 745 | 60314 | +12.86 | **-10.80** (2025) | 167.7 | 32.1 | 15.99 | PASS | PASS | PASS | FAIL |
| `sc-b2` | 1152 | 71246 | +17.12 | **-13.68** (2025) | 167.7 | 32.5 | 13.58 | PASS | PASS | PASS | FAIL |
| `sc-b3` | 1885 | 64179 | +14.43 | **-11.02** (2025) | 230.7 | 33.2 | 13.10 | PASS | PASS | PASS | FAIL |
| `sc-b4` | 1878 | 82310 | +20.94 | **-15.96** (2025) | 186.3 | 28.3 | 14.36 | PASS | PASS | PASS | FAIL |
| `kg0-g155` | 1245 | 111898 | +29.48 | **-17.35** (2025) | 164.7 | 19.4 | 21.26 | PASS | PASS | PASS | FAIL |
| `kg0-g140` | 1411 | 116868 | +30.74 | **-17.08** (2022) | 194.2 | 16.9 | 21.11 | PASS | PASS | FAIL | FAIL |
| `kg0-g125` | 1701 | 112726 | +29.69 | **-17.44** (2022) | 126.8 | 12.0 | 25.28 | PASS | FAIL | FAIL | FAIL |
| `gs2-t155` | 1249 | 126743 | +33.12 | **-17.36** (2025) | 164.7 | 19.6 | 26.53 | PASS | FAIL | PASS | FAIL |
| `gs2-t140` | 1416 | 134091 | +34.80 | **-17.08** (2025) | 194.2 | 16.9 | 27.07 | PASS | FAIL | PASS | FAIL |
| `gs2-t125` | 1708 | 115870 | +30.49 | **-17.23** (2022) | 126.8 | 10.5 | 29.54 | FAIL | FAIL | FAIL | FAIL |
| `cc-t100` | 2557 | 162365 | +40.65 | **-19.34** (2022) | 210.3 | 9.7 | 31.41 | PASS | FAIL | FAIL | FAIL |
| `gr-kg0-q995` | 1021 | 111383 | +29.35 | **-17.97** (2025) | 147.2 | 26.7 | 18.43 | PASS | PASS | PASS | FAIL |
| `gr-kg0-q998` | 954 | 108785 | +28.67 | **-18.00** (2025) | 147.2 | 29.6 | 17.77 | PASS | PASS | PASS | FAIL |
| `gr-kg0-q999` | 868 | 100610 | +26.46 | **-18.06** (2025) | 145.3 | 28.7 | 18.01 | PASS | PASS | PASS | FAIL |
| `gr-kg0-q998-15m` | 420 | 59992 | +12.73 | **-11.63** (2025) | 279.3 | 44.5 | 11.07 | FAIL | PASS | PASS | FAIL |
| `rc-a-q995` | 3256 | 96896 | +25.40 | **-31.14** (2022) | 480.9 | 6.1 | 31.10 | FAIL | FAIL | FAIL | FAIL |
| `rc-a-q998` | 1875 | 79939 | +20.15 | **-20.87** (2022) | 362.5 | 8.7 | 23.90 | FAIL | FAIL | FAIL | FAIL |
| `rc-a-q999` | 1297 | 62514 | +13.76 | **-20.14** (2022) | 582.0 | 8.6 | 24.15 | FAIL | FAIL | FAIL | FAIL |

**`@stress` ≠ `@base` ở đâu:** **KHÔNG một trạng thái tầng nào đổi** (T1 15/20 · T2 12/20 · T3 13/20 · T4 0/20,
y hệt). Chỉ **độ lớn** đổi nhẹ: `CAGR` −0,15…−0,44 pp; `equity` −0,5…−1,2 %; `q*` −0,3…−0,5 pp;
`ddPhut` +0,01…+0,32 pp; `UW` **không đổi** (trừ `kg0-g140`/`gs2-t140` 164,9 → **194,2** ngày và
`rc-a-*` +5,6/+6,2/+13,3 ngày). **T3 giống hệt byte** (bất biến chi phí — cảnh báo ở pre-reg §2 đã đúng).

---

## 4. ĐỐI CHIẾU KỲ VỌNG MASTER GHI TRƯỚC (`PLAN…RESET` §Phase 1 / §6 pre-reg)

| # | dự báo | thực đo @`base` | kết |
|---|---|---|---|
| 1 | `B*` qua tầng 1–2 | PASS T1, T2 (và cả T3) | **KHỚP** |
| 2 | **gate-loosened FAIL tầng 3** | `kg0-g140` ✗, `kg0-g125` ✗, `gs2-t125` ✗, `cc-t100` ✗ **NHƯNG `kg0-g155` ✗→✓ và `gs2-t155/t140` ✓** | **LỆCH MỘT PHẦN** |
| 3 | `sc-b2` qua 1–3, tầng 4 kém `B*` vì nhịp 15' (`n≈1,06× < 1,3×`) | T1–T3 PASS, T4 FAIL (`n 1 152` vs cần `1 410,5`; Calmar 1,26 vs 1,713) | **KHỚP** |
| 4 | `rc-a-*` thất bại tầng 1 (UW 568–773; `qmin` −13…−23) | FAIL T1: UW legacy **568,6 / 631,9 / 769,5** (khớp số đã công bố), `qmin` −14…−23, **năm 2022 âm** | **KHỚP** |
| 5 | hạ phí làm "nhiều lệnh" bớt xấu nhưng không cứu verdict | T1 đổi 6, T2 đổi 2, T3/T4 đổi 0; gate-loosened **vẫn FAIL** (trừ bước 1.70→1.55) | **KHỚP (có 1 ngoại lệ)** |

**Điểm LỆCH duy nhất đáng kể:** ở bước nới gate **nhẹ nhất** (1,70 → 1,55), chất lượng **vẫn non-inferior**:
`win% −0,89 pp` (trần −2,0) và `TSloss% +1,24 pp` (trần +2,5). ⇒ "nới gate = rác" đúng từ **1,40 trở xuống**,
không đúng ở **1,55**. `kg0-g155` chỉ chết ở **tầng 4** (`n 1 245 < 1 410,5`; `conc 8,67 % > 6,73 %`), **không** ở chất lượng.

---

## 5. (3) HẠ PHÍ `0,8 → 0,112` CÓ LÀM LẬT VERDICT "NHIỀU LỆNH = RÁC"?

**Có lật — nhưng chỉ ở RÀO RỦI RO và RÀO BỀN, KHÔNG lật verdict về CHẤT LƯỢNG.**

| tầng | số đối tượng đổi trạng thái legacy → base | danh sách | hướng |
|---|---|---|---|
| **T1** | **6** | `cd-sel15`, `sc-b1`, `sc-b2`, `sc-b3`, `sc-b4`, `gs2-t155` | **FAIL → PASS** |
| **T2** | **2** | `kg0-g155`, `kg0-g140` | **FAIL → PASS** |
| **T3** | **0** | — (bất biến chi phí: `profit` % là **return giá**, không chứa phí) | — |
| **T4** | **0** | — | — |

- **Cơ chế T1**: `cd-sel15`/`sc-b1..b4` ở `legacy` **chỉ vì `UW = 277,9–279,3` ngày** (> 250) là FAIL; hạ phí làm
  đường equity vượt đỉnh chạy **sớm hơn** ⇒ `UW` co còn **167,7–230,7** ngày ⇒ **PASS**. `gs2-t155` FAIL vì
  **`conc 16,46 %`** > 15 %, hạ phí ⇒ **14,46 %** ⇒ PASS.
- **Cơ chế T2**: `q*` của `kg0-g155` **14,0 → 19,8 %** và `kg0-g140` **11,8 → 17,2 %** (vượt trần 15 %) — nhưng
  **hướng đi vẫn đúng**: nới gate **vẫn làm `q*` TỤT** (25,3 → 19,8 → 17,2 → 12,3), chỉ là **mức phí cũ đã che** phần
  vượt trần.
- **KHÔNG lật verdict "nới gate = rác"**: `kg0-g125` vẫn FAIL T2 (`q* 12,3`) + T3 (`win% −2,90 pp`/`TSloss% +4,08 pp`);
  `gs2-t125` FAIL T1 (`conc 33,7 %`) + T2 + T3; `cc-t100` FAIL T2 (`top-1 31,0 %`, `q* 10,0`) + T3; `rc-a-*` FAIL T1+T2+T3.
  **`@stress` cho kết quả y hệt.** ⇒ Hạ phí **mua lại được rào**, **không mua được chất lượng**.

## 6. (4) MỤC NÀO BỎ + LÝ DO (theo số của lượt chấm này)

**BỎ khỏi danh sách ứng viên (không go-live được):**
- `rc-a-q995/q998/q999`: phạm **nhiều rào nhất** — T1 (UW 356–569, **năm 2022 âm**, `qmin` −11…−19), T2 (`q* 6–9`, top-1 23–30),
  T3 (win −7,5…−8,8 pp). Không có mức phí nào cứu.
- `gs2-t125`, `cc-t100`: **`conc` 33,7 % / top-1 31,0 %** và T3 FAIL ⇒ vi phạm đúng cái trần (tập trung 1 coin)
  mà `RISK_APPETITE` §7.1 gọi là **kênh mất thật duy nhất**.
- `kg0-g125`: `q*` 12,3 (< 15) + T3 FAIL.
- `gr-kg0-q998-15m`: T1 FAIL (`UW 279,3 > 250`) — **đồng thời** nhịp 15' không tái lập được ở live.

**BỎ khỏi LUẬT (rào "chết", binding 0 lần trong cohort 20 đối tượng — đề nghị MASTER gỡ/siết lại, KHÔNG tự sửa):**
- **`gross ≤ 70 %`**: `gross MAX` = **34,4–59,7 %** trên cả 20 (`B*` 51,0 %) ⇒ **0/20 bind**. Giữ làm *báo cáo*, bỏ làm *rào*.
- **`mP|SM%` / `mP|SL%` (tầng 3)**: **0/20 FAIL** — CI (đã nở `inflate(19)=2,43`) rộng hơn nhiều so với chênh thật
  (0,0–0,8 pp) ⇒ **không phân biệt được gì**. Hoặc bỏ, hoặc đổi sang **đơn vị USDT/leg** (khác `profit` %).
- **"bỏ top-3 episode > 0" (tầng 2)**: **20/20 PASS** ⇒ cũng chưa bind; lý do: PnL không tập trung vào 3 episode.
  Giữ để kiểm bền nhưng **không phải cơ chế chọn**.

**GIỮ / đáng xét tiếp (qua T1–T3 @base):** `B*`; `kg0-g155` (chỉ kém T4 ở `n`/`conc`); `gr-kg0-q995/q998/q999`
(chỉ kém T4 ở `n` giảm); `cd-sel15`, `sc-b1..b4` (qua T1–T3 @base, nhưng `Calmar < B*`).
**Cảnh báo về T4:** ngưỡng **`n ≥ 1,3×B*` (= 1 410,5)** kết hợp **`conc ≤ B*` (= 6,73 %)** khiến T4 **gần như không thể qua**
(kể cả `gs2-t140`/`cc-t100` có **Calmar cao hơn `B*`** vẫn chết ở `conc`). Đây là **quan sát để MASTER quyết**, không phải đề xuất tự sửa luật.

---

## 7. HẠN CHẾ (khai rõ)

1. **Hậu kiểm TUYẾN TÍNH, bỏ compounding**: `equity/CAGR/maxDD/q*` ở mức phí mới là **ước lượng**, không phải chạy lại sim
   (sizing/throttle/DCA-grid/funding không mô hình lại). D2 **không chạy sim** theo ràng buộc.
2. **Tầng 3 bất biến chi phí** vì `profit` % là **return giá** (`profit = (exit−entry)/entry`, đã kiểm từng leg).
   Muốn tầng 3 nhạy phí phải đổi sang **PnL ròng USDT**.
3. **MTM phút** chỉ có **giá đóng nến 1 phút** (không tick/không `low`): tái lập `intraday_dd.py`, đã kiểm `V2` (mốc 0)
   và **cổng KEEPLEG0 khớp −19,96 %/147,2 ngày**. Đây là **cận dưới** (chưa mô hình margin-call/thanh lý), **1 quan sát lịch sử, không CI**.
4. **Thiếu ticker**: **1 leg-ngày** (`rc-a-q995`, đơn lẻ) ⇒ báo là "thiếu 1", **không bịa giá**; không tag nào phải ghi
   "KHÔNG CHẤM ĐƯỢC".
5. `gs2-*` là nền **T170** (khác nền `kg0-g*` = KEEPLEG0) ⇒ so `gs2-*` vs `B*` là **so chéo nền**, đã ghi rõ.
6. Mọi số là **mô tả quá khứ DEV**, không phải cam kết forward; **chưa chạm HOLDOUT 2026**.

---

## 8. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/reset_rule_score.py --workers 4 --chunk 20 \
  --json docs/result/reset_rule_p1.json --report /home/ubuntu/rr_p1_run.txt
# ~13-18 phut (doc ticker 1m 1.631 ngay, 1.258 ngay co vi the mo); cache MTM: /tmp/rr_p1_mtm.json
# TU KIEM (cổng DỪNG) in o BUOC B + dòng "TU KIEM MTM KEEPLEG0"
# input: kaggle_sim/out/<tag>/storage/printDone.csv + logs/sim.out + java/devrun/FG_KEEPLEG0 + kaggle_data_hpo/ticker_*.bin.gz
```
