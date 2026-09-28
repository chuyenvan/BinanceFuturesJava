# RESULT_TRACKB_REDFLAGS — gỡ 3 cờ đỏ Track B (0 sim)

Ngày đo: **2026-09-28** (D4). Pre-reg: `docs/prereg/PREREG_TRACKB_REDFLAGS.md` (**commit `322aab0`**,
chốt **TRƯỚC** khi đo; sau đó **không sửa thiết kế**). Code: `research/trackb/redflags_trackb.py`
(dùng lại `run_trackb.py`; `build_panel.py` thêm **additive** hai mảng `DVS`/`DVS_DATE` cho universe AS-OF).
JSON: `docs/result/trackb_redflags.json`.
**Thuần Python offline · 0 train / 0 sim · không chạm production/`242`/ONNX/LIVE · không push file dữ liệu ·
DEV ≤ 2025-12-31 · panel 46 MB ở `/tmp` đã dọn.**

---

## 0. KẾT LUẬN (một dòng)

> **Cả 3 cờ đỏ GỠ ĐƯỢC theo đúng tiêu chí pre-reg (3/3 ⇒ `GO` theo luật §5).** Nhưng **phát hiện quyết định
> của D4**: `+0,064 %/ngày` của đối chứng ngẫu nhiên là **`+0,059 %/ngày` do STOP −10 % (b)** + `+0,010 %`
> do **universe tĩnh (a)**; và khi **bỏ hẳn stop**, chênh gross `book − control` **sụp về `+0,006 %/ngày`,
> `CI72h [−0,034; +0,045]` (chứa 0, `p=0,63`)**. ⇒ **"edge" của Track B KHÔNG phải tín hiệu cross-section
> mà là ARTIFACT của stop −10 % (quyền chọn miễn phí, slip chỉ 0,5 %).** ⇒ **Đề xuất: KHÔNG lên bước 2 trên
> cơ sở này** (nếu lên, bước 2 **bắt buộc** mô hình stop bằng **fill thật** rồi đo lại).

---

## 1. VIỆC 1 — GỠ CỜ ĐỎ #1 (bias harness): PHÂN RÃ 2×2

Đối chứng ngẫu nhiên `n=200`, seed `20260928`, `nlong=17`/chân, dollar-neutral, cùng harness.
`TĨNH` = top-200 theo `dv_med` toàn kỳ (như step 1); `AS-OF` = top-200 theo **trung vị `dv` của các mẫu
ngày-15 `< t`** (cần `≥12` mẫu; **causal**).

| ô | universe | stop −10 % | **gross/ngày** |
|---|---|---|---|
| **A** (tái lập) | TĨNH | CÓ | **+0,0667 %** (sd 0,0168) |
| **B** | TĨNH | KHÔNG | +0,0018 % |
| **C** | AS-OF | CÓ | +0,0514 % |
| **D** | AS-OF | KHÔNG | **−0,0022 %** |

**Phân rã 3 nguồn (%/ngày):**

| nguồn | cách đo | đóng góp | % của A |
|---|---|---|---|
| **(b) STOP −10 %** | `A−B` = +0,0649; `C−D` = +0,0536 ⇒ **eff +0,0593** | **+0,0593** | **89 %** |
| **(a) universe TĨNH** | `A−C` = +0,0154; `B−D` = +0,0040 ⇒ **eff +0,0097** | **+0,0097** | **15 %** |
| **(c1) L/S lệch SỐ chân** (n_long=2·n_short, vẫn $neutral) | `c1−A` | −0,0012 | ~0 |
| **(c2) L/S lệch GROSS** (long 0,55 / short 0,45) | `c2−A` | −0,0064 | ~0 |

- **TÁI LẬP ĐÚNG:** `A = +0,0667 %` vs step-1 `+0,0642 %` ⇒ lệch **0,0025 pp** (`≤ 0,010`) ✔.
- **Giải thích được `115 %`** của `A` bằng (a)+(b)+(c) (`≥ 75 %`) ✔.
- **Sau khi sửa** (universe AS-OF, **D**): đối chứng = **`−0,0022 %/ngày`** (`|·| ≤ 0,020`) ✔ ⇒ **#1 GỠ ĐƯỢC**.
- **Cơ chế (b) (nêu rõ):** stop được mô hình như **quyền chọn MIỄN PHÍ** — long được **put free** (cắt lỗ ở
  `−10,5 %`), short được **call free** (cắt lỗ ở `+10,5 %`), **không trả premium**, slip chỉ `0,5 %`.
  Với book neutral, `E[gross] = ½·(E[(−c−R)⁺] + E[(R−c)⁺]) > 0` ⇒ **sinh gross DƯƠNG vô điều kiện tín hiệu**.
