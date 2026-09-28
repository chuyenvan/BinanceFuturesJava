# RESULT_RULERS_UNIT — Rào (a)/(b′) ở **cấp VỊ THẾ** vs **cấp NGÀY** cho Track B

Ngày đo: **2026-09-28**. Pre-reg: `docs/prereg/PREREG_RULERS_UNIT.md` (**commit `107d411`**, chốt **TRƯỚC**;
sau đó **không sửa thiết kế**).
Code: `research/trackb/rulers_unit.py` (tái dùng `run_trackb.py` — **không đổi book**).
JSON: `docs/result/rulers_unit.json`.

**Tuân thủ:** thuần Python **offline** · **0 train / 0 sim** · giữ box Oracle **nhẹ** · **không** chạm
production/`242`/ONNX/LIVE · **không push file dữ liệu** · **DEV ≤ 2025-12-31** (**không** chạm 2026) ·
panel trung gian `/tmp/trackb/panel.npz` (45,8 MB) dọn sau commit.

---

## 0. KẾT LUẬN (một dòng)

> **Rào (a)/(b′) FAIL ở CẢ HAI đơn vị** — và ở **đơn vị ĐÚNG** (cấp **vị thế**, `n = 142 406`) thì
> **FAIL nặng hơn**: `BOOK_EW` `share top-1 % = 264,9 %` (CI raw *[192,6; 415,8]*) ≫ 15 % · `TF(25 %) = −18,57`
> (CI *[−19,59; −17,63]*, `p(>0)=0,000`). Ở **cấp NGÀY** (`n = 1 460`) cũng FAIL nhưng **dịu hơn 6,5–9,1×**
> (`share top-1 % = 40,5 %`, `TF25 = −2,04`). ⇒ **Sai đơn vị KHÔNG phải nguyên nhân FAIL**;
> **vòng trước cũng KHÔNG dùng đơn vị NGÀY** (nó dùng legs **vị thế** `n = 411 971`) — **giả thuyết đơn vị bị BÁC**.
> Track B **vẫn** không đạt rào ⇒ **không đủ điều kiện lên bước 2** *(dù net CI dương)*.

---

## 1. BA ĐƠN VỊ (đúng như pre-reg §1)

| mã | đơn vị | 1 leg = gì | `n` (`BOOK_EW`) |
|---|---|---|---|
| **U1** | **CẤP VỊ THẾ (coin-ngày)** — *chính* | PnL **ròng** 1 ô `(coin, ngày)` có hoạt động (`w≠0` hoặc `Δw≠0`), gồm phí của chính nó; long/short **gộp** | **142 406** |
| **U2** | **CẤP NGÀY (book)** — *đối chiếu* | PnL ròng cả book 1 ngày | **1 460** |
| **U0** | **TÁI LẬP vòng trước** — *đo chênh* | `concat` 4 tín hiệu của **(a)** PnL vị thế **+** **(b)** entry **phí thuần** (chia 4), đúng `run_trackb.py:282` | **411 971** |

**Kiểm chứng dựng lại (bắt buộc):** U0 **tái lập CHÍNH XÁC** `RESULT_TRACKB_STEP1`/`COST2`:
`n = 411 971` · `sum = 1,5455` · `share top-1 % = 413,066` (khớp `book_cost2_trackb.json`) ·
`Σlegs(U1) = Σlegs(U2) = Σlegs(U0) = 1,5455` ⇒ **net/ngày = +0,10586 %** ở **cả 3 đơn vị**
(khớp `RESULT_BOOK_COST2` `+0,1059 %/ngày`) ⇒ các đơn vị **cùng một PnL**, chỉ khác cách **chia leg**.

---

## 2. BẢNG CHÍNH — 3 đơn vị × 6 object (chi phí có hướng `0,112 %/vòng`)

### 2.1 `BOOK_EW` (4 tín hiệu)

| đơn vị | `n` | **`share top-1 %`** (rào a) | **`TF(25 %)`** (rào b′) | `q*` | `asym` | `winrate` | `median` |
|---|---|---|---|---|---|---|---|
| **U1 (vị thế)** | 142 406 | **264,94** · CI raw **[192,56; 415,80]** | **−18,569** · CI raw **[−19,590; −17,628]**, `p(>0)=0,000` | **0,5 %** | 0,655 | 0,410 | −0,000004 |
| **U2 (ngày)** | 1 460 | **40,49** · CI raw **[28,26; 58,05]** | **−2,039** · CI raw **[−2,467; −1,637]**, `p(>0)=0,000` | **5,5 %** | 0,810 | 0,553 | +0,000679 |
| **U0 (vòng trước)** | 411 971 | **413,07** · CI raw **[299,48; 647,81]** | **−29,356** · CI raw **[−30,705; −28,103]**, `p(>0)=0,000` | 0,5 % | 0,305 | 0,241 | −0,000002 |

