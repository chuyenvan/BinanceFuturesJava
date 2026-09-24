# RESULT — TRẦN TẬP TRUNG 1 COIN 15% (`CONC_CAP_PERCOIN`) TRÊN NỀN NHIỀU LỆNH

Thực thi `docs/PREREG_CONC_CAP_HIGHN.md` (commit **`a93982f`**, viết TRƯỚC khi chạy).
Script: `research/analysis/conccap_run.py` + `conccap_score.py` + `conccap_driver3.py`
(commit **`707bc00`**, driver3 = bản chịu 429/404, xem §8).
Code: `git cherry-pick -n 1db0613` (branch `gd92-recheck`) vào `module` HEAD `4850b03` — **KHÔNG commit,
KHÔNG merge**; sau khi build đã `git reset` + `git checkout -- src/` + **xoá** file mới
⇒ `git diff HEAD -- src/` **rỗng**, `module/src` **NGUYÊN TRẠNG**, `GateRollingThreshold.java`
**không còn** trên `module`.
Jar **sha256 `c2b0c9634526c265c371fde04f9eef070bc6f9156263bdd33261a0b46c9c025c`** (99,709,921 byte;
`mvn -o package`: **154 test / 0 fail / 0 error**), đóng gói Kaggle dataset
**`chuyendinh/sim-jar-conccap`** (kèm `JAR_PROVENANCE.txt`).
Mọi sim chạy **trên Kaggle CPU kernel** (`docs/KAGGLE_SIM.md`) — **KHÔNG** chạy Java/sim trên Oracle.
Cửa sổ `20210701 .. 20251230` (DEV), `TICKER_SOURCE=file`, mapper **863** (≥ 800 guard) ở **mọi** chân,
`jar_sha256 = c2b0c963…` ở **mọi** chân. **KHÔNG** chạm 2026. **KHÔNG** push. Chi phí Kaggle: **0**.

---

## 0. KẾT LUẬN (một dòng)

> **Cơ chế ĐÚNG và ĐO ĐƯỢC: trần 15% hạ tập trung 1 coin từ 27.23% → 10.83% (T100, chặn 44 leg)
> và 15.29% → 8.92% (GD92+CAP, chặn 37 leg), KHÔNG làm rate nào XẤU ngoài CI, và cái giá PnL
> ≤ 5.5% (T100 còn ĐƯỢC THÊM +8.4% realized).** Nhưng **nó KHÔNG cứu được rào cứng nào**
> (`UW` toàn kỳ vẫn 248/249 > 200 — `UW` mới là rào đang chặn, không phải `maxDD`), và trên nền
> **GD92 thuần nó là NO-OP** (`blocked=0`, md5 giống hệt OFF). ⇒ **ĐỀ XUẤT: bật mặc định
> `CONC_CAP_PERCOIN_ENABLED=1 / PCT=0.15`** (an toàn + không mất chất lượng), **KHÔNG tự bật**,
> **KHÔNG** coi đây là GO cho T100/GD92 (2 nền này vẫn FAIL rào cứng toàn kỳ từ trước, không do cap).
>
> **Bổ sung 3.3**: dưới khẩu vị MỚI NHẤT (`RISK_APPETITE.md` §7, `UW ≤ 250` — commit `2350f47`
> nới **giữa lúc vòng này chạy**), bật cap biến **`cc-t100` và `cc-g-cp` thành PASS HẾT rào cứng**
> (chúng chỉ còn FAIL vì `conc`); `GD92` thuần vẫn FAIL vì `UW 278` — cap không chạm tới UW.

---

## 1. CỔNG CHẶN — TẤT CẢ PASS (đo TRƯỚC khi đọc kết quả)