- **(c) KHÔNG phải nguồn bias** (cả hai biến thể đều **âm nhẹ**, tức làm gross giảm, không tăng).

---

## 2. VIỆC 2 — GỠ CỜ ĐỎ #2 (turnover): CONTROL CÙNG BAND/HYSTERESIS

Control = **cùng decile + cùng hysteresis `band=2` + cùng trần squeeze + cùng stop**, tín hiệu thay bằng
**random AR(1)** `z[t]=ρ·z[t−1]+√(1−ρ²)ε[t]`; **hiệu chỉnh `ρ*` để khớp turnover** (`n=15` book để chọn `ρ`,
`n=200` cho kết quả). `ρ*=0,76`.

| | TO/ngày | gross/ngày | **net @0,112 %**/ngày |
|---|---|---|---|
| **`BOOK_EW`** | 0,351 | **+0,1398 %** | **+0,1058 %** |
| **control (AR1 ρ\*=0,76)** | **0,344** (lệch **2,0 %** ✔) | +0,0660 % | −0,0330 % |
| **chênh book − control** | — | **+0,0738 %** | **+0,0783 %** |
| **CI95 raw (khối 72h)** | — | **[+0,0440 %, +0,1036 %]** `p(>0)=1,000` | **[+0,0483 %, +0,1083 %]** |
| CI95 raw (khối 10 ngày) | — | [+0,0433 %, +0,1042 %] | — |

- **Khớp turnover 2,0 % ≤ 10 %** ✔ và **chênh gross CI72h > 0** ✔ ⇒ **#2 GỠ ĐƯỢC** (theo tiêu chí §2).
- ⚠️ **NHƯNG — ô quyết định của cả D4 (bỏ hẳn stop):**

| KHÔNG stop | gross/ngày |
|---|---|
| `BOOK_EW` | +0,0063 % |
| control (ρ\*=0,76) | +0,0007 % |
| **chênh book − control** | **+0,0056 %** — **CI72h `[−0,0340 %, +0,0452 %]`, `p(>0)=0,63`** |

⇒ **Toàn bộ `+0,074 %/ngày` chênh lệch là ARTIFACT của stop**, không phải tín hiệu. Stop nâng gross book
lên **`+0,134 %/ngày`** nhưng chỉ nâng control **`+0,065 %/ngày`** ⇒ chênh `+0,068 %` = **giá trị quyền chọn
miễn phí trên coin high-vol** (mà `vol` SHORT) — **không phải alpha**.

---

## 3. VIỆC 3 — GỠ CỜ ĐỎ #3 (`vol` = beta?): HỒI QUY `pnl = α + β_btc·r_btc + β_alt·r_altEW`

`r_btc` = BTC 24h; `r_altEW` = mean 24h của universe eligible. CI `α`/`β` bằng **block bootstrap khối 72h**.

| object | PnL | **`α` (%/ngày)** | **`t_block(α)`** | CI95(α) | `β_btc` | `β_alt` | `R²` |
|---|---|---|---|---|---|---|---|
| **`vol`** | net @0,112 | **+0,0946 %** | **3,07** | **[+0,0340, +0,1549]** | +0,158 | **−0,334** | **0,500** |
| `vol` | net, khối 10 ngày | +0,0946 % | 3,20 | — | +0,158 | −0,334 | 0,500 |
| `BOOK_EW` | net @0,112 | **+0,0981 %** | **4,90** | — | +0,080 | −0,076 | 0,061 |

- **`α > 0` và `CI95(α)` khối 72h `> 0`** ⇒ **#3 GỠ ĐƯỢC**: `vol` **không** chỉ là beta BTC/alt.
- **Cảnh báo:** `R² = 0,50` cho `vol` ⇒ **một nửa phương sai ngày là beta thị trường** (`β_alt = −0,334`,
  tức book **long-alt-beta**); `α` còn dương nhưng **phần dương đó chính là artifact stop** (VIỆC 2).