**Verdict:** **(a) FAIL · (b′) FAIL ở CẢ BA đơn vị.** Ở U1 và U0, `q* = 0,5 %` (bước nhỏ nhất đã làm tổng ≤ 0);
U2 `q* = 5,5 %` ngày.

### 2.2 Bộ 4 THƯỚC CHUẨN (`RULERS_CURRENT` §10.1) — `BOOK_EW`

| đơn vị | `wl_ratio` | `tf_5` | `loss_mean` | `conc_5 %` |
|---|---|---|---|---|
| U1 (vị thế) | 1,526 | **−8,815** | 0,000240 | **670,4** |
| U2 (ngày) | 1,235 | **+0,018** | 0,004469 | 98,9 |
| U0 (vòng trước) | 3,276 | −15,721 | 0,000095 | 1117,2 |

⇒ `tf_5` (bỏ top-5 % leg) **chỉ dương ở U2** (+0,018, ~0) và **âm ở U1/U0**;
`conc_5` cực lớn (top-5 % leg mang **670 %** net tại U1) ⇒ **edgeless, lãi nằm ở đuôi**.

### 2.3 4 book con — **CẢ 4 đều (a) FAIL · (b′) FAIL ở CẢ 3 đơn vị**

| object | U1 `n` / `share top-1 %` / `TF25` | U2 `n=1460` / `share top-1 %` / `TF25` | U0 `n` / `share top-1 %` / `TF25` |
|---|---|---|---|
| `funding` | 64 823 · **257,63** · **−26,187** | 40,87 · **−2,991** | 107 754 · 355,42 · −28,057 |
| `dOI` | 66 956 · **381,84** · **−31,255** | 53,90 · **−4,238** | 107 813 · 527,16 · −32,760 |
| `vol` | 56 331 · **209,85** · **−22,518** | 52,14 · **−5,994** | 87 995 · 286,52 · −25,345 |
| `reversal` | 64 159 · **374,84** · **−28,096** | 75,62 · **−5,392** | 108 409 · 537,01 · −31,119 |

---

## 3. CHÊNH GIỮA 2 ĐƠN VỊ (`BOOK_EW`)

| chỉ số | U1 (vị thế) | U2 (ngày) | **chênh U1 − U2** | tỷ số |
|---|---|---|---|---|
| `share top-1 %` | **264,94** | **40,49** | **+224,45 pp** | U1 nặng hơn **6,54×** |
| `TF(25 %)` | **−18,569** | **−2,039** | **−16,530** | U2 dịu hơn **9,11×** |
| mức vượt rào (a) so 15 % | 17,7× | 2,7× | — | — |
| `net/ngày` | +0,10586 % | +0,10586 % | **0** | **giống hệt** |

⇒ **Đơn vị làm ĐỔI ĐỘ LỚN 6,5–9,1× nhưng KHÔNG đổi KẾT LUẬN** (FAIL cả hai).
**giả thuyết "vòng trước FAIL vì áp rào lên đơn vị NGÀY" bị số liệu BÁC**: U0 (vòng trước) có `n = 411 971`
leg **vị thế**, không phải 1 460 ngày.

---

## 4. ĐỐI CHỨNG NGẪU NHIÊN (n=200, seed `20260928`, cùng số vị thế/ngày `nlong=17`)

| đơn vị | net/ngày (mean / p95) | `TF(25 %)` (mean) | (a) PASS | (b′) PASS |
|---|---|---|---|---|
| U1 (vị thế) | **−0,0331 %** / −0,0028 % | −28,04 | **0/200** | **0/200** |
| U2 (ngày) | **−0,0331 %** / −0,0028 % | −3,75 | **0/200** | **0/200** |

- **`BOOK_EW` net `+0,1059 %/ngày` > control `−0,0331 %`** (khớp `RESULT_BOOK_COST2`) ⇒ book **hơn** control
  về net và **cả về `TF25`** (U1: −18,6 vs −28,0; U2: −2,04 vs −3,75) — nhưng **CẢ HAI đều FAIL rào**.
