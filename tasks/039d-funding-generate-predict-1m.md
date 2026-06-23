---
id: 039d
status: DONE
owner: CCD
depends_on: [039a, 039c]
touches_live_process: false
writes_242_data: false
resource: kaggle + 226
kaggle_slots: 1
checkpoint: true
max_retry: 2
report: docs/reports/039d.md
require_review: true
---

# TASK-039d: Generate selector predict MỖI PHÚT (tập đã filter) → set chunk-NGÀY + verify reader

## Mục tiêu
Bản 039c gốc predict ở **lưới 15m** → set `funding_selector_pred_v1` (chunk-THÁNG, đã DONE).
Giờ cần bản **MỖI PHÚT của tập đã filter** (Tool1 vốn có per-phút; chỉ cần bỏ ép grid 15m), nạp vào
set MỚI **chunk-NGÀY** `funding_selector_pred_1m`, rồi VERIFY reader đọc khớp (chuẩn bị backtest).

> Vì sao chunk-NGÀY: per-phút ~15x dày hơn 15m → chunk-tháng vỡ "Record too big". Bắt buộc dùng
> `writeMetricMapDay226`. Xem `docs/DATA_CHUNKING_STANDARD.md`.

## Tiền đề ĐÃ ĐO (không cần làm lại)
- Tool1 (`ff_*.bin.gz`) ĐÃ chứa dữ liệu **mỗi phút** của tập lọt EntrySignalFilter (đo 202101:
  khoảng cách ts phổ biến = 1 phút, chỉ 6.7% rơi đúng lưới 15m). → chỉ cần `GRID=0` trong generate.
- `ml/funding_selector/generate_predict.py` ĐÃ sửa: thêm env `GRID` (mặc định `0`=mỗi phút;
  `1`=ép 15m như cũ). KHÔNG cần sửa thêm code generate.
- Tool nạp ĐÃ viết: `ExportSelectorPred1mToAerospike` (dùng `writeMetricMapDay226`, set mặc định
  `funding_selector_pred_1m`). Jar đã build (shaded, 2026-06-22 20:34).

## PHẦN A — Kaggle generate per-phút (CCD chạy, harvest TẠI CHỖ — KHÔNG headless)
> ⚠️ `claude -p` headless đẩy kernel rồi thoát, KHÔNG harvest được. CCD phải poll tới khi kernel
> DONE rồi mới tải — đây là lý do giao CCD chứ không phải supervisor headless.

1. Nhân bản pipeline 039c gốc (kernel `chuyendinh/funding-generate`): input giữ NGUYÊN
   — dataset Tool1 (`ff_*.bin` 66 tháng) + `chuyendinh/funding-model-v1` (4 .ubj + train_meta)
   + OI (`oi_percoin_full.bin`). Chỉ khác: đặt biến môi trường **`GRID=0`** khi gọi
   `generate_predict.py` (mặc định đã là 0, nhưng set tường minh trong kernel cho rõ).
   OUT_DIR ghi `predict_YYYYMM.bin` (giờ mỗi phút → mỗi file lớn ~15x bản 15m).
2. Push kernel, **poll tới khi COMPLETE** (1 kernel loop 66 tháng; per-phút nặng hơn — có thể chạm
   12h limit. Nếu chạm: chia 2 nửa tháng hoặc bật RESUME=1 + chạy lại, KHÔNG bỏ dở).
3. Đóng gói output thành dataset Kaggle MỚI `chuyendinh/funding-predict-1m-v1` (KHÔNG đè
   `funding-predict-v1` của bản 15m).
4. Spot-check trước khi đóng: 1 tháng (vd 202206) phải có số dòng ~15x bản 15m tương ứng;
   p∈[0,1]; record 26B; BTC ts khoảng cách ~1 phút (không phải 15m).

## PHẦN B — Tải về 226 + nạp set chunk-NGÀY (CCD chạy trên 226)
SSH 226: `ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226`
(noise filter: `| grep -avE "post-quantum|store now|upgraded|openssh"`). Jar đã ở 226
`/home/chuyennd/java/simulator/binance-futures-convert.jar` (hoặc scp bản mới nhất nếu cần).

1. Tải predict-1m về 226 thư mục RIÊNG (không đè bản 15m):
   `kaggle datasets download chuyendinh/funding-predict-1m-v1 -p /home/chuyennd/java/simulator/predict_1m/ --unzip`
   (chạy TRÊN 226 — Kaggle không tới 242). Copy `symbol_map.csv` vào `predict_1m/` nếu chưa có.
2. **Smoke 1 tháng trước** (an toàn chunk-ngày): `java -Xmx11g -cp <jar>
   com.binance.chuyennd.research.ExportSelectorPred1mToAerospike /home/chuyennd/java/simulator/predict_1m
   /home/chuyennd/java/simulator/predict_1m/symbol_map.csv funding_selector_pred_1m smoke`
   → PHẢI **0 chunk-loi** (nếu "Record too big" xuất hiện → SAI, báo ngay; chunk-ngày đáng lẽ an toàn).
3. Nếu smoke OK → chạy full (bỏ `smoke`), nền (`setsid ... </dev/null >log 2>&1 &`), poll tới DONE.
   Log cuối phải: `DONE nap -> set funding_selector_pred_1m (chunk-NGAY) | tong N rec | 0 chunk-loi`.

## PHẦN C — VERIFY reader khớp (mục tiêu chính: chuẩn bị backtest đọc format mới)
1. Đọc lại 1 symbol bằng `getMetricMapDay226("funding_selector_pred_1m","p24h","BTCUSDT")`:
   - viết/ chạy 1 tool kiểm nhanh (mẫu `CheckMetricSetPoints` nhưng gọi bản Day) → đếm số điểm.
   - Đối chiếu số điểm BTC đọc-ra == số dòng BTC (symId=1) trong file predict_1m gốc (đếm bằng python).
     KHỚP = reader chunk-ngày đúng.
2. Đối chiếu GIÁ TRỊ: lấy 5 ts bất kỳ của BTC, so p24h đọc-từ-Aerospike với p trong file .bin. Phải bằng.
3. (Nếu có thời gian) so cùng ts giữa set 15m cũ và set 1m mới: tại các ts rơi đúng lưới 15m, giá trị
   p PHẢI trùng (cùng model, cùng feature) — xác nhận bản 1m chỉ DÀY hơn chứ không lệch giá trị.

## RESULT (CCD ghi vào docs/reports/039d.md)
- Số dòng tổng bản 1m vs bản 15m (kỳ vọng ~10-15x).
- Số record + dung lượng set `funding_selector_pred_1m` (chunk-ngày).
- `0 chunk-loi` xác nhận.
- Verify B-C: số điểm BTC khớp file? 5 giá trị mẫu khớp? 15m-grid trùng giá trị set cũ?
- Ghi rõ bước nào cần user (nếu kernel chạm 12h limit phải chia).

## Lưu ý
- KHÔNG đụng set 15m cũ `funding_selector_pred_v1` (giữ nguyên để so sánh).
- KHÔNG đụng v5/v6 (đã bỏ).
- Build Java ở LOCAL rồi scp (226 không tự compile). Jar hiện đã đủ tool — chỉ scp nếu sửa thêm.
- Mọi log/output trên 226 ghi nơi có sẵn dung lượng; KHÔNG ghi lung tung ngoài simulator dir.
