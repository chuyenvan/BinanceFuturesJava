# RESULT_SHORT_STATE — GATE STATE THEO TỪNG COIN cho SHORT (0-sim) ⇒ **NULL**

Ngày: **2026-10-01**, branch `module`. Pre-reg: `docs/prereg/PREREG_SHORT_STATE.md` (**`b76b6299`**, TRƯỚC đo).
Code: `research/analysis/short_state_0sim.py`. Số: `docs/result/RESULT_SHORT_STATE.json`.
Nền: `RESULT_PUMPDUMP_DETECT` (NULL) · `RESULT_SHORT_REGIME` (`47a4b63d`, NULL market-regime).

**Tuân thủ:** 0-sim (KHÔNG chạy sim 1m) · không `.java`/ONNX/242/LIVE/2026 · không push dữ liệu ·
DEV ≤ 2025-12-31 · chỉ `git add` file của mình.

---

## 0. KẾT LUẬN NGẮN

> **NULL.** *(AMENDMENT A2 — ngưỡng có cơ sở paper+data — xem §5: B đổi dấu điểm **net24 +0,055 %**,
tail 27,0 %→20,9 %, nhưng **CI vẫn chứa 0** ⇒ vẫn NULL.)* Tập **(B) "xả dần"** *tốt hơn* baseline: drift SHORT **+0,152 %/24h** (baseline universe
> +0,012 %; S1-d0 −0,033 %) và **cắt được một phần đuôi** (SL-rate `maxFav≥+10 %`: **27,0 %→22,1 %**,
> big-alt **20,6 %**) — **NHƯNG vẫn < cost 0,21 %/24h** ⇒ **net24 = −0,058 %** (CI95 `[−0,137;+0,428]` **chứa 0**),
> không ngoài CI ⇒ **FAIL luật GO**. Tập **(A) đúng là phải AVOID**: drift **+0,234 %/24h** (short lỗ) và
> **đuôi nổ to** (SL-rate **41,4 %**). ⇒ **NULL — chốt đóng hướng short.**

## 1. PHƯƠNG PHÁP (0-sim, universe ticker đầy đủ)

- Nguồn: state ex-ante từ `CLOSES_1H.bin`; forward = nhãn `.pb` (univers = **ticker đầy đủ**, 37 489 126 dòng
  sau join, `nBars_72h≥288`); **tier** = hạng `notional` proxy (`Σ V·C` phút, lấy mẫu **14 ngày**, Aerospike).
- Tham số **CỐ ĐỊNH**: `PUMP_X=+15 %/24h`; **(B)** = `pump_age>7d & vol_decay<1,0 & ret30<0 & dd30<−0,15`;
  **(A)** = `pump_age≤2d | vol_decay>1,5`. Cost **0,21 %/24h**.
- ⚠️ tier xấp xỉ (mẫu 14 ngày, 9,0 % NaN) — ghi rõ.

## 2. KẾT QUẢ (drift SHORT forward, %, **net24 = −mean(ret24) − 0,21 %**, CI95 block-72h)

| state | n | frac | mean ret24 | **short net24** | CI95 | ngoài 0? | hit24 | **SL-rate(maxFav≥10 %)** | năm dương |
|---|---|---|---|---|---|---|---|---|---|
| *(ALL universe)* | 37 489 126 | 1,000 | +0,012 | **−0,222** | [−0,216;+0,202] | KHÔNG | 51,3 % | 27,0 % | 2/4 |
| **B xả dần** | 11 659 434 | 0,311 | **−0,152** | **−0,058** | [−0,137;+0,428] | **KHÔNG** | 50,7 % | **22,1 %** | **3/4** |
| B xả dần · big-alt | 2 853 558 | 0,076 | −0,164 | −0,046 | [−0,147;+0,469] | KHÔNG | 51,2 % | **20,6 %** | 3/4 |
| B xả dần · rac | 3 371 961 | 0,090 | −0,127 | −0,083 | [−0,167;+0,416] | KHÔNG | 50,3 % | 21,6 % | 3/4 |
| **A gương thanh khoản** | 5 160 242 | 0,138 | **+0,234** | **−0,444** | [−0,565;+0,107] | KHÔNG | 54,4 % | **41,4 %** | 2/4 |
| big-alt (ALL) | 10 339 254 | 0,276 | −0,050 | −0,160 | [−0,162;+0,250] | KHÔNG | 52,1 % | 24,9 % | 2/4 |
| rac (ALL) | 9 563 304 | 0,255 | +0,004 | −0,214 | [−0,230;+0,214] | KHÔNG | 50,7 % | 25,4 % | 2/4 |
| vol_decay<1 | 23 066 374 | 0,615 | −0,086 | −0,124 | [−0,146;+0,310] | KHÔNG | 51,4 % | 24,3 % | 3/4 |
| vol_decay>1,5 | 1 636 258 | 0,044 | **+0,404** | −0,614 | [−1,002;+0,201] | KHÔNG | 52,7 % | **39,1 %** | 2/4 |
| ret30<0 | 23 024 731 | 0,614 | −0,066 | −0,144 | [−0,172;+0,306] | KHÔNG | 50,9 % | 24,2 % | 2/4 |

Theo năm (short24 %): **B** = 2022 **+0,138** · 2023 **−0,218** · 2024 **+0,301** · 2025 **+0,199** (2023 âm).

## 3. TRẢ LỜI (a–d)

