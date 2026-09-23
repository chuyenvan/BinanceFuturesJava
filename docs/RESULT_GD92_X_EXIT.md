# RESULT — GD92 × {HINGE V3 weak 0.17, LADDER L1} tren nen T170

Pre-reg: `docs/PREREG_GD92_X_EXIT.md` (commit **`0d1d690`**, viet TRUOC khi chay).
Code rolling: cherry-pick **`1db0613`** (từ branch `gd92-recheck`) vào `module` HEAD **`fc7065d`**
bằng `git cherry-pick -n` — **KHÔNG commit, KHÔNG merge**; sau khi build đã `git checkout -- src/`.
Jar mới sha256 **`e1fed2cbdc07355d33cf601e21df7a3f842a02d6d68d1d0da8edcec74b9976b9`**
(`mvn -o package`, tests BẬT, 25 lớp test PASS, BUILD SUCCESS 25.9s).
Tất cả sim chạy trên **Kaggle CPU kernel** (`docs/KAGGLE_SIM.md`); **KHÔNG chạy Java/sim trên Oracle**.
Cửa sổ `TIME_RUN=20210701` .. `SIM_END_DATE=20251231` (DEV, 1,644 ngày), `TICKER_SOURCE=file`,
mapper **863** (≥ 800 guard) ở **MỌI** chân. Chi phí Kaggle: **0** (CPU kernel không tính quota).

---

## 0. Cổng PARITY — CẢ HAI ĐỀU PASS (byte-identical)

| chân | profile | md5 `printDone.csv` | tham chiếu | n | equity |
|---|---|---|---|---|---|
| `gx-par1` | `x1_gs_t170` (KHÔNG key rolling) | **`efb793e2468ca3a7318da0f0ad23d4fc`** | `efb793e2…` | 1089 | 111070 |
| `gx-par2` | `x1_c3_full` (KHÔNG key rolling) | **`dc16e4da6ff6cb7b8d41c592bc3d9c45`** | `dc16e4da…` | 2559 | 121770 |

⇒ Ba điểm nối dây phục hồi (`GateRollingThreshold.java` md5 `e1e99295c76bfd066493ca25ebeb1243`,
149 dòng) **KHÔNG dịch một bit nào** khi `SIM_GATE_ROLLING_PCT` không khai báo. Được phép đọc kết quả.

**`[GATE-ROLL]` BẬT thật** ở CẢ A/B/C (log giống nhau tuyệt đối):
```
*** [GATE-ROLL] BAT: pct=0.92 window=90d | 39510 moc gio | moc dau 1624989600000
    | nguong min=0.00456 max=0.01265 | tinh ~25.7s ***
```

Mốc đầu `1624989600000` = **2021-06-30** ⇒ cua so 2021-07..2025-12 **có ngưỡng trượt thật từ ngày đầu**;
**0 cảnh báo** `truy van TRUOC moc gio dau tien` ⇒ **`nBeforeFirst = 0`** (khớp `RESULT_GD92_RECHECK`).
Ngưỡng trượt chạy trong dải **0.456% – 1.265%** quanh hằng số cũ 0.800%.
`gx-c` xác nhận thêm `[CFG] TS_LADDER ON lo=[0.0,0.1,0.25,0.5,1.0] gaps=[0.04,0.08,0.15,0.25,0.35]`.

Mapper **863** ở mọi chân. **Thời gian/chi phí:** 6 kernel (`gx-par1/par2/a/b/c/d`), mỗi kernel
JVM **1 139–1 322s** (19–22 phút), push→COMPLETE ~25 phút, 5 kernel chạy song song một lượt;
**chi phí 0** (Kaggle CPU kernel không tính quota). Không slot nào bị chiếm quá hạn.

---

