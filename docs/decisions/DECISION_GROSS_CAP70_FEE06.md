# DECISION_GROSS_CAP70_FEE06 — Trần gross **70 % (CỨNG)** + phí chuẩn **0,6 %/vòng** (owner chốt 26/09 05:35)

Trạng thái: **CHỐT** (quyết định owner, nguồn duy nhất — không diễn giải lại).
Bằng chứng: `docs/result/RESULT_CAP70_FEE06.md` · pre-reg `docs/prereg/PREREG_CAP70_FEE06.md` (`6f37caa`).
**Thay thế** các mốc cũ ở `docs/runbooks/RISK_APPETITE.md` (đã merge, giữ nguyên phần cũ).

## 1. Hai con số được chốt

| # | quyết định | giá trị | **THAY THẾ** |
|---|---|---|---|
| 1 | **Trần gross exposure** | **70 % equity — CỨNG / binding** | "quan sát **54–58 %**" (mốc mô tả, **không** phải trần) |
| 2 | **Phí chuẩn nghiên cứu** | **0,6 %/vòng** | **0,8 %/vòng** (`RATE_FEE 0,002 + 2×SLIPPAGE 0,003 = 0,008`) dùng ở các vòng trước |

## 2. Hệ quả + số binding (đo trên pool **P32**, 9.657 tick × 32, đường RE, KHÔNG build lại)

- **MỨC:** `break-even fee` của rổ top-K = **1,2006 %/vòng (K=8) → 1,2678 % (K=32)** ⇒ ở **0,6 %** biên an toàn
  **≈ +0,60…+0,67 %/vòng** (`net_coin`), cao hơn mức ở 0,8 % (≈ +0,40…+0,47 %/vòng). Rổ **dương** ở cả 2 mức.
- **`K` (quyết định):** dưới trần 70 %, mọi `Δ` của `K ∈ {10,12,16,32}` vs `K = 8` — cả `net/tick` sau size
  lẫn `net/1đv-gross` — **TRONG CI** ở **cả 3 cách áp trần** và **cả 4 mức phí** ⇒ **không có `K*` đo được**.
  ⇒ **GIỮ `K = 8`** (đúng LUẬT §8 pre-reg — verdict do luật đã commit sinh ra, không chọn post-hoc).
- **Cách áp trần 70 % (BẮT BUỘC cấu hình đúng cách):**
  - **(A) chuẩn hoá theo TB** (`size = 70/gross_TB`): `s = 1,4339` ở `K=8` — **TB = 70 %** nhưng **max VẪN 120,5 %**.
  - **(B) chặn TỪNG TICK** (`size = 70/gross_max`): `s = 0,8333` ở `K=8` — **max = 70,0 % mọi tick**; đổi lại
    TB tụt còn **40,7 %**. Siết theo max **tốn ~42 % net/tick** so với (A).
  - ⇒ **Trần 70 % là ràng buộc BUỘC CO, không phải cho phép nới**: `gross_max(K=8) = 84 % > 70 %` ⇒
    dưới cách (B), **size ≈ 0,83× hiện hành** (≈ `1,67 %` equity/lệnh thay vì `2,0 %`).
- **`Δ` alpha xếp hạng ≡ 0 độc lập với phí** (đại số + kiểm bằng số): `Δ(f=0,004) = Δ(f=0,006) = Δ(f=0,008)`
  trên **24/24 cặp** model-vs-model (lệch `0,00e+00`); ở `f = 0,006`, **0/12 cặp** ngoài CI ⇒ **phí 0,6 % KHÔNG
  cứu được `Δ = 0`**. Kiểm hợp lệ: `A45−45deploy = +0,00035` (TRONG CI), `V5−V1 = −0,00018` (TRONG CI).

## 3. Vì sao `Δ` bất biến theo phí (đại số — để không ai "thử lại với mức phí đẹp hơn")

Phí là **hằng số mỗi vòng** ⇒ trên **cùng tập (tick, coin)** ghép cặp:
`Δnet(f) = mean[(gross_a − f) − (gross_c − f)] = mean[gross_a − gross_c] = Δgross` — **độc lập `f`**.
Phí chỉ đổi **MỨC** (`net = gross − f`), **KHÔNG** đổi **`Δ`** giữa hai mô hình trên cùng rổ.
Chỉ khi **số lệnh đổi theo `K`** (quét `K`) thì phí **không** triệt tiêu ⇒ mới phải tính lại — và kể cả vậy
vẫn **trong CI** ở mọi mức phí.

## 4. Giới hạn (đọc kèm — chống over-claim)

Con số gross là **quy đổi POST-HOC neo `2,0 %/lệnh` TRÊN COIN PHÂN BIỆT**; bản neo trên **số vị thế `e_t`**
cho `K=8` = **821 %** (vô lý) ⇒ chỉ **tỉ lệ giữa các `K`** là đọc được. **KHÔNG** mô hình hoá de-dup live /
DCA nhiều chân / trần size·notional / funding. `net/tick` tuyệt đối là **MÔ HÌNH**, không phải equity LIVE.
**KHÔNG** chạm ONNX/LIVE/2026/`HoldoutSeal`.

## 5. Việc phải làm khi triển khai trần 70 % (chưa làm ở vòng này)

1. Cấu hình chọn cách áp trần: **(A)** hay **(B)** — khuyến nghị **(B)** (mọi tick ≤ 70 %) kèm `size ≈ 0,83×`.
2. Thêm guard gross-exposure (tương tự `CONC_CAP_PERCOIN_*`) + **prove binding** bằng sim **shadow** (không LIVE).
3. `CONC_CAP_PERCOIN_PCT = 0,15` **giữ nguyên** — nới `K` **không** làm xấu trần 1-coin (tỉ trọng ≈ `1/số coin
   phân biệt`: 4,1 % → 3,0 % khi 8 → 12) ⇒ ràng buộc bind là **gross**, không phải conc.