| cổng | kỳ vọng (pre-reg §3) | đo được | kết |
|---|---|---|---|
| **P1 parity** | `cc-par1` = `x1_gs_t170`, cap **OFF**: md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, eq 111,070 | md5 **`efb793e2468ca3a7318da0f0ad23d4fc`**, n=**1089**, eq **111,070**, `java_rc=1`, mapper 863, jar `c2b0c963` | **PASS** |
| **P2 rolling thật** | `[GATE-ROLL] BAT: pct=0.92 window=90d` + không truy vấn trước mốc đầu | `cc-g92` + `cc-g-cp` đều có dòng BAT (pct=0.92 W=90d, 39,510 mốc, mốc đầu 1624989600000 = 2021-06-30, ngưỡng 0.456–1.265%) và **`beforeFirst_warn = 0`** | **PASS**† |
| **P3 cap bind THẬT** | `[CONC-PC] MODE pct=0.15` + `SUMMARY blocked=N ≥ 1` + md5 khác OFF | `cc-t100`: MODE ✓, **blocked=44**, md5 `9ba7b022…` ≠ OFF; `cc-g-cp`: MODE ✓, **blocked=37**, md5 `a78b9b05…` ≠ OFF; **`cc-g92`: blocked=0** | **PASS** (và **ghi rõ: `cc-g92` TẦM THƯỜNG**) |
| **P4 key bind** | md5 ON khác OFF ở ≥1 chân | 2/3 chân khác; `cc-g92` **trùng byte** (`cd913759…`) | **PASS** |

† **Đính chính nhỏ so với pre-reg:** pre-reg ghi `nBeforeFirst=0`, nhưng bản build này **không in**
counter `nBeforeFirst` (hàm `GateRollingThreshold.stats()` không được gọi ở đâu trong code); bằng
chứng **tương đương** là **0 cảnh báo** `[GATE-ROLL] truy vấn … TRUOC moc gio dau tien` trong log —
đã kiểm bằng máy (`before_first_warn=0` ở **cả** `cc-g92` và `cc-g-cp`). Không có mốc nào bị truy vấn
trước mốc đầu.

**Kiểm tra "1 trục" cục bộ:** profile chạy ON chỉ khác profile OFF đúng **2 dòng**
`CONC_CAP_PERCOIN_ENABLED=1` + `CONC_CAP_PERCOIN_PCT=0.15` (đã diff key/giá trị:
`hn-g92` vs `hn-g-cp` khác đúng 2 dòng CAP; `hn-t100` vs `hn-g92` khác đúng 2 dòng rolling).

---

## 2. CƠ CHẾ — guard bind ở đâu, chặn cái gì

| chân | md5 `printDone` | n | equity | `blocked` (SUMMARY) | dòng SKIP | coin bị chặn | level |
|---|---|---|---|---|---|---|---|
| `hn-par1` (T170, cap OFF) | `efb793e2…` | 1,089 | 111,070 | — | 0 | — | — |
| **`cc-t100`** | `9ba7b0223351a5…` | **2,557** | **129,024** | **44** | 44 | **CUDIS 43 + ALPINE 1** | **DCA_LEVEL1 ×44** |
| `hn-t100` (OFF) | `dc16e4da…` | 2,559 | 121,770 | — | 0 | — | — |
| `cc-g92` | `cd913759ecd4bf…` **= OFF** | 2,632 | 133,944 | **0** | 0 | — | — |
| `hn-g92` (OFF) | `cd913759ecd4bf…` | 2,632 | 133,944 | — | 0 | — | — |
| **`cc-g-cp`** | `a78b9b050b2bf7…` | **2,607** | **143,137** | **37** | 37 | **JELLYJELLY 37** | **DCA_LEVEL1 ×37** |
| `hn-g-cp` (OFF) | `43fb90ee41c29b…` | 2,608 | 149,400 | — | 0 | — | — |

- `đếm SKIP trong sim.out == SUMMARY blocked=` trên **mọi** chân (scorer assert).
- **Guard bind ĐÚNG chỗ đau**: T100 bị chặn toàn bộ leg DCA thêm của **CUDIS** (28.51% equity ở
  `RESULT_FRAGILITY_N`) và 1 leg **ALPINE** (20.31%); GD92+CAP bị chặn toàn bộ leg DCA thêm của
  **JELLYJELLY** (15.29%). Đều ở `DCA_LEVEL1`.