## 1. Bảng chính — 5 rate chất lượng (toàn bộ leg)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---|---|---|---|---|---|
| **T170** (`gx-par1`, parity) | 1089 | 88.25 | 9.73 | 7.642 | −16.992 | 5.244 |
| **(A) GD92-only** `gx-a` | 1108 | 87.73 | 11.37 | 7.084 | −16.249 | 4.431 |
| **(B) GD92 + HINGE V3** `gx-b` | 1115 | 87.62 | 11.48 | 7.150 | −16.290 | 4.459 |
| **(C) GD92 + LADDER L1** `gx-c` | 1105 | 87.78 | 11.31 | 6.955 | −16.344 | 4.319 |
| **(D) GD92 + cap 10/30** `gx-d` *(tuỳ chọn)* | 1104 | 87.95 | 11.14 | 7.061 | −16.318 | 4.457 |
| *(tham chiếu)* HINGE V3 trần | 1095 | 88.22 | 9.77 | 7.723 | −16.998 | 5.308 |
| *(tham chiếu)* LADDER L1 trần | 1086 | 88.21 | 9.58 | 7.621 | −17.149 | 5.249 |

## 2. CI hiệu (chan − T170), block-72h / 2000 rep / seed 20260905 / anchor 2021-07-01

Báo **CẢ HAI** độ rộng: legacy **×1.21** (brief) và chuẩn hoá **`inflate(k=3)=1.482304`**.
Một rate chỉ tính là **ngoài CI** khi ngoài **CẢ HAI** (tiền lệ `traillad_score.py`).

| chân | rate | hiệu | CI @1.21 | CI @1.4823 | ngoài cả hai | hướng |
|---|---|---|---|---|---|---|
| **A** | win% | −0.520 | [−1.917, +0.765] | [−2.219, +1.067] | – | – |
| **A** | TSloss% | **+1.638** | [+0.022, +3.171] | [−0.333, +3.526] | – (chỉ ngoài @1.21) | **XẤU** |
| **A** | mP\|SM | −0.557 | [−1.321, +0.132] | [−1.484, +0.295] | – | – |
| **A** | mP\|SL | +0.743 | [−1.491, +3.239] | [−2.023, +3.772] | – | – |
| **A** | meanP | −0.813 | [−1.945, +0.233] | [−2.190, +0.478] | – | – |
| **B** | win% | −0.623 | [−2.068, +0.679] | [−2.377, +0.988] | – | – |
| **B** | TSloss% | **+1.746** | [+0.097, +3.279] | [−0.261, +3.637] | – (chỉ ngoài @1.21) | **XẤU** |
| **B** | mP\|SM | −0.492 | [−1.279, +0.237] | [−1.450, +0.408] | – | – |
| **B** | mP\|SL | +0.702 | [−1.499, +3.134] | [−2.020, +3.655] | – | – |
| **B** | meanP | −0.785 | [−1.917, +0.270] | [−2.163, +0.516] | – | – |
| **C** | win% | −0.463 | [−1.966, +0.975] | [−2.297, +1.306] | – | – |
| **C** | TSloss% | +1.579 | [−0.278, +3.345] | [−0.685, +3.752] | – | – |
| **C** | mP\|SM | −0.687 | [−1.583, +0.185] | [−1.782, +0.384] | – | – |
| **C** | mP\|SL | +0.648 | [−1.550, +3.136] | [−2.077, +3.663] | – | – |
| **C** | meanP | −0.925 | [−2.200, +0.259] | [−2.477, +0.536] | – | – |

**A/B/C: 0 TỐT / 0 XẤU ngoài CI (cả hai độ rộng).** Nếu chỉ dùng thinh thích legacy ×1.21 thì
A và B có **1 rate XẤU** (TSloss%); nhưng luật đã khoá là "ngoài ở CẢ HAI" ⇒ 0/0.
Điểm ước lượng của **mọi** rate (trừ mP|SL) đều **ngược chiều TỐT** — GD92 kéo chất lượng lệnh xuống,
biên độ thì chưa vượt nhiễu.

**Đối chứng máy chấm (kiểm chứng CI tool):** `T170` vs `gx-par1` và `T170T` vs `gx-par1` (hai chân
byte-identical) cho **hiệu đúng bằng 0.000 ở cả 5 rate, CI [0.000, 0.000]**.

### 2b. Hai câu hỏi phụ (đúng luật kết luận của pre-reg §5)

