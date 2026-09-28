# PREREG_RULERS_UNIT — CHỐT TRƯỚC **ĐƠN VỊ ĐO** cho Rào (a)/(b′) áp lên Track B

Ngày: **2026-09-28**. File này **chốt TRƯỚC** khi đo bất kỳ số nào của vòng này
(sau đó **không sửa thiết kế**; nếu lệch phải khai riêng như mọi pre-reg khác).

**Bối cảnh.** `RESULT_BOOK_COST2` (`623f040`): dưới chi phí CÓ HƯỚNG ~`0,112 %/vòng`,
`BOOK_EW` net **+0,1059 %/ngày**, CI95 `[+0,0615 %, +0,1502 %]` ⇒ Track B **MỞ LẠI**.
**Nhưng** Rào (a) `share top-1 % ≤ 15 %` và (b′) `TF(25 %) > 0` **FAIL cho MỌI object**.
**Nghi ngờ: sai ĐƠN VỊ ĐO** — chứ không phải sai tín hiệu.

---

## 1. BA ĐƠN VỊ SẼ BÁO (báo CẢ BA — **không** chọn cái đẹp)

| mã | đơn vị | "1 leg" = gì | `n` kỳ vọng |
|---|---|---|---|
| **U1** | **CẤP VỊ THẾ (coin-ngày)** — *đơn vị chính* | PnL **RÒNG** của **một vị thế `(coin i, ngày t)`** = `w_i·s_i + (−w_i·f_i) − fee_i` (`fee_i = 0,5·C_i·|Δw_i|`, `C_i` = chi phí có hướng nhóm thanh khoản, `book_cost2.json` `C["2000"]["k0.5"]`) | ~hàng chục nghìn … trăm nghìn |
| **U2** | **CẤP NGÀY (book)** — *đối chiếu* | PnL **RÒNG cả book trong ngày `t`** = `gross[t] + fund[t] − fee[t]` | **1 460** |
| **U0** | **TÁI LẬP định nghĩa vòng trước** — *chỉ để đo CHÊNH* | `legs` = `concat` (4 tín hiệu) của **(a)** entry PnL-vị-thế `+` **(b)** entry **PHÍ thuần** `−feeamt`, mỗi cái chia 4 — đúng như `run_trackb.py:282` (`rao(legs)`) + `cost2_trackb.py` | ~`412 000` |

### 1.1 Chốt TRƯỚC các lựa chọn định nghĩa (không đổi sau khi thấy số)
1. **Long/short: GỘP là chính** (1 vị thế = 1 leg, dấu do `w_i`). **Tách long / short báo PHỤ** (không dùng để phán PASS/FAIL).
2. **Một vị thế = MỘT leg**, gồm cả **phần phí của chính nó** ⇒ `Σlegs = PnL RÒNG cả kỳ` (đúng bằng tổng mà rào muốn kiểm). **KHÔNG** tách entry phí thành leg riêng (khác U0).
3. **`BOOK_EW`**: leg `(coin i, ngày t)` = **trung bình cộng 4 book con** tại ô đó (`0` nếu tín hiệu đó không giữ). **1 ô `(coin,ngày)` = 1 leg** (không nhân 4).
4. Ngày **không giữ vị thế nào** ⇒ **không có leg nào** (không thêm leg 0) ở U1; ở U2 vẫn là **1 ngày** (giá trị `0`).
5. Cửa sổ: **`T0D..T1D`** = 2022-01-01 … 2025-12-30 (`band = 2`, top-200, nhịp ngày) — **y hệt** `RESULT_TRACKB_STEP1`/`COST2`. **DEV ≤ 2025-12-31**, **không** chạm 2026.

---

## 2. RÀO GỐC ĐƯỢC VIẾT CHO ĐƠN VỊ NÀO (trích `RULERS_CURRENT.md`)

- §7 (owner chốt 26/09 23:11): *"**(a) RÀO CỨNG MỚI:** `%PnL đến từ top-1% **lệnh**` ≤ 15 %"*.
- §8 (owner chốt 26/09 23:17): *"**(b′) RÀO CỨNG:** bỏ TOP-50 % **lệnh** ⇒ PnL vẫn phải DƯƠNG …
  ⇒ gần với **"**lệnh** TRUNG VỊ phải có lãi" (median **leg** > 0)"* — sau hạ về **25 %** (§12, 28/09 15:51).
- §6/§9: bối cảnh con số (*"top-1 % **lệnh** = 24–41 % lãi"*, *"bỏ top-5 % **leg**"*, `q*` tính trên
  **T100/GD92/KEEPLEG0/T170** — các pipeline **arm/sim**, 1 **lệnh** = 1 lần vào/thoát).
- §10.1: bộ 4 thước chuẩn `wl_ratio · tf_5 · loss_mean · conc_5` — đều định nghĩa **theo leg**.

⇒ **Đơn vị gốc của rào = "LỆNH" (một leg / một vị thế)** — **KHÔNG** phải "ngày".
Đơn vị thi hành đúng cho một **book cross-section** = **U1 (cấp vị thế)**.
**U2 (cấp ngày)** chỉ là **đối chiếu** (1 "leg" = 1 ngày ⇒ gộp ~35 vị thế vào 1 quan sát ⇒ **thô hơn**).

