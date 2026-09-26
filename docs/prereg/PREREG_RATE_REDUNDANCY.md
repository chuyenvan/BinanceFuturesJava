# PREREG_RATE_REDUNDANCY — KIỂM TRÙNG LẶP THANG ĐO (tầng B) + TEST RÀO MỚI (a)/(b)

Chốt **TRƯỚC khi đo** (2026-09-26 23:2x GMT+7). Thuần **Python offline trên Oracle**; **KHÔNG** train,
**KHÔNG** Java/sim, **KHÔNG** chạm production/242/ONNX/đường LIVE, **KHÔNG** push git. DEV only:
mọi dữ liệu **`<= 2025-12-31`**, **không đọc 2026** (holdout nguyên vẹn).
Code: `research/analysis/rate_redundancy.py`. Kết quả: `docs/result/RESULT_RATE_REDUNDANCY.md`
(+ `docs/result/RATE_REDUNDANCY.json`). Sao lưu số thô: `/tmp/rr/` (xoá sau khi xong).
**Không** chạy lại vòng `PREREG_TAIL_ROBUST_RULERS.md` (phiên khác đã chốt; nếu artifact của nó đã
có thì dùng lại, không tính trùng).

## 0. Động cơ (số đã đo — KHÔNG diễn giải lại)

- Luật bằng chứng hiện hành (`docs/analysis/RULERS_CURRENT.md` §6): **"≥ 2 rate ngoài CI"** vs **cả 2**
  đối chứng (block-72h, 2000 rep, seed 20260905, `inflate(k)`, ≥3 seed).
- Owner 26/09 23:11 (§7 cùng file): (a) **`%PnL đến từ top-1% lệnh ≤ 15%`**; (b) **bỏ top-20% lệnh
  ⇒ PnL vẫn phải DƯƠNG**; (c) **hạ cấp thang *mean-based*** về **báo cáo** + **kiểm trùng lặp rate**.
- Roài đã biết (`docs/result/RESULT_FRAGILITY_N.md` §0.3): `share top-1%` = **25,9% (T170) · 40,9%
  (T100) · 37,8% (GD92)**; bỏ top-5% ⇒ PnL **ÂM** (T100/GD92).
- **RỦI RO CỐT LÕI:** nếu 2 rate **trùng/phụ thuộc đại số** ⇒ luật *"≥2 rate"* **KHÔNG** còn là **2
  bằng chứng độc lập** ⇒ phải siết lại.

## 1. CÂU HỎI CHỐT TRƯỚC (trả lời sau khi đo, KHÔNG đổi luật)

**(Q1)** Trong 7 thang tầng B (`n` · `win%` · `TSloss%` · `mP|SM` · `mP|SL` · `meanP` · `mMargin`),
cặp/nhóm nào **trùng đại số** (một rate là **hàm xác định** của các rate kia)?
**(Q2)** Cặp nào **trùng thống kê** (`|rho| ≥ 0,9` cả Pearson & Spearman)?
**(Q3)** Bộ rate tối thiểu (2–4) **KHÔNG trùng** để luật *"≥2 rate"* = **2 bằng chứng độc lập** là gì?
**(Q4)** Rào mới (a) `≤15%` và (b) bỏ-top-20% **>0**: biến thể nào PASS? (dự kiến: **0**) — nếu 0 ⇒
**nói rõ: dưới rào mới KHÔNG cấu hình nào đủ điều kiện go-live**.

## 2. NGUỒN DỮ LIỆU (dùng lại, KHÔNG build lại)

- `printDone.csv` của mọi run **đã có** dưới `/home/ubuntu/kaggle_sim/out/<tag>/storage/` **và**
  `/home/ubuntu/java/devrun/<tag>/storage/`. Chỉ nhận run có cột `profit` · `status` · `pnl` ·
  `margin` · `start` · `end` · `sym` **và** `n_leg >= 30` sau lọc DEV.
- Lọc DEV: `start <= 2025-12-31 23:59`; **bỏ** leg `start >= 2026-01-01`. Ghi rõ số leg bị bỏ.
- Cột dùng: `profit` = **% giá** (`100·(exit−entry)/entry`, đổi dấu theo `side`) — nguồn của `win%`,
  `TSloss%`, `mP|SM`, `mP|SL`, `meanP`; `pnl` = **USDT** net (nguồn của mọi thang TIỀN, gồm rào a/b).
  **KHAI BÁO TRƯỚC:** rào (a)/(b) đo trên cột **`pnl` (USDT)** — đồng nhất với
  `RESULT_FRAGILITY_N.md` §0.3; **báo thêm** bản `profit`-weighted làm kiểm độ nhạy.
- **Không** dùng `net`/`gross` của pool `P32` (khác đơn vị: pool 32 coin/tick), tránh lẫn vòng khác.

## 3. ĐỊNH NGHĨA "TRÙNG LẶP" (CHỐT TRƯỚC — 2 mức)

**(i) TRÙNG ĐẠI SỐ (deterministic):** rate `Y` là **hàm xác định** của bộ `{X}` nếu **có** một đồng
nhất thức `Y = f({X})` cho **sai số tuyệt đối ≤ 1e-4** trên **≥ 95 %** run đủ điều kiện, và sai số
**trung vị ≤ 1e-6**. (Ngưỡng 1e-4 để chừa làm tròn in CSV; đồng nhất thức thật lệch chỉ do làm tròn.)
Các đồng nhất thức **ứng viên kiểm trước** (suy ra từ định nghĩa §2, không phải từ dữ liệu):
- **H1** (kiểm cấu trúc): `status` chỉ có 2 giá trị `STOP_MARKET_DONE` (SM) và `STOP_LOSS_DONE` (SL)
  ⇒ `n_SM + n_SL = n`.