- **`share top-1 %` của control KHÔNG đo được**: chỉ **5/200** rep có `Σ>0` (chuỗi ngẫu nhiên market-neutral
  gần như luôn âm ròng) ⇒ `share top-1 %` **vô nghĩa khi `Σ ≤ 0`** ⇒ ghi **N/A** (đúng pre-reg §3).

---

## 5. TRẢ LỜI 4 CÂU (bắt buộc)

**(1) Rào (a)/(b′) đạt hay không ở CẤP VỊ THẾ? Ở cấp NGÀY?**
→ **KHÔNG ở cả hai.**
· **Cấp VỊ THẾ (U1, đơn vị đúng):** (a) `share top-1 % = 264,94 %` CI raw **[192,56; 415,80]** ⇒ **FAIL**
  (vượt 15 % tới **17,7×**); (b′) `TF25 = −18,569` CI raw **[−19,590; −17,628]**, `p(>0)=0,000` ⇒ **FAIL**.
  **Cả 4 book con FAIL y hệt** (bảng §2.3). `q* = 0,5 %` ⇒ gần như **không có đuôi bền**.
· **Cấp NGÀY (U2):** (a) `40,49 %` CI raw **[28,26; 58,05]** ⇒ **FAIL** (CI **hoàn toàn** > 15 %);
  (b′) `TF25 = −2,039` CI raw **[−2,467; −1,637]**, `p(>0)=0,000` ⇒ **FAIL**.

**(2) Chênh giữa 2 đơn vị? Vòng trước FAIL có phải vì sai đơn vị?**
→ Chênh **LỚN**: `share top-1 %` **+224,45 pp** (264,94 vs 40,49; U1 nặng hơn **6,54×**);
`TF25` **−16,530** (U2 dịu hơn **9,11×**); `net/ngày` **giống hệt** (+0,10586 %).
⇒ **KHÔNG phải vì sai đơn vị**: FAIL ở **mọi** đơn vị.
Và **quan trọng hơn**: **vòng trước KHÔNG dùng đơn vị NGÀY** — `run_trackb.py:282` gọi `rao(legs)` với
`legs` = **vị thế (coin-ngày) + entry phí**, `n = 411 971` (tái lập **chính xác** ở §1/U0). Nghi vấn
*"rào bị áp lên chuỗi PnL theo NGÀY (≈14 ngày cho top-1 %)"* **không đúng với code đã ghi**.

**(3) Rào gốc viết cho đơn vị nào? Có cần chỉnh cách áp cho book không?**
→ **Rào gốc viết cho "LỆNH" = một leg / một vị thế**, **KHÔNG phải ngày**:
· `RULERS_CURRENT.md` **§7**: *"**(a) RÀO CỨNG MỚI:** `%PnL đến từ top-1 % **lệnh** ≤ 15 %`"*;
· **§8**: *"**(b′) … bỏ TOP-50 % **lệnh** ⇒ PnL vẫn phải DƯƠNG … gần với "**lệnh** TRUNG VỊ phải có lãi"
  (median **leg** > 0)"* (sau hạ 25 % ở §12);
· §9 dùng *"bỏ top-5 % **leg**"* + `q*` trên **T100/GD92/KEEPLEG0/T170** — pipeline **arm/sim**, 1 lệnh = 1 leg.
⇒ **Đơn vị thi hành đúng cho book cross-section = U1 (cấp vị thế)**. **Có** cần chỉnh **cách áp**:
**quy ước hoá đơn vị** (xem §6) để (i) hết nhập nhằng "leg = vị thế hay entry phí", (ii) **cấm** phán rào
bằng cấp ngày (quá thô, kết luận lệch 6,5–9,1×, **có thể che mất tập trung đuôi**).

**(4) Track B có đạt rào không ⇒ có được lên bước 2?**
→ **KHÔNG đạt rào** (a) và (b′) ở **đơn vị đúng (U1)** ⇒ theo **luật pre-reg §6.4/§6.5**,
**KHÔNG đủ điều kiện lên bước 2**. Cần nói rõ để khỏi hiểu sai: `RESULT_BOOK_COST2` nói **"MỞ LẠI"**
theo nghĩa **"không NULL vì CHI PHÍ"** (net CI **dương**, đã tái lập `+0,10586 %/ngày`) — **KHÔNG** phải
"đạt rào". Rào **(a)+(b′)** vẫn **chặn**: lãi **tập trung ở đuôi** (top-1 % vị thế = **265 %** net;
bỏ 25 % vị thế tốt nhất ⇒ **−18,6** trên tổng **+1,55**).

---