- **(a) Tập (B) có drift âm > cost 0,21 %/24h?** **KHÔNG.** Đúng chiều (âm) nhưng biên **−0,152 %/24h**
  < cost 0,21 % ⇒ net24 **−0,058 %** (dù tốt hơn hẳn baseline +0,012 %). **Chưa đủ cửa.**
- **(b) Tập (A) có phải avoid?** **CÓ, rõ.** ret24 **+0,234 %** (short lỗ), tail SL-rate **41,4 %** (gấp 1,5×)
  ⇒ **(A) là "gương thanh khoản" xấu cho short** — đúng trực giác owner.
- **(c) Có tách được đuôi +10 %?** **TÁCH ĐƯỢC MỘT PHẦN:** SL-rate 27,0 %→**22,1 %** (B), **20,6 %** (B·big-alt),
  ngược lại **(A) 41,4 %**, vol_decay>1,5 **39,1 %**. Tức state **phân biệt được đuôi**, nhưng mức cắt
  (~18 % tương đối) **không đủ** đưa net qua cost.
- **(d) theo năm + CI:** B dương **3/4 năm** (2023 âm), **CI chứa 0** (không ngoài). Tất cả state đều
  **CI chứa 0**, không state nào net>0 ngoài CI.
- **Overfit?** Nhiều biến thể nhưng **không biến thể nào net>0** ⇒ **không phải overfit**, mà là **thiếu biên**.

## 5. AMENDMENT A2 — STATE theo **NGƯỠNG CÓ CƠ SỞ** (paper + data thật)

Cơ sở: `docs/research/SHORT_STATE_DEFS.md` (12 paper + đo ZigZag thật). Ngưỡng **lấy từ số đo**:
up-leg median **18 ngày** / +54 %; bleed median **24 ngày**. Thay định nghĩa A/B thô bằng:
- **A `A_ev`** = `pump_age_d ≤ 18` **hoặc** `ret7 ≥ +50 %` (median của 1 leg) — *cơ sở P7/P8 MAX dương, P9 momentum ≤2–4 tuần, P2/P3 coin nhỏ bơm/xả*.
- **B `B_ev`** = `pump_age_d > 18` **và** `vol_decay < 1` **và** `ret30 < 0` **và** `dd30 < −20 %` — *cơ sở P9 reversal >1 tháng, P6 illiquidity, P11 regime, data bleed dài 24+ ngày*.

| state (A2) | n | mean ret24 | **short net24** | CI95 | ngoài 0? | hit24 | **SL-rate** | năm dương |
|---|---|---|---|---|---|---|---|---|
| ALL | 37 489 126 | +0,012 | −0,222 | [−0,216;+0,202] | KHÔNG | 51,3 % | 27,0 % | 2/4 |
| **A `ret7≥50 %`** | 496 432 | **+0,180** | −0,390 | [−0,781;+0,416] | KHÔNG | 59,6 % | **55,3 %** | 3/4 |
| A `pump_age≤18` | 17 912 735 | +0,083 | −0,293 | [−0,328;+0,172] | KHÔNG | 52,3 % | 34,4 % | 2/4 |
| **B xả dần `B_ev`** | 6 275 538 | **−0,265** | **+0,055** | [−0,075;+0,636] | **KHÔNG** | 51,0 % | **20,9 %** | **3/4** |
| B_ev · big-alt | 1 474 730 | −0,276 | **+0,066** | [−0,072;+0,633] | KHÔNG | 51,4 % | **19,8 %** | 3/4 |
| B_ev · rac | 1 917 865 | −0,258 | **+0,048** | [−0,105;+0,653] | KHÔNG | 50,3 % | 20,8 % | 3/4 |
| B_ev · dd<−10 % (rộng) | 9 004 246 | −0,227 | **+0,017** | [−0,041;+0,514] | KHÔNG | 51,1 % | **18,6 %** | 3/4 |

Theo năm (short24 %): **B_ev** = 2022 **+0,391** · 2023 **−0,304** · 2024 **+0,557** · 2025 **+0,276** (2023 âm).

**Đọc A2:** ngưỡng có cơ sở **đổi dấu điểm** của B: net24 **`−0,058 % → +0,055 %`** và cắt đuôi mạnh hơn
(SL-rate 27,0 %→**20,9 %**, big-alt **19,8 %**); A vẫn **xấu rõ** (đặc biệt `ret7≥+50 %`: SL-rate **55,3 %** ⇒ tuyệt đối avoid).
**NHƯNG vẫn FAIL GO** vì **CI chứa 0** (`B_ev` CI `[−0,075;+0,636]`), chưa ngoài CI. ⚠️ **Nguy cơ overfit:
ngưỡng 18d/50 %/−20 % suy từ **chính** phân bố full-DEV, và **4 biến thể B đều net>0** ⇒ theo pre-reg ⇒ **nghi overfit**, KHÔNG được coi là GO.

## 4. QUYẾT ĐỊNH

**NULL — chốt đóng hướng short.** State gate định hướng đúng (B tốt hơn, A xấu) và **cắt được ~18–31 % đuôi**
(đến SL-rate 20,9 %/18,6 %), nhưng **biên vẫn không vượt cost một cách có ý nghĩa** (CI chứa 0; kể cả A2
net24 +0,055 % **chưa ngoài CI**) ⇒ không có cửa. Cơ chế gốc không đổi: **đuôi tăng
đến từ idiosyncratic coin, và biên ròng sau phí+funding ≤ 0** ở mọi state ĐÃ THỬ (carry, down-signal,
gate market, regime, state-coin, path-exit). Mở lại chỉ khi có **DATA MỚI** (liquidation / L2 / fill thật).