| so sánh | kết quả | ý nghĩa |
|---|---|---|
| **(B) vs HINGE V3 trần** | 0 TỐT / 0 XẤU ngoài cả hai (TSloss% **+1.708** ngoài ở @1.21) | GD92 **KHÔNG** làm HINGE V3 sáng hơn — kéo xuống |
| **(C) vs LADDER L1 trần** | 0 TỐT / 0 XẤU ngoài cả hai (TSloss% **+1.736** ngoài ở @1.21) | GD92 **KHÔNG** làm LADDER L1 sáng hơn — kéo xuống |
| **(B) vs (A)** (HINGE thêm gì trên nền GD92) | 0/5 ngoài CI | HINGE V3 **không** thêm gì đo được |
| **(C) vs (A)** (LADDER thêm gì trên nền GD92) | 0/5 ngoài CI | LADDER L1 **không** thêm gì đo được |

---

## 3. Rào cứng `docs/RISK_APPETITE.md` — PASS cả **theo năm** LẪN **toàn kỳ**

| tag | equity | CAGR% | maxDD toàn kỳ | UW toàn kỳ | quy min% | conc 1 coin% | n | hold med (h) | turn (leg/ngày) | SumPnL |
|---|---|---|---|---|---|---|---|---|---|---|
| T170 (`gx-par1`) | 111 070 | 29.27 | −11.84 | 92 | −0.92 | 9.77 | 1089 | 4.8 | 0.662 | 76 070 |
| **(A)** `gx-a` | 99 179 | 26.06 | −12.85 | **164** | −1.43 | 10.34 | 1108 | 6.3 | 0.674 | 64 180 |
| **(B)** `gx-b` | 101 460 | 26.69 | −12.81 | **164** | −2.51 | 9.95 | 1115 | 5.6 | 0.678 | 66 461 |
| **(C)** `gx-c` | 97 909 | 25.69 | −13.10 | **164** | −2.14 | 11.37 | 1105 | 7.5 | 0.672 | 62 909 |
| **(D)** `gx-d` *(tuỳ chọn)* | 100 063 | 26.30 | −13.12 | **164** | −2.26 | 10.65 | 1104 | 7.7 | 0.672 | 65 064 |
| *(tc)* HINGE V3 trần | 114 287 | 30.09 | −11.67 | 119 | −1.97 | 9.77 | 1095 | 4.2 | 0.666 | 79 287 |
| *(tc)* LADDER L1 trần | 114 756 | 30.21 | −12.03 | 119 | −1.37 | 9.79 | 1086 | 5.8 | 0.661 | 79 757 |

Theo năm (maxDD% / UW / ret%) — **tất cả P**:

| tag | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| T170 | −2.46/37/+12.21 | −11.84/72/+19.58 | −2.73/63/+34.96 | −6.60/92/+32.14 | −4.23/52/+32.71 |
| **A** | −3.71/44/+6.26 | −12.85/72/+17.77 | −2.39/45/+44.06 | −6.60/88/+33.81 | −4.89/**164**/+17.53 |
| **B** | −3.71/36/+6.81 | −12.81/44/+18.51 | −2.45/45/+44.46 | −6.54/119/+35.48 | −4.88/**164**/+17.08 |
| **C** | −3.62/44/+5.39 | −13.10/73/+18.53 | −2.35/58/+44.22 | −6.72/88/+30.61 | −6.02/**164**/+18.95 |

Không năm nào âm; maxDD mọi năm ≤ 13.10% (trần 30%); tập trung ≤ 11.37% (trần 15%).

> **Ghi chú quan trọng so với bài học GD92 cũ:** GD92 chạy một mình trên nền **x1_c3_full** đã
> **FAIL toàn kỳ (maxDD −16.55%, UW 278)**. Trên nền **T170** lần này, rào cứng **PASS cả hai tầng**
> (UW toàn kỳ 164 ≤ 200). Nghĩa là **hiệu ứng UW 278 là của nền T100 + GD92**, KHÔNG tái hiện trên
> nền T170 — nhưng điều đó **không** cứu được chân nào, vì tiêu chí quyết định là **rate chất lượng
> (0/5 ngoài CI)**.

---

## 4. ⭐ BẢNG PnL CHI TIẾT THEO NĂM (bắt buộc)

Cột `PnL(USDT)` = Σ cột `pnl` của `printDone.csv` theo năm **vào lệnh** (`start`);
`ret%`/`maxDD%`/`UW`/`qmin%`/`equity` = từ **đường equity thật** trong `sim.out`.

