---
id: 039c
status: CANCELLED
owner: headless
depends_on: [039a]
touches_live_process: false
writes_242_data: false
resource: kaggle
kaggle_slots: 1
checkpoint: true
max_retry: 2
report: docs/reports/039c.md
require_review: true
---

# TASK-039c: Generate funding predict SET (per-tháng) để ốp backtest

## Mục tiêu
Tiền-tính P(chạm +6%) cho MỌI entry-point trên toàn lịch sử, xuất ra SET per-tháng để backtest/WFO
đọc sẵn (không phải predict realtime mỗi run). DÙNG LẠI feature đã có (Tool1 + OI trên Kaggle) —
**KHÔNG export lại feature**. Nguồn model = artifact từ TASK-039a.

## Phụ thuộc
- **CẦN TASK-039a xong** (có `model_<H>.ubj` 4 horizon trong `ml/funding_selector/models_v1/`).
- Dataset Kaggle sẵn: `funding-tool1-features` (ff_*.bin, 66 tháng), `funding-oi-percoin` (oi_percoin_full.bin + symbol_map.csv).

## Quyết định kiến trúc (user review)
- **Chạy 1 Kaggle kernel loop 66 tháng** (KHÔNG master-worker Aerospike). Lý do: predict rất nhẹ
  (đọc 1 file ff ~60MB + predict, ~vài giây/tháng → ~30 phút tổng < 12h limit). Master-worker queue
  chỉ thêm rủi ro khi không cần. Nếu sau cần nhanh hơn → nâng 5 worker theo tháng (đã có pattern ExportTool1).
- **Predict cho cả 4 horizon** trong 1 lần (1 record chứa 4 p_win) → backtest chọn cột nào tùy chiến lược.
- **Generate cho mọi điểm Tool1∩OI** (KHÔNG cần label, KHÔNG filter nBars) → phủ mọi entry khả dĩ.

## Việc cần làm

### Bước 1 — Viết `ml/funding_selector/generate_predict.py`
Tái dùng `read_bin`, `oi_df`, merge logic từ train code. Luồng:
```
load OI (oi_percoin_full.bin) 1 LAN  -> oi_df (sort ts)
load 4 model: xgb.Booster().load_model(model_<H>.ubj)  cho H in [4h,12h,24h,72h]
feat = [f0..f39] + 5 OI  (ĐÚNG thứ tự train_meta; assert khớp feature_list)
for moi file ff_YYYYMM.bin:
    t = tool1_df(file)  (filter 15m grid)
    merged = merge_asof(t, oi, on=ts, by=symId, backward, tol=2h)   # GIONG train, KHONG merge label
    X = merged[feat]
    for H: p[H] = booster_H.predict(DMatrix(X))    # P(win); kiem convention pred=[:,1] tuong duong
    ghi predict_YYYYMM.bin: record big-endian ">q h 4f" = (ts:long, symId:short, p4h,p12h,p24h,p72h:float)
```
- **Convention khóa:** model_<H>.ubj là XGBClassifier đã save → load bằng Booster, `predict` trả P(class=1)=P(win) trực tiếp (kiểm: so 1 điểm với XGBClassifier.predict_proba[:,1] lúc 039a). Ghi đúng P(win).
- NaN giữ nguyên (model xử được). Số dòng/tháng = số điểm Tool1 15m grid có trong tháng.

### Bước 2 — Build + push kernel `funding-generate`
- Dataset_sources: tool1, oi, + **model** (tạo dataset nhỏ `funding-model-v1` chứa 4 .ubj + feature_list, upload từ models_v1).
- Header resolve path đệ quy. `OUT_DIR=/kaggle/working`.
- checkpoint=true: nếu kernel chết giữa chừng, ghi từng `predict_YYYYMM.bin` ngay sau mỗi tháng (không gom cuối) → retry chỉ làm tháng thiếu.

### Bước 3 — Monitor + tải + đóng gói SET
- Poll until complete/error. Tải toàn bộ `predict_*.bin` (66 file).
- Tạo Kaggle dataset `chuyendinh/funding-predict-v1` chứa 66 file (để 226 tải về).
- **Tải về 226**: trên 226 `kaggle datasets download chuyendinh/funding-predict-v1 -p /home/chuyennd/java/simulator/predict/ --unzip`.

## OUTPUT FILE (rõ ràng)
| File | Nơi | Format |
|---|---|---|
| `predict_YYYYMM.bin` ×66 | Kaggle working → dataset `funding-predict-v1` → 226 `/home/chuyennd/java/simulator/predict/` | record 26B big-endian `>q h 4f` = ts(long), symId(short), p_win[4h,12h,24h,72h](4×float). NaN nếu feature thiếu. |
| `predict_index.json` | cùng | liệt kê 66 tháng + số dòng mỗi tháng + ts range |
| `docs/reports/039c.md` | repo | tiến trình + sanity check + hướng dẫn java đọc set |

> Backtest integration (java đọc set này thay ONNX realtime) là VIỆC RIÊNG — 039c chỉ TẠO set, không sửa backtest.

## TIẾN TRÌNH theo dõi (ghi report)
1. Upload model dataset — slug?
2. push kernel — version?
3. status + tiến độ (log in mỗi tháng "predict_YYYYMM ghi N dòng").
4. tải 66 file — đủ?
5. tạo dataset funding-predict-v1 + tải về 226 — path?

## NGHIỆM THU (pass/fail)
- [ ] Đủ 66 file `predict_YYYYMM.bin` (202101..202606).
- [ ] Mọi p_win ∈ [0,1] (hoặc NaN); KHÔNG có giá trị < 0 hoặc > 1 (sai convention predict).
- [ ] Số dòng mỗi tháng ≈ số điểm Tool1 15m grid tháng đó (so với log Tool1; lệch < 1%).
- [ ] **Spot-check 1 tháng**: load predict_202401.bin, lấy 5 dòng, so với chạy lại model.predict trên đúng (ts,coin) đó — khớp tới 1e-4.
- [ ] Đã tải về 226 + predict_index.json đầy đủ.
- KHÔNG tự ốp vào backtest — báo người sau khi set sẵn sàng.

## Kiểm soát tài nguyên
- 1 Kaggle slot. Phải xong 039a trước (depends_on). Kiểm slot trước push.
- Output về 226 chỉ GHI vào thư mục predict/ mới — KHÔNG đụng live/ingest/Aerospike production.
- File lớn: 66×~? — ghi từng tháng (checkpoint), không gom RAM.