## 6. QUY ƯỚC ĐƠN VỊ ĐỀ XUẤT (để không lặp lại lỗi định nghĩa)

1. **Rào (a)/(b′) phải ghi ĐƠN VỊ ngay trong tên** — chuẩn hoá:
   `share top-1 % **theo LỆNH (vị thế)**` và `TF(25 %) **theo LỆNH (vị thế)**`.
2. Với **book cross-section**: **1 lệnh = 1 ô `(coin, ngày)`** (long/short **gộp**, PnL **ròng** gồm phí
   của chính nó, `Σlegs = net`). **KHÔNG** tách entry phí thành leg riêng; **KHÔNG** nhân 4 book con rồi
   `concat` (đó là định nghĩa U0 — chỉ dùng để **đối chiếu**, không để phán).
3. **KHÔNG** phán rào bằng **cấp ngày**: 1 ngày gộp ~35 vị thế ⇒ làm **nhòe** tập trung đuôi
   (minh chứng: (a) 40,5 % vs 264,9 % — **cùng một PnL**).
4. Bộ **4 thước chuẩn** (`wl_ratio · tf_5 · loss_mean · conc_5`) + `q*`/`asym`/`winrate`/`median`
   **cũng theo đơn vị vị thế**.
5. Khi `Σlegs ≤ 0`: **`share top-1 %` = N/A** (không đọc thành PASS) — như đối chứng ngẫu nhiên ở §4.

---

## 7. MỤC NÀO BỎ + LÝ DO

| mục | quyết định | lý do (số đo) |
|---|---|---|
| Giả thuyết *"vòng trước áp rào lên đơn vị NGÀY"* | **BỎ** | tái lập U0 **chính xác** (`n = 411 971` leg **vị thế**, `share top-1 % = 413,066`), không phải 1 460 ngày |
| Kỳ vọng *"đổi sang đơn vị vị thế là Track B đạt rào"* | **BỎ** | U1 **harsh hơn** U2: (a) 264,94 % (**17,7×** ngưỡng) · (b′) −18,57 (`p(>0)=0`) |
| Việc **đọc (a) ở cấp ngày** như một "đơn vị hợp lệ" | **BỎ** (giữ làm **đối chiếu**) | cùng PnL: (a) `40,49 %` (U2) vs `264,94 %` (U1) ⇒ 6,54× — dễ **ngộ nhận** |
| Định nghĩa U0 (tách **entry phí** thành leg + `concat` 4 book) | **BỎ** (giữ làm **đối chiếu**) | làm **phồng** `n` (411 971 vs 142 406) & **méo** phân vị; (a) 413 % vs 265 % |
| Kết luận Track B *"không NULL vì chi phí"* | **GIỮ** | net `+0,10586 %/ngày` (khớp `RESULT_BOOK_COST2`), `Σlegs = net` ở cả 3 đơn vị |
| Rào **(a)/(b′)** và *"KHÔNG deploy"* | **GIỮ** | FAIL ở **mọi** đơn vị; `p(TF25>0) = 0,000` |
| *"Được lên bước 2"* | **HẠ xuống KHÔNG đạt** (theo luật rào) | pre-reg §6.4/§6.5: đạt rào ở U1 là điều kiện |

**Ghi chú kỹ thuật:** hằng số **có hướng `0,112 %/vòng`** (không phải `0,757 %` cũ — đã bác ở `623f040`);
stop `−10 %` + trượt `+0,5 %`, hysteresis `band = 2`, top-200, nhịp ngày, `T0D..T1D` = 2022-01-01 … 2025-12-30.

---

## 8. SẢN PHẨM + TÁI LẬP

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_RULERS_UNIT.md` | pre-reg, commit **`107d411`** |
| `research/trackb/rulers_unit.py` | đo 3 đơn vị + CI + đối chứng (**~175 s**; panel dựng lại **21 s**) |
| `docs/result/rulers_unit.json` | mọi số + CI (thô + `inflate(8)`) |
| `/tmp/trackb/panel.npz` (45,8 MB) | trung gian, **dọn sau commit** |

```bash
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages python3 research/trackb/build_panel.py
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages python3 research/trackb/rulers_unit.py
```

**Hạn chế:** nhịp NGÀY (00:00 UTC, hold 24h); chi phí có hướng lấy từ mẫu `bookTicker`+`aggTrades`
(14 symbol × 4 ngày — xem `RESULT_BOOK_COST2` §1); mọi kết luận là **mô tả quá khứ DEV**.
