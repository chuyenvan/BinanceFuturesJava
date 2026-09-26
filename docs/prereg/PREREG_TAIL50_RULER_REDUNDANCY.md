# PREREG_TAIL50_RULER_REDUNDANCY — RÀO (b′) BỎ TOP-50 % + KIỂM TRÙNG LẶP 17 THƯỚC TAIL-ROBUST

Chốt **TRƯỚC khi đo** (2026-09-26 23:20 GMT+7, sau quyết định owner 23:17). Thuần **Python offline**
trên Oracle; **KHÔNG** train, **KHÔNG** Java/sim, **KHÔNG** chạm production/242/ONNX/LIVE, **KHÔNG** push git.
DEV only: mọi leg **`start <= 2025-12-31 23:59`**, **không đọc 2026**. Code:
`research/analysis/tail50_ruler_redundancy.py`. Kết quả: `docs/result/RESULT_TAIL50_RULER_REDUNDANCY.md`
(+ `docs/result/TAIL50_RULER_REDUNDANCY.json`). Số thô: `/tmp/t50/`. File output **NHỎ** (`df -h /` ~93 %).

## 0. ĐỘNG CƠ (quyết định owner — nguồn chân lý)

> *"cần cứng, chấp nhận làm lại từ đầu. **20 % với tôi vẫn rủi ro lắm**, nếu được để **50 %** rồi không ra
> mới hạ nó xuống."* — owner 26/09 23:17 (`RULERS_CURRENT.md` §8, commit `4afb3e1`).

⇒ **RÀO (b′) = BỎ TOP-50 % LỆNH ⇒ PnL VẪN PHẢI DƯƠNG** (thay rào bỏ-20 %). **Rào (a) giữ nguyên:
`%PnL từ top-1 %` ≤ **15 %**. Vòng trước (`RESULT_RATE_REDUNDANCY.md`, `8ddc173`/`5b18ecb`) đã đo bỏ
5/10/20/50 % nhưng **chưa** đo bước 30/40 % toàn kỳ + **chưa** đo phân rã theo **từng năm**, và **chưa**
kiểm trùng lặp 17 thước tail-robust (`PREREG_TAIL_ROBUST_RULERS.md`, `4660529`).

## 1. ĐỐI TƯỢNG & NGUỒN (khai báo trước, không đổi)

- **Tám biến thể** (đúng vòng trước, `TARGETS` của `rate_redundancy.py`): `KEEPLEG0` · `T100` · `GD92` ·
  `kg0-q995` · `kg0-q998` · `kg0-q999` · `T170` · `kg0-q998-15m`; thư mục tại `/home/ubuntu/kaggle_sim/out`
  hoặc `/home/ubuntu/java/devrun`, dữ liệu `storage/printDone.csv`.
- **Tùy chọn** `sel15`/`sel15-q998`/`sel15-q999`/`all15`: **nếu** có artifact cục bộ thì dùng, **không** có
  thì **ghi `missing`** — **KHÔNG** chạy sim để sinh (phiên khác đang chạy; không block).
- **Thang đo tiền:** mọi thang bất-trị-đuôi tính trên cột **`pnl` (USDT/leg, ròng)** — đúng cột đã dùng
  cho rào vòng trước. Báo **phụ** trên `profit` (% giá) để kiểm độ nhạy.

## 2. VIỆC 1 — RÀO (b′) BỎ TOP-30/40/50 % (định nghĩa chốt trước)

Với vector `P = pnl` của `n` leg, sắp `o = sort(P)` giảm dần. **`TF(x %)` = `Σ o[k:]`**, `k = max(1, ⌈x·n/100⌉)`
⇒ **bỏ `k` leg TỐT NHẤT**. **PASS (b′)** ⟺ `TF(x %) > 0`.

- **Bước đo `x` = {0, 5, 10, 20, 30, 40, 50} %** — **toàn kỳ** và **TỪNG NĂM** (`end.year`, năm có ≥ 5 leg;
  năm < 5 leg ghi `insufficient`).
- **Đồng nhất thức phải kiểm:** `TF(50 %) ≡ Σ pnl của `n−k` leg NHỎ NHẤT` ("nửa dưới", chẵn/lẻ theo
  `k=⌈0,5n⌉`); sai số phải `= 0` trên cả 8 biến thể.
- **`median` PnL/leg** và **`sign%`(pnl>0)** từng biến thể (để khắc rõ `median>0` KHÔNG ⟺ `TF(50%)>0`).
- **Đường cong `q*`:** PnL sau khi bỏ `x %` với `x` = {0,5,10,20,30,40,50}; **`q*` = bước 0,5 % nhỏ nhất**
  làm `TF(x) ≤ 0` (binh pháp vòng trước). Báo bảng giá trị để thấy điểm cắt `TF = 0`.
- **Rào (a):** `share_top1_pct = Σ(k=⌈0,01n⌉ leg tốt nhất)/Σpnl · 100`; **PASS** ⟺ `≤ 15 %`.
- **Bảng PASS/FAIL** cả (a) và (b′) cho 8 biến thể, ở cả 3 bước 30/40/50 %.
- **Khai báo trước kỳ vọng:** theo số đã đo (`5b18ecb`), `TF(50 %) < 0` ở **cả 8** ⇒ dự kiến **(b′) 0/8 PASS**.