---

## 4. TRẢ LỜI (bắt buộc)

1. **#1 — tái lập + phân rã?** → tái lập **`+0,0667 %/ngày`** (step1 `+0,0642`, lệch 0,0025 pp).
   **(a) universe tĩnh `+0,0097` · (b) stop −10 % `+0,0593` · (c1/c2) trọng số L/S lệch `−0,001 / −0,006`**
   (đều âm ⇒ không phải nguồn bias). **Sau khi sửa (AS-OF) + bỏ stop: đối chứng `−0,0022 %/ngày` ≈ 0.** ✔
2. **#2 — turnover khớp + chênh?** → `ρ*=0,76` ⇒ TO khớp **2,0 %**; chênh gross **`+0,0738 %`**
   `CI72h [+0,0440, +0,1036]`; chênh net@0,112 **`+0,0783 %`** `CI72h [+0,0483, +0,1083]`.
   **NHƯNG bỏ stop ⇒ chênh `+0,0056 %`, `CI72h [−0,034, +0,045]` (chứa 0).**
3. **#3 — alpha + t sau khi trừ beta?** → `vol` net **`α=+0,0946 %/ngày`, `t_block=3,07 > 1,96`**, CI `>0`;
   `β_btc +0,158`, `β_alt −0,334`, `R² 0,50`. ⇒ **không phải beta thuần**, nhưng `R²` cao và **α này = stop artifact**.
4. **3 cờ đỏ gỡ được chưa ⇒ có lên bước 2?** → **Theo pre-reg §5 (3/3 tiêu chí): `GO`.** **Theo bằng chứng
   tổng thể: `KHÔNG NÊN`** — vì **edge (chênh với control cùng turnover) biến mất khi bỏ stop**
   (`+0,006 %/ngày`, CI chứa 0). ⇒ **Track B chưa có bằng chứng alpha cross-section.**
5. **Mục nào BỎ + lý do?**
   - **BỎ claim "book có edge tín hiệu `+0,07 %/ngày`"**: chênh đó = **stop artifact**, raw signal `+0,006 %` (CI chứa 0).
   - **BỎ stop −10 % "miễn phí" làm cơ chế**: phải thay bằng **fill thật** (slip/gap, stop-market) trước khi tin con số tuyệt đối.
   - **BỎ (c) trọng số L/S lệch như nguyên nhân bias**: đo được **âm** ⇒ không đóng góp.
   - **GIỮ (a) universe AS-OF**: bỏ look-ahead/survivorship là **bản sửa đúng** (~0,010 %/ngày, nên dùng từ nay).
   - **GIỮ cảnh báo `vol` = SHORT VOL/beta**: `R²=0,50`, `β_alt=−0,334` ⇒ **short-vol position**, không phải alpha thuần.
   - **Rào (a)/(b′) vẫn FAIL** (từ step 1 / BOOK_COST2) ⇒ dù sao cũng **không deploy**.

---

## 5. SẢN PHẨM + TÁI LẬP

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_TRACKB_REDFLAGS.md` | pre-reg, commit **`322aab0`** |
| `research/trackb/redflags_trackb.py` | VIỆC 1/2/3 (**~512 s**, 0 byte ghi bền) |
| `research/trackb/build_panel.py` | thêm `DVS`/`DVS_DATE` (additive) cho universe AS-OF |
| `docs/result/trackb_redflags.json` | mọi số + nguồn |

```bash
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages python3 research/trackb/build_panel.py    # ~59 s
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages python3 research/trackb/redflags_trackb.py # ~512 s
```

**Hạn chế (ghi trước, đúng pre-reg §6):** control random là **xấp xỉ** cơ chế book; `ρ*` chọn trên `n=15`
(độ ồn ~±3 %); hồi quy BTC/alt **đa cộng tuyến** (2 regressor ~0,8 tương quan); mọi kết luận là **mô tả quá
khứ DEV**, **không** deploy. **Panel `/tmp/trackb` (46 MB) đã dọn.**