- **`cc-g92`: `blocked=0` ⇒ KẾT QUẢ TẦM THƯỜNG.** Đỉnh tập trung OFF của GD92 (14.38%) **thấp hơn**
  trần 15% ⇒ guard không bao giờ chạm ⇒ `cc-g92` ≡ `hn-g92` **byte-identical**. Đúng như dự đoán
  ghi trước (pre-reg §7).

---

## 3. BẢNG CHÍNH — OFF vs ON từng chân

| chân | n OFF→ON | **conc OFF→ON** | bind | **XAU ngoài CI** (cả 2 độ rộng) | UW | maxDD | năm âm | **PnL mất** (realized) | equity |
|---|---|---|---|---|---|---|---|---|---|
| **T100** | 2,559 → 2,557 | **27.23% → 10.83%** ✓ | **44** | **0/5** | 248 → **248** | −16.13 → −16.13 | không | **−8.36% (ĐƯỢC THÊM)** | 121,770 → **129,024 (+5.96%)** |
| **GD92** | 2,632 → 2,632 | 14.38% → 14.38% | **0** | 0/5 (**no-op**) | 278 | −16.55 | không | **0.00%** | 133,944 → 133,944 |
| **GD92+CAP** | 2,608 → 2,607 | **15.29% → 8.92%** ✓ | **37** | **0/5** | 249 → 249 | −17.65 → −17.65 | không | **5.47% (mất)** | 149,400 → **143,137 (−4.19%)** |

- `maxDD` báo **cả hai chuẩn**: S1 `≤30%` và S2 `≤40%` — **mọi chân đều dưới cả hai** (pre-reg §5).
- **Không năm nào âm** ở bất kỳ chân nào (như mọi vòng trước).
- `UW` **không đổi** khi bật cap (cap chặn margin 1 coin, không liên quan đỉnh vốn): T100 248,
  g-cp 249, g92 278 ⇒ **vẫn FAIL toàn kỳ** `UW ≤ 200` (rào đang chặn thật sự).

### 3.1 Năm rate chi tiết (ON − OFF), CI block-72h 2000 rep seed 20260905 anchor 2021-07-01

| nền | rate | Δ | CI @x1.21 | CI @inflate(3)=1.4823 | ngoài? |
|---|---|---|---|---|---|
| **T100** (`cc-t100` − `hn-t100`) | win% | **+0.105** | [−0.024, 0.252] | [−0.055, 0.283] | trong |
| | TSloss% | **−0.262** | [−0.692, 0.066] | [−0.777, 0.151] | trong (nghiêng TỐT) |
| | mP\|SM | −0.030 | [−0.259, 0.149] | [−0.305, 0.195] | trong |
| | mP\|SL | +0.228 | [−0.328, 1.064] | [−0.485, 1.220] | trong |
| | meanP | **+0.078** | [−0.021, 0.220] | [−0.048, 0.247] | trong |
| **GD92** (`cc-g92` − `hn-g92`) | *5/5 rate* | **0.000** | [0, 0] | [0, 0] | byte-identical (no-op) |
| **GD92+CAP** (`cc-g-cp` − `hn-g-cp`) | win% | −0.006 | [−0.024, 0.002] | [−0.027, 0.005] | trong |
| | TSloss% | +0.083 | [−0.028, 0.299] | [−0.065, 0.335] | trong |
| | mP\|SM | +0.042 | [−0.059, 0.205] | [−0.089, 0.235] | trong |
| | mP\|SL | −0.235 | [−0.930, 0.088] | [−1.045, 0.203] | trong (nghiêng XẤU nhẹ) |
| | meanP | −0.023 | [−0.071, 0.007] | [−0.080, 0.016] | trong (nghiêng XẤU nhẹ) |

⇒ **Tổng XAU ngoài CI trên cả 3 cặp = 0/15** (0/5 mỗi cặp, ở **cả hai** độ rộng).
Tham chiếu (KHÔNG phải tiêu chí): mọi chân nhiều lệnh đều XAU **3/5 vs T170** (T170 nhiều win% hơn)
— đúng như `RESULT_GD92_RECHECK`/`RESULT_EXIT_HIGH_N` đã ghi; **cap không sửa được khoảng cách đó**.