- **H2** (tần suất): `win% ≡ 100 − TSloss%` ⟺ mọi leg `profit>0` ⟺ `status=SM`.
- **H3** (bình quân): `meanP ≡ (1 − TSloss%/100)·mP|SM + (TSloss%/100)·mP|SL`
  (đúng **tự động** nếu H1 đúng, vì SM/SL là **phân hoạch đủ** của `n`).
- **H4** (quy mô): `mMargin` **không** có đồng nhất thức đại số với các rate kia (ghi rõ để không
  over-claim nếu thấy `rho` cao — đó là **thống kê**, không phải đại số).
- **H5** (mẫu số): `win%` · `TSloss%` · `meanP` · `mMargin` **cùng mẫu số `n`**; `mP|SM` mẫu số `n_SM`;
  `mP|SL` mẫu số `n_SL`. Nếu H1 đúng thì `n` + `TSloss%` suy ra `n_SM`, `n_SL`.

⇒ **Kết luận loại:** rate nào dính **bất kỳ** H nào với sai số đạt ngưỡng ⇒ gọi **TRÙNG (đại số)**.

**(ii) TRÙNG THỐNG KÊ:** `|rho| ≥ 0,9` **đồng thời** Pearson **và** Spearman trên **≥ k = 6** quan sát
(khối chính = **run**; khối phụ = **ô run×năm**, ngưỡng **≥ 10** ô). Mức **mạnh** = `|rho| ≥ 0,99`.
Báo **cả hai** khối; **chỉ** gọi trùng thống kê khi **cả hai khối** đều vượt ngưỡng (tránh trùng giả
do nền chung). Ngưỡng phân loại: `|rho| < 0,9` = **ĐỘC LẬP**.

## 4. LUẬT ĐỀ XUẤT BỎ RATE TỐI THIỂU (CHỐT TRƯỚC — deterministic)

**B1.** Kiểm H1–H5. **Bỏ** mọi rate thỏa **trùng đại số** (i), theo thứ tự ưu tiên **giữ rate "gốc
thô"** và bỏ rate **suy ra**: bỏ `meanP` (suy ra từ H3) trước; nếu H2 đúng thì **bỏ `win%`** (giữ
`TSloss%`) — chốt trước: **giữ `TSloss%`** vì nó là **tần suất thua lỗ biên** (kinh tế trực tiếp hơn).
**B2.** Với các rate còn lại, tính ma trận `(|rho|)` trên **cả 2 khối**. **Bỏ** rate nằm trong cặp `(ii)`
theo thứ tự ưu tiên bỏ: **mean-based trước** (`mP|SM`, `mP|SL`, `meanP`) → rồi **size-based**
(`mMargin`) — chốt trước: **giữ rate "độ vênh/kinh tế"**, bỏ rate "bình quân thuần".
**B3.** **Điều kiện đạt:** bộ giữ **2–4 rate** và **mọi cặp trong bộ có `|rho| < 0,9`** ở **cả 2 khối**.
Nếu không đạt, **hạ `k` xuống** mức tối thiểu còn thỏa (báo rõ đã hạ), và **nêu tên** rate phải quay lại.
**B4.** Bộ chuẩn phải phủ **≥ 3 khía cạnh** khác nhau trong 4: **tần suất** (`win%`/`TSloss%`) ·
**độ lớn thắng** (`mP|SM`) · **độ lớn thua** (`mP|SL`) · **quy mô vốn** (`mMargin`).
**B5.** Rate **bỏ khỏi cổng** (nếu có) chỉ **báo cáo**, không dùng làm bằng chứng quyết định.

## 5. TEST RÀO MỚI (a) + (b) — CÁCH ĐO (CHỐT TRƯỚC)

**Rào (a)** `%PnL đến từ top-1% lệnh`: `k1 = max(1, ceil(0,01·n))`; lấy `k1` leg `pnl` **lớn nhất**;
`share1 = 100 · Σ pnl(top k1) / Σ pnl(toàn bộ)`. **PASS ⟺ `share1 ≤ 15,0`**.
**Rào (b)** tail-free: `kq = max(1, ceil(q·n))` cho `q ∈ {5 %, 10 %, 20 %}`; bỏ `kq` leg `pnl` **lớn
nhất**; `TF(q) = Σ pnl(còn lại)`. **PASS(q=20 %) ⟺ `TF(20%) > 0`**. Báo **cả `TF(5 %)`, `TF(10 %)`**.
Báo **giá trị USDT** và **% của Σ pnl gốc**. Tính **toàn kỳ** và **theo từng năm** (`end.year`);
năm có `n_year < 5` ⇒ ghi **"không đủ mẫu"**, không tính PASS/FAIL.

**Đối tượng đo (danh sách chốt trước):** `KEEPLEG0` = `gr-par-kg0` (nền gate-recal, md5 `99e42b75`)
· `T100` = `hn-t100` · `GD92` = `hn-g92` · `kg0-q995` = `gr-kg0-q995` · `kg0-q998` = `gr-kg0-q998`
· `kg0-q999` = `gr-kg0-q999` · `T170` = `t170-x1-2021` (tham chiếu) · `sel15`/`sel15-q998`/
`sel15-q999` = `(nếu có artifact, thêm vào; thiếu ⇒ ghi rõ)`.

## 6. RÀNG BUỘC & OUTPUT

- `df -h /` ~93 % ⇒ file **NHỎ**; log ra file, output tool **THẬT NHỎ**. Không train/sim/push.
- Commit (`KHÔNG` push) ngay sau bước PREREG này; commit lần 2 sau RESULT.
- Toàn bộ số ghi `/tmp/rr/` (xoá sau), JSON nhỏ trong `docs/result/`.