### T170 (mốc, `gx-par1` — md5 `efb793e2`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 92.62 | 7.38 | 4.368 | 4 273 | +12.21 | −2.46 | 37 | +4.44 | 39 272 |
| 2022 | 198 | 83.84 | 11.11 | 3.861 | 7 688 | +19.58 | −11.84 | 72 | +2.90 | 46 960 |
| 2023 | 126 | 88.10 | 15.87 | 8.074 | 16 331 | +34.96 | −2.73 | 63 | −0.37 | 63 378 |
| 2024 | 281 | 90.04 | 10.68 | 4.769 | 20 403 | +32.14 | −6.60 | 92 | −0.92 | 83 695 |
| 2025 | 335 | 87.46 | 6.87 | 5.784 | 27 375 | +32.71 | −4.23 | 52 | +1.27 | **111 070** |

### (A) GD92-only `gx-a`

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 147 | 88.44 | 11.56 | 3.226 | 2 193 | +6.26 | −3.71 | 44 | +0.20 | 37 192 |
| 2022 | 184 | 83.70 | 11.41 | 3.331 | 6 609 | +17.77 | −12.85 | 72 | +2.72 | 43 802 |
| 2023 | 206 | 88.35 | 15.05 | 6.473 | 19 213 | +44.06 | −2.39 | 45 | +1.62 | 63 101 |
| 2024 | 307 | 89.58 | 11.07 | 4.742 | 21 370 | +33.81 | −6.60 | 88 | −1.43 | 84 384 |
| 2025 | 264 | 87.50 | 8.71 | 3.912 | 14 795 | **+17.53** | −4.89 | **164** | +1.19 | **99 179** |

### (B) GD92 + HINGE V3 `gx-b`

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 147 | 88.44 | 11.56 | 3.279 | 2 386 | +6.81 | −3.71 | 36 | +0.36 | 37 385 |
| 2022 | 188 | 82.98 | 12.23 | 3.413 | 6 920 | +18.51 | −12.81 | 44 | +2.75 | 44 305 |
| 2023 | 206 | 88.35 | 15.05 | 6.506 | 19 609 | +44.46 | −2.45 | 45 | +1.97 | 64 001 |
| 2024 | 310 | 89.68 | 10.97 | 4.772 | 22 742 | +35.48 | −6.54 | 119 | −2.51 | 86 655 |
| 2025 | 264 | 87.50 | 8.71 | 3.895 | 14 805 | **+17.08** | −4.88 | **164** | +0.98 | **101 460** |

### (C) GD92 + LADDER L1 `gx-c`

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 147 | 88.44 | 11.56 | 3.098 | 1 887 | +5.39 | −3.62 | 44 | +0.20 | 36 887 |
| 2022 | 190 | 85.26 | 10.00 | 3.410 | 6 835 | +18.53 | −13.10 | 73 | +2.95 | 43 722 |
| 2023 | 204 | 88.24 | 15.20 | 6.436 | 19 249 | +44.22 | −2.35 | 58 | +2.82 | 63 057 |
| 2024 | 306 | 89.54 | 11.11 | 4.435 | 19 342 | +30.61 | −6.72 | 88 | −2.14 | 82 312 |
| 2025 | 258 | 86.82 | 9.30 | 3.873 | 15 597 | **+18.95** | −6.02 | **164** | +0.88 | **97 909** |

### Mốc tham chiếu HINGE V3 trần (devrun Oracle, đọc lại — không chạy lại)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 92.62 | 7.38 | 4.221 | 4 114 | +11.75 | −2.47 | 37 | +4.36 | 39 114 |
| 2022 | 201 | 83.58 | 11.44 | 4.049 | 8 261 | +21.12 | −11.67 | 58 | +3.62 | 47 375 |
| 2023 | 126 | 88.10 | 15.87 | 8.160 | 16 740 | +35.52 | −2.71 | 63 | −0.37 | 64 203 |
| 2024 | 284 | 90.14 | 10.56 | 4.926 | 22 189 | +34.50 | −6.54 | 119 | −1.97 | 86 305 |
| 2025 | 335 | 87.46 | 6.87 | 5.797 | 27 982 | +32.42 | −4.12 | 52 | +1.06 | **114 287** |