### 3.2 Rào cứng (RISK_APPETITE) — theo năm VÀ toàn kỳ, cả S1 (DD 30%) lẫn S2 (DD 40%)

| chân | 2021 | 2022 | 2023 | 2024 | 2025 | toàn kỳ |
|---|---|---|---|---|---|---|
| `hn-t100` (OFF) | P | P | P | P | **F (UW 227)** | **FAIL (UW 248, conc 27.23)** |
| **`cc-t100`** | P | P | P | P | **F (UW 224)** | **FAIL (UW 248)** — **conc đã hết FAIL** |
| `hn-g92` (OFF) | P | P | P | P | P | **FAIL (UW 278)** |
| `cc-g92` (ON) | P | P | P | P | P | **FAIL (UW 278)** |
| `hn-g-cp` (OFF) | P | P | P | P | P | **FAIL (UW 249, conc 15.29)** |
| **`cc-g-cp`** | P | P | P | P | P | **FAIL (UW 249)** — **conc đã hết FAIL** |

- Cap **xoá đúng 1 mục FAIL duy nhất mà nó nhắm tới: `conc ≤ 15%`** (T100 và g-cp).
  `cc-g92` không đổi (vốn 14.38% < 15% ⇒ đã PASS conc).
- **`UW ≤ 200` KHÔNG đổi** và vẫn là rào đang chặn (đúng nhận định `RESULT_FRAGILITY_N` §6.4).
- **`maxDD` không phải rào chặn**: mọi chân dưới **cả** 30% và 40% theo năm lẫn toàn kỳ.

### 3.3 Chấm THÊM dưới khẩu vị MỚI NHẤT của `RISK_APPETITE.md` §7 (UW ≤ 250, quỹ ≥ −20%)

`RISK_APPETITE.md` được nới **giữa lúc vòng này đang chạy** (commit `2350f47`, 09:06:56 — sau
pre-reg `a93982f` 08:37): `UW 200 → 250`, `quỹ xấu nhất −15% → −20%`, `maxDD 30% → 40%`,
`conc ≤ 15%` **GIỮ**, `không năm âm` **GIỮ**. Pre-reg đã khoá theo đúng thang task giao
(`UW ≤ 200`) nên **không đổi**; dưới đây là **báo cáo thêm** dưới thang mới:

| chân | maxDD ≤ 40% | UW ≤ 250 | quỹ ≥ −20% | conc ≤ 15% | năm âm | dưới §7 (mới) |
|---|---|---|---|---|---|---|
| `hn-t100` (OFF) | −16.13 ✓ | 248 ✓ | −4.64 ✓ | **27.23 ✗** | không | **FAIL (chỉ vì conc)** |
| **`cc-t100`** | −16.13 ✓ | 248 ✓ | −4.64 ✓ | **10.83 ✓** | không | **PASS HẾT** |
| `hn-g92` (OFF) | −16.55 ✓ | **278 ✗** | −4.59 ✓ | 14.38 ✓ | không | **FAIL (UW)** |
| `cc-g92` | −16.55 ✓ | **278 ✗** | −4.59 ✓ | 14.38 ✓ | không | **FAIL (UW)** |
| `hn-g-cp` (OFF) | −17.65 ✓ | 249 ✓ | −5.58 ✓ | **15.29 ✗** | không | **FAIL (chỉ vì conc)** |
| **`cc-g-cp`** | −17.65 ✓ | 249 ✓ | −5.58 ✓ | **8.92 ✓** | không | **PASS HẾT** |

