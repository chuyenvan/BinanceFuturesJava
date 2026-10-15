# SHADOW2 vs SIM — dry-run 2026-10-15 (QUEUE_1015 P3)

Pre-reg thước/luật: `docs/prereg/PREREG_SHADOW2_PROMOTION.md`. Script: `research/shadow/compare_shadow2.py`.

## Trạng thái: **SCRIPT XONG, DRY-RUN BLOCKED** (lý do ở §3)

## 1. Đã làm
- `research/shadow/compare_shadow2.py` — so lệnh paper `shadow-c3b` (`~/shadow_c3b/ledger.csv`, CHỈ ĐỌC) với sim cùng cấu hình (K24 + `GATE_QUOTA_SKIP_WHEN_FULL=true`, chi phí vào OFF).
  - Chuẩn hoá symbol (bỏ hậu tố USDT/USDC/BUSD), thời gian shadow epoch-ms UTC → GMT+7 để khớp `start` của sim.
  - Khớp cùng symbol, phút vào lệch ≤ `--tol-min` (mặc định ±1′), greedy 1-1.
  - Loại cửa sổ KHÔNG đạt chuẩn `2026-10-12 09:06 → 2026-10-15 14:49` (mặc định `--drop-excluded true`).
  - Xuất: `n_shadow`, `n_sim`, `matched`, tỉ lệ khớp 2 phía, chênh giá vào (median/mean/maxabs), chênh PnL, **lệnh một-bên + lý do**.
- Smoke: parse đúng cả 2 định dạng — shadow ledger 18 lệnh; sim `printDone.csv` (gqsf-a1) 3 541 lệnh.

## 2. Số đo trên ledger hiện có (2026-10-15 ~12:15 +07)
`~/shadow_c3b/ledger.csv` chỉ có **18 lệnh**: **17 lệnh cùng phút `2026-10-08 22:20 +07`** (burst) + **1 lệnh `2026-10-13 22:24 +07`** (USUSDT). `legs.csv` 27 dòng; `open_positions.csv` 7 vị thế mở đều mở lúc `2026-10-08 22:20`.

## 3. Vì sao DRY-RUN (10-11 → 10-12 09:00) không chạy được — BLOCKED
1. **Shadow vắng lệnh trong cửa sổ dry-run:** lọc `--start 2026-10-11 --end 2026-10-12T09:00` ⇒ **0 lệnh shadow** (ledger chỉ có lệnh ở 10-08 22:20 và 10-13 22:24) ⇒ **không có gì để so**. Cửa sổ 10-08→10-09 (17 lệnh) nằm ngoài dry-run đã khai trước; muốn dùng phải có pre-reg riêng.
2. **Chưa có sim cùng kỳ:** sim K24+skipFull trên Vision cho 10-10→10-12 cần (a) bundle ticker dựng từ Vision (exporter `ho4p1-jar-exp` sha `99c5f040`, docs `HO4_P1.md` §S1) — **chưa dựng**, và (b) chạy 1 kernel Kaggle — nhưng template sim khai `sim-jar-nsel` (jar `b7c89f09`) **đã bị xoá khỏi Kaggle** (xem `docs/data/KAGGLE_REQUIRED.md` §P1-RESIDUAL) ⇒ kernel không chạy được tới khi khôi phục dataset.
3. **Tuần thật** (10-15 15:00 → 10-22) bắt đầu **sau** thời điểm này ⇒ báo cáo tuần chưa đến hạn.

## 4. Việc cần để mở khoá
- Đẩy lại `chuyendinh/sim-jar-nsel` (jar `b7c89f09`, có sẵn `~/src_wt_nsel/target/binance-java-sdk-1.2.4.jar`, sha trùng) — **chờ owner xác nhận** (owner vừa dọn Kaggle).
- Dựng bundle ticker Vision cho cửa sổ cần đo (10-10→10-22, lead-in) theo exporter HO4.
- Sau 10-22 (hoặc đủ ≥4 tuần theo pre-reg) chạy `compare_shadow2.py` và viết `docs/result/SHADOW2_WEEK_<n>.md`.

## 5. ĐIỀU TRA CỤM 17 LỆNH `2026-10-08 22:20 +07` (MASTER 10-15 14:19) — **KHÔNG phải lỗi khởi động**

Nguồn (CHỈ ĐỌC): `~/shadow_c3b/app/logs/full.log` (39 MB), `~/shadow_c3b/ledger.csv`, `legs.csv`, `open_positions.csv`.