---

## 3. CHỈ SỐ BÁO CÁO (định nghĩa GIỐNG NHAU cho cả 3 đơn vị)

Gọi `o = sort(legs, giảm dần)`, `Σ = Σ legs` (`>0` để (a) có nghĩa; nếu `Σ ≤ 0` ⇒ **(a) = N/A**, ghi rõ, **không** đọc thành PASS).

| chỉ số | công thức |
|---|---|
| `share_top1 %` (rào a) | `Σ o[:⌈1 %·n⌉] / Σ × 100` |
| `TF(25 %)` (rào b′) | `Σ o[⌈25 %·n⌉:]` |
| `q*` | bước nhỏ nhất `p ∈ {0,5; 1,0; …}` (bước `0,5 %`) sao cho `Σ o[⌈p·n⌉:] ≤ 0` |
| `asym` | `mean(|leg âm|) / mean(leg dương)` |
| `winrate` | tỷ lệ leg `> 0` |
| `median` | trung vị leg (dự bị §10.1) |
| `wl_ratio` | `mean(leg dương) / mean(|leg âm|)` (= `1/asym`) |
| `tf_5` | `Σ o[⌈5 %·n⌉:]` |
| `loss_mean` | `mean(|leg âm|)` |
| `conc_5` | `Σ o[:⌈5 %·n⌉] / Σ × 100` |

---

## 4. CI — BLOCK BOOTSTRAP **THEO NGÀY** (hợp cho MỌI đơn vị)

- **Khối 10 ngày** (`block = 10`, như `RESULT_TRACKB_STEP1`), **2000 rep**, **seed `20260905`**,
  **`inflate(k) = sqrt(2·ln k)`** với **`k = 8`** (như các vòng trước).
- Với **U0/U1**: resample **các ngày** theo khối ⇒ **gom lại leg của các ngày đó** ⇒ tính lại chỉ số
  (giữ nguyên cấu trúc phân vị trong từng mẫu). Với **U2**: resample trực tiếp chuỗi ngày.
- **Báo**: điểm (toàn mẫu) + **CI raw95** + **CI `inflate(8)`** + `p(>0)` cho `share_top1 %`, `TF25`,
  `asym`, `winrate`, `mean`.

---

## 5. ĐỐI CHỨNG NGẪU NHIÊN — **Ở CẢ HAI ĐƠN VỊ**

Y hệt `RESULT_TRACKB_STEP1` §3: **`n = 200` book chọn coin ngẫu nhiên** (seed **`20260928`**, cùng số
vị thế/ngày), chấm ở chi phí có hướng `0,112 %/vòng`; tính **cả** rào ở **U1** và **U2**
(mean `[p5, p95]` trên 200 rep). Điều kiện "hơn đối chứng" xét ở **cùng** đơn vị.

---

## 6. LUẬT KẾT LUẬN (CHỐT TRƯỚC — không suy diễn sau)

1. **`(a) PASS` tại đơn vị `U`** ⟺ `share_top1 %(U) ≤ 15`. **`(b′) PASS` tại `U`** ⟺ `TF25(U) > 0`.
2. **Đơn vị để PHÁN** = **U1 (cấp vị thế)** — vì rào gốc viết cho **LỆNH** (§2).
   `U2` chỉ để **đo chênh**; **PASS ở U2 mà FAIL ở U1 ⇒ KHÔNG tính là đạt rào.**
3. **"Chênh 2 đơn vị"** = hiệu `share_top1 %(U1) − share_top1 %(U2)` và `TF25(U1) − TF25(U2)` (điểm),
   kèm nhận xét `n` và kết luận **vòng trước FAIL có phải vì đơn vị hay không** (đối chiếu `U0`).
4. **Track B "đạt rào"** ⟺ **PASS cả (a) và (b′) ở U1**.
5. **"Được lên bước 2"** ⟺ (i) **đạt rào ở U1**, **VÀ** (ii) net/ngày CI ngoài 0 phía dương (đã có),
   **VÀ** (iii) không kém đối chứng ngẫu nhiên ở cùng đơn vị.
6. Nếu **không** đạt: **vẫn** báo cáo chênh 2 đơn vị + **đề xuất quy ước đơn vị rõ ràng** cho book
   (mục "quy ước") để các vòng sau không lặp lại lỗi định nghĩa.
7. Mọi kết luận là **mô tả quá khứ DEV**; **không** phải cam kết lợi nhuận.

---

## 7. RÀNG BUỘC (CỨNG)

Thuần **Python offline**, **0 train / 0 sim** · giữ box Oracle **nhẹ** (shadow đang chạy) ·
**KHÔNG** chạm production/`242`/ONNX/LIVE · **KHÔNG** push file dữ liệu · **DEV ≤ 2025-12-31**
(**không** chạm 2026) · file **nhỏ**, dọn ngay · commit **sớm** + **push**.

---

## 8. SẢN PHẨM

`docs/prereg/PREREG_RULERS_UNIT.md` (file này) → `research/trackb/rulers_unit.py` →
`docs/result/RESULT_RULERS_UNIT.md` + `docs/result/rulers_unit.json`.