⇒ **Dưới khẩu vị mới, bật cap 15% là thứ DUY NHẤT xoá được mục FAIL còn lại của T100 và GD92+CAP**
(biến 2/3 nền nhiều lệnh từ FAIL thành **PASS hết rào cứng**); GD92 thuần vẫn FAIL vì `UW`
(cap không chạm tới). **Lưu ý đo lường:** §7.3 (commit `7d85426`, 11:04) đã đổi cách đo `maxDD`
sang **MTM mốc PHÚT** (dao sâu hơn chuỗi ngày: T100 −16.13% → **−26.26%**, T170 −11.84% → −19.96%)
— số ở bảng trên là **thang CŨ (chuỗi ngày)** dùng đúng như pre-reg đã khoá; **dưới thang phút mới
thì `maxDD` vẫn dưới 40%** nên không đổi kết luận PASS/FAIL, nhưng biên an toàn mỏng hơn nhiều.

---

## 4. BẢNG PnL CHI TIẾT THEO NĂM — OFF vs ON (và cap "mất" bao nhiêu)

### 4.1 T100 (`hn-t100` OFF / `cc-t100` ON)

| chân | năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OFF | 2021 | 293 | 81.57 | 18.43 | 2.122 | 3,248 | +9.28 | −7.35 | 47 | −0.56 | 38,247 |
| OFF | 2022 | 406 | 82.27 | 17.00 | 2.200 | 6,619 | +17.31 | −12.46 | 64 | +0.63 | 44,866 |
| OFF | 2023 | 308 | 88.64 | 13.64 | 5.767 | 27,014 | +60.43 | −2.51 | 45 | +7.80 | 71,978 |
| OFF | 2024 | 668 | 86.23 | 14.52 | 3.902 | 32,687 | +45.36 | −11.36 | 121 | −4.64 | 104,567 |
| OFF | 2025 | 884 | 83.26 | 14.82 | 2.512 | 17,202 | +16.45 | −10.60 | 227 | −2.47 | 121,770 |
| **ON** | 2021–2024 | *giống hệt OFF* | | | | | | | | | |
| **ON** | 2025 | **882** | **83.56** | **14.06** | **2.738** | **24,457** | **+23.39** | **−9.20** | **224** | −2.47 | **129,024** |
| | | | | | | **Σ OFF 86,770 → ON 94,025** | | | | | **+5.96%** |

⇒ **Cap KHÔNG mất PnL trên T100 — nó ĐƯỢC THÊM `+7,255 USDT = +8.36%`** realized (equity +5.96%),
mọi thay đổi nằm ở **2025** (năm CUDIS/ALPINE bị chặn leg DCA). 4 năm đầu **byte-identical**.
`TSloss%` 2025 **giảm** 14.82 → 14.06, `maxDD` 2025 **giảm** −10.60 → −9.20, `UW` 227 → 224.

### 4.2 GD92 (`hn-g92` OFF / `cc-g92` ON) — **GIỐNG HỆT TỪNG BYTE**

| chân | năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cả hai | 2021 | 277 | 79.78 | 20.22 | 1.665 | 1,343 | +3.83 | −7.74 | 47 | −0.65 | 36,342 |
| cả hai | 2022 | 416 | 79.57 | 19.71 | 1.276 | 2,637 | +7.26 | −13.21 | 69 | −3.81 | 38,980 |
| cả hai | 2023 | 509 | 86.05 | 16.50 | 4.659 | 29,241 | +74.11 | −5.24 | 63 | +13.32 | 67,868 |
| cả hai | 2024 | 792 | 84.47 | 16.29 | 3.572 | 29,714 | +43.91 | −11.36 | 114 | −4.59 | 97,935 |
| cả hai | 2025 | 638 | 85.11 | 11.60 | 3.968 | 36,009 | +36.77 | −6.11 | 116 | +1.72 | 133,944 |
| | | | | | | **Σ 98,944 → 98,944** | | | | | **0.00%** |

### 4.3 GD92+CAP (`hn-g-cp` OFF / `cc-g-cp` ON)