### Mốc tham chiếu LADDER L1 trần (`tl-l1`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 92.62 | 7.38 | 4.398 | 4 127 | +11.79 | −2.45 | 37 | +4.49 | 39 126 |
| 2022 | 203 | 85.71 | 9.36 | 4.163 | 8 845 | +22.61 | −12.03 | 73 | +3.63 | 47 971 |
| 2023 | 126 | 88.10 | 15.87 | 8.480 | 18 219 | +38.17 | −2.75 | 62 | −0.01 | 66 281 |
| 2024 | 280 | 90.00 | 10.71 | 4.607 | 20 240 | +30.48 | −6.72 | 119 | −1.37 | 86 429 |
| 2025 | 328 | 86.28 | 7.32 | 5.614 | 28 327 | +32.77 | −4.33 | 52 | +0.94 | **114 756** |

**Đọc bảng:** A/B/C đều **mất khoảng nửa lợi nhuận 2025** (ret +17.1..+19.0% so T170 +32.71%, HINGE V3
trần +32.42%, LADDER L1 trần +32.77%) và **UW 2025 nhảy lên 164** (T170 52; hai biến thể trần 52).
Toàn kỳ: equity A/B/C 97.9k–101.5k, **dưới T170 8.7–11.8%**, trong khi hai biến thể trần **trên** T170
(114.3k / 114.8k). PnL/equity **chỉ để báo cáo, không dùng để chọn.**

---

## 5. Bắt sóng lớn (capture ratio, từ `trailTrace.csv`)

Nhóm = leg có `peak ≥ +20% / 50% / 100%`. Mốc T170 = chân `tl-part` (`SIM_TRAIL_TRACE=1`,
`printDone` **byte-identical** `efb793e2` — đã chứng minh trace là đo-lường-only).
HINGE V3 trần **KHÔNG có** `trailTrace.csv` ⇒ không đo capture cho nó được (không tự bịa).

**peak ≥ +20%**

| tag | n | %trailing | med_gap_pp | med_capture | mean_capture | SumPnL |
|---|---|---|---|---|---|---|
| T170 (tl-part) | 123 | 98.4 | 8.14 | 0.662 | 0.596 | 51 997 |
| **A** | 111 | 99.1 | 8.05 | 0.676 | 0.619 | 38 104 |
| **B** | 83 | 98.8 | 8.08 | 0.678 | 0.601 | 27 634 |
| **C** | 130 | 99.2 | 10.94 | 0.623 | 0.570 | 46 150 |
| LADDER L1 trần | 146 | 98.6 | 14.89 | 0.624 | 0.544 | 64 331 |

**peak ≥ +50%**

| tag | n | %trailing | med_gap_pp | med_capture | mean_capture | SumPnL |
|---|---|---|---|---|---|---|
| T170 (tl-part) | 29 | 93.1 | 64.70 | 0.406 | 0.420 | 23 049 |
| **A** | 16 | 93.8 | 61.65 | 0.313 | 0.389 | 10 876 |
| **B** | 14 | 92.9 | 80.73 | 0.173 | 0.322 | 9 262 |
| **C** | 22 | 95.5 | 42.49 | 0.574 | 0.417 | 18 161 |
| LADDER L1 trần | 38 | 94.7 | 48.46 | 0.574 | 0.435 | 33 532 |

**peak ≥ +100%**

| tag | n | %trailing | med_gap_pp | med_capture | mean_capture | SumPnL |
|---|---|---|---|---|---|---|
| T170 (tl-part) | 21 | 90.5 | 112.34 | 0.262 | 0.308 | 15 906 |
| **A** | 11 | 90.9 | 138.00 | 0.153 | 0.223 | 6 510 |
| **B** | 11 | 90.9 | 138.02 | 0.153 | 0.222 | 6 560 |
| **C** | 12 | 91.7 | 113.14 | 0.206 | 0.262 | 8 625 |
| LADDER L1 trần | 23 | 91.3 | 103.40 | 0.326 | 0.335 | 19 155 |

