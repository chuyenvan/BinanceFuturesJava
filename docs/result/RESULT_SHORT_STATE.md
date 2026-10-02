# RESULT_SHORT_STATE — GATE STATE THEO TỪNG COIN cho SHORT (0-sim) ⇒ **NULL**

Ngày: **2026-10-01**, branch `module`. Pre-reg: `docs/prereg/PREREG_SHORT_STATE.md` (**`b76b6299`**, TRƯỚC đo).
Code: `research/analysis/short_state_0sim.py`. Số: `docs/result/RESULT_SHORT_STATE.json`.
Nền: `RESULT_PUMPDUMP_DETECT` (NULL) · `RESULT_SHORT_REGIME` (`47a4b63d`, NULL market-regime).

**Tuân thủ:** 0-sim (KHÔNG chạy sim 1m) · không `.java`/ONNX/242/LIVE/2026 · không push dữ liệu ·
DEV ≤ 2025-12-31 · chỉ `git add` file của mình.

---

## 0. KẾT LUẬN NGẮN

> **NULL.** Tập **(B) "xả dần"** đúng là *tốt hơn* baseline: drift SHORT **+0,152 %/24h** (baseline universe
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

## 4. QUYẾT ĐỊNH

**NULL — chốt đóng hướng short.** State gate định hướng đúng (B tốt hơn, A xấu) và **cắt được ~18 % đuôi**,
nhưng **biên gross (−0,15 %/24h) vẫn < cost (0,21 %)** ⇒ không có cửa. Cơ chế gốc không đổi: **đuôi tăng
đến từ idiosyncratic coin, và biên ròng sau phí+funding ≤ 0** ở mọi state ĐÃ THỬ (carry, down-signal,
gate market, regime, state-coin, path-exit). Mở lại chỉ khi có **DATA MỚI** (liquidation / L2 / fill thật).