| chân | năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OFF | 2021 | 275 | 79.64 | 20.36 | 1.923 | 1,961 | +5.60 | −7.89 | 47 | +0.47 | 36,961 |
| OFF | 2022 | 416 | 79.81 | 19.71 | 1.332 | 3,167 | +8.76 | −13.25 | 73 | −2.97 | 40,200 |
| OFF | 2023 | 499 | 86.37 | 16.43 | 4.813 | 31,750 | +78.06 | −5.48 | 63 | +13.43 | 71,580 |
| OFF | 2024 | 783 | 84.29 | 16.48 | 3.818 | 38,558 | +53.89 | −12.03 | 149 | −5.58 | 110,437 |
| OFF | 2025 | 635 | 85.04 | 11.65 | 3.950 | 38,963 | +35.28 | −7.00 | 112 | +0.74 | 149,400 |
| **ON** | 2021–2024 | *giống hệt OFF* | | | | | | | | | |
| **ON** | 2025 | **634** | 85.02 | **11.99** | 3.854 | **32,701** | **+29.61** | −7.00 | 112 | +0.74 | **143,137** |
| | | | | | | **Σ 114,400 → 108,138** | | | | | **−4.19%** |

⇒ **Cap mất `6,263 USDT = 5.47%`** realized (equity −4.19%), **toàn bộ ở 2025** (JELLYJELLY).
4 năm đầu **byte-identical**. `TSloss%` 2025 tăng nhẹ 11.65 → 11.99.

### 4.4 Trả lời thẳng: "chặn tập trung mất bao nhiêu PnL?"

| chân | realized `Σ pnl` OFF → ON | **mất** | equity OFF → ON | equity Δ |
|---|---|---|---|---|
| T100 | 86,770 → 94,025 | **−8.36% (tức ĐƯỢC THÊM 8.36%)** | 121,770 → 129,024 | **+5.96%** |
| GD92 | 98,944 → 98,944 | 0.00% (no-op) | 133,944 → 133,944 | 0.00% |
| GD92+CAP | 114,400 → 108,138 | **+5.47% (mất)** | 149,400 → 143,137 | **−4.19%** |

**Ngưỡng pre-reg §6 là `≤ ~10%` ⇒ CẢ HAI chân bind đều ĐẠT** (T100 không mất gì, g-cp mất 5.47%).

---

## 5. n / meanP-leg / hold / turnover / Σfunding / ΣPnL

| tag | n | meanP/leg (USDT) | hold_med (giờ) | turnover | Σfunding | funding/leg | ΣPnL | **Σfunding/ΣPnL** |
|---|---|---|---|---|---|---|---|---|
| `hn-par1` (T170) | 1,089 | 69.853 | 4.8 | 0.662 | −2,097.6 | −1.93 | 76,070 | **−2.76%** |
| `hn-t100` (OFF) | 2,559 | 33.908 | 11.1 | 1.557 | −9,308.8 | −3.64 | 86,770 | **−10.73%** |
| **`cc-t100`** | 2,557 | 36.772 | 11.1 | 1.555 | −10,134.2 | −3.96 | 94,025 | **−10.78%** |
| `hn-g92` (OFF) | 2,632 | 37.593 | 12.5 | 1.601 | −6,259.5 | −2.38 | 98,944 | **−6.33%** |
| **`cc-g92`** | 2,632 | 37.593 | 12.5 | 1.601 | −6,259.5 | −2.38 | 98,944 | **−6.33%** |
| `hn-g-cp` (OFF) | 2,608 | 43.865 | 14.2 | 1.586 | −7,213.7 | −2.77 | 114,400 | **−6.31%** |
| **`cc-g-cp`** | 2,607 | 41.480 | 14.2 | 1.586 | −7,182.8 | −2.76 | 108,138 | **−6.64%** |

⇒ Cap **không sửa được hạng số hạng funding** (T100 −10.73 → **−10.78%**, xấu hơn 0.05pp; g-cp
−6.31 → −6.64%). `Σfunding/ΣPnL` vẫn là hạng **hệ thống theo n** như `RESULT_FRAGILITY_N` §6.3 —
**cap không phải thuốc chữa funding**. `hold_med` và `turnover` gần như không đổi.

---

## 6. KẾT LUẬN + ĐỀ XUẤT (theo luật khoá trước ở pre-reg §6)