**Đọc bảng:** GD92 làm **số leg đạt sóng lớn GIẢM** ở mọi ngưỡng (≥20%: 123→111/83/130;
≥50%: 29→16/14/22; ≥100%: 21→11/11/12) — gate trượt **chặn mất chính các leg thắng lớn**.
Ở ngưỡng ≥100%, capture của A/B (0.153) **tệ hơn** cả T170 (0.262) và LADDER L1 trần (0.326).
C trội hơn A/B về capture ≥50%/100% (đúng như cơ chế ladder) nhưng **vẫn dưới** chân trần tương ứng
(0.574 vs 0.574 ngang ở ≥50%; 0.206 vs 0.326 ở ≥100%) và **thấp hơn hẳn về n/SumPnL**.
*(Nhóm được chọn theo peak đã xảy ra ⇒ có post-selection; chỉ dùng chẩn đoán, không phải tiêu chí.)*

---

## 6. Chân (D) tuỳ chọn — GD92 + cap 10/30 (`gx-d`, khám phá, KHÔNG nằm trong k=3)

Override: `(A) + SIM_TS_MAX_GAP=0.30 + SIM_TS_MAX_GAP_WEAK=0.10`. Có `[GATE-ROLL]` BẬT, mapper 863,
`printDone` **khác** `efb793e2` (md5 riêng, n=1104) ⇒ hai key cap **bind thật**.

| | |
|---|---|
| n | 1104 |
| win% / TSloss% / mP\|SM / mP\|SL / meanP | 87.95 / 11.14 / 7.061 / −16.318 / 4.457 |
| CI vs T170 (block-72h, cả hai độ rộng) | **0 TỐT / 0 XẤU** — TSloss% +1.408 **trong** CI ở CẢ HAI |
| equity / CAGR% / maxDD toàn kỳ / UW toàn kỳ | 100 063 / 26.30 / −13.12 / 164 |
| quy min% / conc 1 coin% | −2.26 / 10.65 |
| rào cứng **năm** / **toàn kỳ** | **PASS** cả 5 năm / **PASS** |
| hold med / turn | 7.7h / 0.672 leg/ngày |
| **kết luận** | **NULL** |

**Bảng PnL chi tiết theo năm — (D) GD92 + cap 10/30**

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 147 | 88.44 | 11.56 | 3.625 | 2 476 | +7.07 | −3.59 | 44 | +1.56 | 37 476 |
| 2022 | 186 | 85.48 | 9.68 | 3.305 | 6 668 | +17.79 | −13.12 | 73 | +2.96 | 44 144 |
| 2023 | 203 | 88.18 | 15.27 | 6.773 | 20 663 | +47.01 | −2.62 | 53 | +2.64 | 64 896 |
| 2024 | 306 | 89.54 | 11.11 | 4.335 | 19 389 | +29.82 | −6.70 | 88 | −2.26 | 84 196 |
| 2025 | 262 | 87.40 | 8.78 | 4.089 | 15 867 | **+18.85** | −5.29 | **164** | +0.73 | **100 063** |

Capture (peak ≥20/50/100%): n = **150 / 25 / 12**, med_capture **0.504 / 0.502 / 0.176**,
SumPnL 49 882 / 18 146 / 8 390. Cùng kết luận: GD92 kéo chất lượng xuống, cap 10/30 không cứu được.

---

## 7. VERDICT

| chân | rate (k=3) | rào cứng **năm** | rào cứng **toàn kỳ** | kết luận |
|---|---|---|---|---|
| **(A) GD92-only** | 0 TỐT / 0 XẤU ngoài CI | PASS | PASS | **NULL** |
| **(B) GD92 + HINGE V3** | 0 TỐT / 0 XẤU ngoài CI | PASS | PASS | **NULL** |
| **(C) GD92 + LADDER L1** | 0 TỐT / 0 XẤU ngoài CI | PASS | PASS | **NULL** |
| **(D) GD92 + cap 10/30** *(tuỳ chọn, khám phá — KHÔNG nằm trong k=3)* | 0 TỐT / 0 XẤU ngoài CI | PASS | PASS | **NULL** |

**KHÔNG GO. Không chân nào đạt tiêu chí (cần ≥2 rate ngoài CI cùng hướng TỐT + 0 XẤU ngoài CI).**
GD92 **KHÔNG** làm các biến thể exit "sáng" hơn — nó **kéo chúng xuống**:

1. **Trên nền T170**, thêm GD92 (chân A) làm **mọi** điểm ước lượng (trừ mP|SL) đi theo hướng XẤU,
   mất **12.7%** equity (111 070 → 99 179) và gần **một nửa** lợi nhuận năm 2025 (+32.71% → +17.53%).