### 5.1 Gate lúc đó: **ARMED**, không phải fallback base
- Khởi động 10-08 **14:49:10**: `[GATE-RATIO] LIVE nạp buffer: size=230544 firstTs=20261001 13:00 (warm-up=armed)` ⇒ gate nạp buffer đã persist (≥7 ngày dữ liệu sạch từ 2026-10-01 13:00) ⇒ **armed**, KHÔNG rơi vào `fallback base`.
- Trong giờ có cụm: `buffer=240888` (22:01) → `242328` (23:01) — **tăng đơn điệu, không reset, không nạp lại**. Dòng `[GATE]` có `thr=[0.02280..0.02727]` (khoảng theo từng ứng viên, KHÔNG phẳng `base=0.008`) ⇒ đúng nhánh armed.
- Chỉ tới **10-12 11:13** gate mới hỏng persist (`CRC32 lệch`) → seed lại từ 10-08 14:49 ⇒ `warm-up=chưa đủ 7d -> fallback base`. Trước đó (gồm 10-08 22:20) luôn armed.
- `q_t = 0.006205` (hằng số, in mỗi giờ từ 15:01→23:01 ngày 10-08; đổi 0.009209 từ 10-09 00:01).

### 5.2 Cùng tick? — **CÓ, cùng đúng 1 tick**
- 17 lệnh ledger đều `ts_entry = 1791472800000` = **2026-10-08 15:20:00 UTC = 22:20:00 +07**.
- `legs.csv` có **24** dòng cùng tick đó; `open_positions.csv` 7 vị thế còn mở cũng cùng tick ⇒ **24 chân/ứng viên vào cùng 1 tick** (17 đã chốt vào ledger, 7 còn mở).
- Log: `[GATE] … n_pass=24 u=0.3505` tại tick `1791472800000`; tick NGAY TRƯỚC (`1791472740000`, 22:20:06) `n_pass=0`, tick SAU (22:23) `n_pass=0`.
- Dòng gate theo giờ: `22:01 … pass=0` → `23:01 … pass=35` ⇒ **chỉ duy nhất giờ 22:01→23:01 ngày 10-08 có pass>0** (mọi giờ khác pass=0).

### 5.3 Dấu hiệu khởi động lại? — **KHÔNG**
- `MainClass:` (JVM start) gần nhất TRƯỚC cụm: **10-08 14:49:10** (mở đầu log). Kế tiếp: **10-09 02:49:32**. ⇒ **không có restart quanh 22:20** (cụm cách lần start 7,5 giờ).
- Buffer gate **tăng đơn điệu** suốt 10-08 (không rỗng, không reset). Không có dòng `seed lại`/`fallback base` trước 10-12.

### 5.4 Cơ chế thật của cụm
- Predictor **mức THỊ TRƯỜNG** `return15M` nhảy vọt tại tick `1791472800000`: `Predict: {"return15M":0.03045}` (3,05%) — so tick trước `0.01478`, tick sau `0.02267`.
- Đúng lúc thị trường sập mạnh: `DownAvg15M −4.146%`, `btcRate15M −1.071%` (22:21) ⇒ model dự báo "bật lại" 3,05% cho 15M kế tiếp.
- `AIRejectFilter.evaluate` so `pred15M (3,05%) ≥ thr` cho **mọi** ứng viên ⇒ toàn bộ top-K qua gate một lượt: lý do log `✅ AI PASS … Reason: PERFECT: 15M(3.05%)` cho cả 24 symbol (OGN, RLC, LYN, …, EDU), khớp `[GATE] n_pass=24`.
- Đây là **hành vi thiết kế** (gate momentum mức thị trường, K24): một cú spike p15 thị trường ⇒ vào cả rổ top-K cùng tick.

### 5.5 KẾT LUẬN
> Cụm 17 lệnh (thực ra **24 chân** cùng tick) `2026-10-08 22:20 +07` **KHÔNG phải lỗi khởi động (startup bug)**:
> gate đang **ARMED** (buffer ≥7d, `q_t=0.006205`), **không restart JVM, không buffer rỗng**; cụm là do **spike p15 thị trường = 3,05% trong 1 tick lúc thị trường sập −4,1%** ⇒ `n_pass=24` (toàn top-K) do thiết kế K24 + gate momentum mức thị trường.
> Ghi chú rủi ro (không kết luận lỗi): cụm khiến **24 vị thế mở cùng lúc** ⇒ cần xét trần đồng thời (concentration) — tách khỏi câu hỏi "startup bug".