Luật: **đề xuất bật mặc định CHỈ KHI** (i) 0 rate XAU ngoài CI ở mọi chân bind ≥ 1;
(ii) conc max ≤ 15% ở mọi chân ON; (iii) PnL mất ≤ ~10% toàn kỳ ở mọi chân ON.

| điều kiện | đo được | đạt? |
|---|---|---|
| (i) 0 XAU ngoài CI (cả 2 độ rộng) | 0/5 ở **cả hai** chân bind (T100, g-cp) | ✅ |
| (ii) conc ≤ 15% mọi chân ON | 10.83% (T100) · 8.92% (g-cp) · 14.38% (g92) | ✅ |
| (iii) PnL mất ≤ 10% | T100 **+8.36%** · g-cp **−5.47%** · g92 0% | ✅ |

> ### ⇒ **ĐỀ XUẤT: bật mặc định `CONC_CAP_PERCOIN_ENABLED=1` + `CONC_CAP_PERCOIN_PCT=0.15`.**
> **KHÔNG tự bật, KHÔNG tự tích hợp sản xuất** (chờ user/master quyết).

**Kèm 4 điều kiện biên PHẢI đọc kèm (không được trích riêng dòng đề xuất):**

1. **Cap KHÔNG phải GO cho T100/GD92.** Hai nền này **FAIL rào cứng toàn kỳ từ trước**
   (`UW` 248/249 > 200; nhiều rate XAU ngoài CI **so với T170**). Cap chỉ xoá **đúng 1 mục**
   (`conc`) — nó là **giảm rủi ro**, không phải một chiến lược mới.
2. **Trên GD92 thuần, cap là NO-OP** (`blocked=0`, `cc-g92` byte-identical `hn-g92`) ⇒ khi
   đỉnh tập trung lịch sử < 15%, trần 15% không bảo vệ thêm gì. Nếu muốn bảo vệ nhiều hơn phải
   hạ `PCT` (0.10) — **ngoài phạm vi pre-reg này, chưa đo**.
3. **Rào chặn thật vẫn là `UW ≤ 200`**, không phải `conc` cũng không phải `maxDD`
   (mọi chân dưới cả 30% và 40%). Bật cap **không** làm ai "GO".
4. **Cái giá đo được là thật nhưng nhỏ và 1 phía**: chỉ ảnh hưởng **2025** (4 năm đầu
   byte-identical); T100 **được thêm** +8.36% còn GD92+CAP **mất** 5.47% — tức **không đồng nhất
   dấu**, đúng bản chất "chặn thì bỏ lỡ cả lệnh thắng lẫn lệnh thua, ở đây nghiêng về bỏ lệnh thua".
   **Đừng dùng equity/CAGR để chọn** (chỉ báo cáo).
5. **Kết quả T100 (+8.36%) là một quan sát của MỘT mẫu lịch sử**, không phải kỳ vọng;
   khía cạnh bảo vệ **không hồi phục được** (coin về 0 khi đang giữ) **không** được kiểm ở vòng này
   (chưa có nhãn delist — xem `RESULT_FRAGILITY_N` §5.3).

---

## 7. DỰ ĐOÁN GHI TRƯỚC — đối chiếu

| dự đoán (pre-reg §7) | kết quả |
|---|---|
| `cc-t100` bind mạnh, conc → ≤15% | ✅ bind 44, 27.23% → 10.83% |
| `cc-g92` bind ≈ 0 ⇒ OFF ≡ ON, tầm thường | ✅ **blocked=0, md5 y hệt** |
| `cc-g-cp` bind rất ít | ⚠️ bind **37** (nhiều hơn "rất ít" dự đoán) — vì JELLYJELLY tích luỹ 37 leg DCA |
| 0 rate XAU ngoài CI | ✅ 0/15 |
| PnL mất ở T100 nhỏ (<10%) | ✅ **không mất, mà +8.36%** |
| KHÔNG chân nào GO | ✅ |

---

## 8. PHƯƠNG PHÁP / CẢNH BÁO (đọc trước khi trích dẫn)