## 3. VIỆC 2 — ĐỊNH NGHĨA TRÙNG LẶP CHO 17 THƯỚC TAIL-ROBUST

Bộ 17 thước lấy **nguyên định nghĩa** `PREREG_TAIL_ROBUST_RULERS.md` §5 (`R1..R17`). **Panel = các RUN DEV**
(giống vòng rate: gom mọi thư mục có `storage/printDone.csv`, `n ≥ 30` leg, `start ≤ 2025-12-31`).
**Khối A** = 448 run (mỗi run 1 dòng); **Khối B** = ô `run × năm` (năm ≥ 30 leg).

- **`net` khai báo trước:** `net_leg = pnl / margin` (**lợi suất trên ký quỹ/leg, KHÔNG đơn vị** — khớp tinh
  thần "`net`/leg (phân số)" của prereg gốc, và **loại hiệu ứng quy mô run**). **Khối phụ (độ nhạy):**
  `net_leg = pnl` (USDT) — báo riêng, **không** dùng cho luật.
- **15/17 thước tính được trên run:** `wmean_p1p99` · `wmean_p5p95` · `tmean_1` · `tmean_5` · `median` ·
  `sign_frac` · `tf_1` · `tf_5` · `tf_10` · `conc_1` · `conc_5` · `hhi_gain` · `loss_mean` · `wl_ratio` ·
  `max_loss`. **`ic_wmean`/`ic_med` KHÔNG tính được** trên panel run: cần **điểm đối tượng** căn theo pool
  (cột `pred15m` là **1 feature cố định**, KHÔNG phải điểm đối tượng đang chấm) ⇒ **loại khỏi ma trận, ghi rõ**
  (2 thước này vẫn được vòng `PREREG_TAIL_ROBUST_RULERS` đo trên pool P32).
- **Trùng ĐẠI SỐ (i):** cặp `(u,v)` là hàm affine `u = a·v + b` nếu hồi quy tuyến tính cho **residual
  tương đối ≤ 1e-6** trên **≥ 95 %** run (khối A) ⇒ `v` dư thừa.
- **Trùng THỐNG KÊ (ii):** cặp `(u,v)` đạt nếu **`|Pearson| ≥ 0,9` VÀ `|Spearman| ≥ 0,9`** **trên CẢ HAI
  khối A và B** (đúng luật vòng rate). Báo thêm ngưỡng **≥ 0,99** (mức phụ thuộc gần tuyệt đối).
- **LUẬT CHỌN BỘ CHUẨN TỐI THIỂU (B1–B4, chốt trước):**
  - **B1.** Bộ gồm **2–4 thước**, mọi cặp trong bộ **KHÔNG** trùng theo (i) và (ii).
  - **B2.** Bộ **KHÔNG giao** với `{TSloss %, mP|SM, mP|SL, mMargin}` (đã chốt ở vòng rate) — nếu giao thì bỏ.
  - **B3.** **Ưu tiên** theo `D3` của prereg gốc: `median` > `tf_5` > `wmean_p1p99` > `sign_frac` > `conc_5`
    > `ic_med` > `loss_mean` > còn lại. Khi 2 thước trùng ⇒ **giữ thước ưu tiên cao hơn**, loại thước kia.
  - **B4.** Bộ chọn phải **phủ ≥ 3 khía cạnh**: (a) **vị trí** (median/tf), (b) **tần suất thắng** (sign_frac),
    (c) **độ lớn thua/bất đối xứng** (loss_mean/wl_ratio/max_loss). Nếu bộ 2 thước không phủ ⇒ lấy 3.
- **Danh sách cặp `|rho| ≥ 0,9` và `≥ 0,99`** liệt kê tường minh; cặp trùng (ii) chỉ nêu khi đạt **cả 2 khối**.

## 4. CÂU HỎI CHỐT TRƯỚC (trả lời sau khi đo, KHÔNG đổi)

**(1)** Ở rào **(b′) bỏ-50 %**: biến thể nào **DƯƠNG**? (0 ⇒ nói rõ).
**(2)** **`q*`** từng biến thể + **`median` PnL/leg** + giá trị `TF(x)` tại 30/40/50 %.
**(3)** Cặp thước tail-robust nào **TRÙNG** (bảng `rho`) ⇒ **bộ chuẩn tối thiểu đề xuất** (2–4 thước).
**(4)** Dưới rào **(a)+(b′)** có biến thể nào **đủ go-live** không; nếu **không** thì **mắt xích nào phải
đổi** (cấu trúc lại / luật thoát / nhóm lệnh) — ngắn, chỉ dựa trên số.

## 5. RÀNG BUỘC (CỨNG, chốt trước)

Không train, không sim/Java, không chạm 242/ledger/ONNX/đường LIVE, không push git. DEV `<= 2025-12-31`,
không đọc 2026. Output tool **NHỎ**; JSON vài trăm KB. Không chạy lại vòng `PREREG_TAIL_ROBUST_RULERS`
(phiên khác đang chạy) — chỉ **đọc** artifact nếu đã có.