2. **(B) vs HINGE V3 trần:** điểm ước lượng tệ hơn ở **mọi** rate chất lượng (TSloss% ngoài CI @1.21,
   hướng XẤU); equity 101 460 vs **114 287**.
3. **(C) vs LADDER L1 trần:** y hệt (TSloss% ngoài CI @1.21, hướng XẤU); equity 97 909 vs **114 756**.
4. **(B) vs (A)** và **(C) vs (A)**: 0/5 rate ngoài CI ⇒ **HINGE V3 / LADDER L1 không thêm gì đo được**
   *trên nền GD92* — đúng như đã thấy khi chúng chạy một mình trên T170.
5. GD92 **chặn mất leg thắng lớn**: số leg đạt peak ≥100% giảm 21 → 11 (A/B) / 12 (C).

### Phán quyết theo đúng luật đã khoá (pre-reg §5)
**NULL cho cả A, B, C.** Viết rõ: **GD92 không phải là đòn bẩy cho biến thể exit** — nó là
thành phần **đã biết là thua** (`RESULT_GD92_RECHECK`: 0 TỐT / 3 XẤU vs T170), và khi ghép vào
T170 nó vẫn thua (chỉ khác là mức độ nhẹ hơn và **không** còn FAIL toàn kỳ như trên nền T100).
Ghép hai thứ NULL/THUA lại **không** sinh ra GO.

### So với dự đoán ghi trước (pre-reg §6)

| dự đoán | thực tế | đúng/sai |
|---|---|---|
| A/B/C đều NULL (0–1 rate ngoài CI) | **0/5 cả ba** | **ĐÚNG** |
| PASS theo năm nhưng FAIL toàn kỳ ở A/B/C (UW ~278 kéo dài) | PASS **cả hai** — UW toàn kỳ chỉ **164** | **SAI** (hiệu ứng UW 278 thuộc nền T100, không tái hiện trên T170) |
| A/B/C mang "vết" xấu của GD92 vs T170 | đúng: win%↓, TSloss%↑, mP\|SM↓, meanP↓ | **ĐÚNG** |
| GD92 không làm exit variant sáng hơn | đúng ở cả hai chiều (vs chân trần và vs A) | **ĐÚNG** |

Một quan sát ngoài dự đoán, ghi lại chứ không tô hồng: **2023 của A/B/C tốt hơn T170**
(ret +44.1/44.5/44.2% vs +35.0%) và có nhiều lệnh gấp ~1.6 lần (206/204 vs 126) — nhưng năm 2025
bù lại phần lớn phần thua, và tổng kỳ vẫn thấp hơn; đây là **dịch chuyển phân bố**, không phải cải thiện.

---

## 8. Multiplicity + kỷ luật

- Vòng này `k=3` (A/B/C vs T170). Chân **(D)** là **tuỳ chọn/khám phá**, báo cáo riêng — nếu gộp vào thì
  `k=4` cho `inflate(4)=1.6651`, và (D) **vẫn** 0/5 ngoài CI ở độ rộng đó (TSloss% +1.408 nằm trong cả
  hai độ rộng) ⇒ gộp hay không **không đổi verdict**. Đây là vòng **exit/gate thứ ~6** chống T170 trong chương trình
  (TRAIL-HINGE 3 biến thể · TRAIL-LADDER 3 · TRAIL-CAP-1030 2 · CLOSE-BIGGAP 18 · PEAK-CLOSE 1 · vòng này 3).
  Một thắng lợi đơn lẻ cũng **không đủ** để đổi incumbent — phải qua holdout 2026. Vì kết quả là NULL,
  vấn đề multiplicity **không cần viện đến**.
- **Không push.** Branch `gd92-recheck` **KHÔNG merge** vào `module`; code rolling **KHÔNG commit**
  (đã `git checkout -- src/` sau khi build; chỉ commit docs + script). **Không** chạm 242.
  **Không** đóng holdout 2026. **Không** quét biến thể GD92 (0.88/0.90/0.94/0.96, W=60/120/180).
  **Không** đổi incumbent (T170 giữ nguyên).
- Kết quả dương (nếu có) vẫn chỉ là **ứng viên**, cần forward — vòng này không có kết quả dương.