1. **Đối chứng OFF dùng lại artifact Kaggle có sẵn** (`hn-t100`, `hn-g92`, `hn-g-cp`) — cùng
   bundle `sim-x1-2021-bundle`, cùng cửa sổ, cùng dataset ticker. Jar OFF là `bb282f40…`
   (vòng `RESULT_EXIT_HIGH_N`), jar ON là `c2b0c963…` — **cùng nguồn** (`module` + `cherry-pick -n
   1db0613`); chứng minh tương đương: **P1 parity byte-identical trên T170** với jar mới, và
   **`cc-g92` byte-identical `hn-g92`** (nhánh rolling, jar cũ) ⇒ cherry-pick **trung tính hành vi**.
2. **CI "ngoài" = ngoài ở CẢ HAI độ rộng** (legacy ×1.21 **và** chuẩn hoá `inflate(k=3)=1.482304`;
   k = 3 chân ứng viên so với baseline của nó). Không nhân chồng hệ số.
3. **`conc` dùng thước của `gd92xexit_score.conc_max`** (gom `(sym, end)`, chia equity ngày bắt đầu)
   — cùng công thức đã dùng ở `RESULT_FRAGILITY_N` §2 (`T100 27.23`, `GD92 14.38`) nên so được.
   (`RESULT_FRAGILITY_N` §1(b) còn báo 28.51% cho T100 theo thước "max theo mốc PHÚT + equity
   `b+unP`" — hai thước khác nhau, **cùng kết luận vượt trần**.)
4. **`maxDD`/`UW`/`qmin`/`ret%` lấy từ `logs/sim.out`** (`b+unP`) qua `gd92xexit_score`, cùng công
   thức `RESULT_EXIT_HIGH_N`; `maxDD` theo năm cộng dồn lại thành maxDD toàn kỳ.
5. **Chi phí & thời gian Kaggle**: **0 USD** (CPU kernel không tính quota). 4 kernel:
   `cc-par1` (1,128s JVM), `cc-t100` (1,183s), `cc-g92` (727s), `cc-g-cp` (1,079s).
   Wall-clock thực tế **~2h35m** (09:00 → 11:32 giờ VN) vì **slot 5/5 bị job `ofi-v3-build-s0..s5`
   của chương trình OFI chiếm suốt** — 3 chân `cc-t100/g92/g-cp` phải **push lại nhiều lần** cho tới
   khi có slot (xem `conccap_driver3.py`): Kaggle **tạo kernel nhưng KHÔNG tạo run khi hết slot**
   (API trả `404 No runs found for this kernel`, không báo lỗi) — bẫy mới, đã ghi lại.
6. **Không đọc 2026**: `date_last = 20251230` ở cả 4 chân.
7. Vòng này **không** quét biến thể (pct 0.10/0.20, aggregate cap, exit/gate mới) và **không** đổi
   incumbent (T170 giữ).

---

## 9. ARTIFACT

| thứ | đường dẫn / giá trị |
|---|---|
| pre-reg | `docs/PREREG_CONC_CAP_HIGHN.md` (commit `a93982f`) |
| script | `research/analysis/conccap_run.py`, `conccap_score.py`, `conccap_driver3.py`, `conccap_score.json` (commit `707bc00`) |
| code | `cherry-pick -n 1db0613`; `GateRollingThreshold.java` md5 `e1e99295c76bfd066493ca25ebeb1243` (149 dòng); **`module/src` nguyên trạng** |
| jar | sha256 `c2b0c9634526c265c371fde04f9eef070bc6f9156263bdd33261a0b46c9c025c`; Kaggle ds `chuyendinh/sim-jar-conccap` |
| output | `/home/ubuntu/kaggle_sim/out/{cc-par1,cc-t100,cc-g92,cc-g-cp}` |
| md5 `printDone` | par1 `efb793e2468ca3a7318da0f0ad23d4fc` · t100 `9ba7b0223351a5f5982c87d36b0b1d94` · g92 `cd913759ecd4bf50adab2b818eaf9525` · g-cp `a78b9b050b2bf75a4a6ca7dadb3e4203` |
