# TASK-125: Validate độc lập một lượt TOÀN BỘ dữ liệu WFO (CCD opus, READ-ONLY trên Oracle)

- **status:** doing (giao CCD 2026-07-04 trưa)
- **resource:** local + SSH Oracle (`ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd ubuntu@161.118.212.3`, lọc noise grep -vE "post-quantum|store now|upgraded|openssh")

## ⛔ HÀNG RÀO CỨNG
1. **READ-ONLY tuyệt đối trên Oracle**: chỉ đọc/scan/tính. CẤM: ghi/xoá/sửa bất kỳ file dữ liệu nào, CẤM reset/status-làm-thay-đổi jobstore, CẤM kill/khởi động process, CẤM đụng server 242/226. File tạm & script → chỉ `~/claudedata/validate125/` (được tạo mới thư mục này).
2. Đang có vế B chạy (2 java Xmx9g) + export ticker: mọi lệnh java/python của bạn phải `nice -n 15` và `-Xmx2g` tối đa. Foreground ≤4 phút — dài hơn thì setsid nohup + poll.
3. Mọi số liệu trong report phải kèm LỆNH đã chạy (reproducible). Không suy diễn — cái gì không đo được ghi "chưa đo được vì X".

## Phạm vi validate (theo thứ tự)
1. **Ticker Aerospike Oracle-local (nguồn vế A/B/C):** quét coverage theo NGÀY 20210101→20260301 — ngày thiếu hẳn / ngày <1440 phút / số symbol per ngày (min/median). Đặc biệt định lượng vùng từng thấy "Date data error": 20251231, 2025Q2. Cách quét: tự viết tool java nhỏ (compile trong ~/claudedata/validate125/) dùng jar task121 làm classpath lib, hoặc python nếu khả thi — miễn READ-ONLY.
2. **3 bộ WfoDataset** (`wfo_dataset_wf`, `wfo_dataset`, `wfo_dataset_leaked_restricted`): re-verify md5 3 bin vs manifest từng bộ; range tick đầu/cuối 3 file mỗi bộ khớp nhau; funding coins/tick theo quý đối chiếu số audit đã có (docs/reports/funding_coverage_audit_20260702.md).
3. **Set gate mới nạp `ai_pred_market_gate_wfo`** (ns=test local): đếm record so 1,795,680; range ts đầu/cuối so csv; sample 1000 record ngẫu nhiên decode Snappy+gson → NaN/null check + đối chiếu 20 dòng với csv gốc.
4. **Bộ ticker file `kaggle_data_hpo/`** (chờ export pid 467269 xong — poll marker log "DONE" hoặc process chết): đủ ngày liên tục 20210101→20260301? mọi file `gunzip -t` pass? spot-check 3 ngày (2021, 2023, 2025): load số phút + số symbol, ĐỐI CHIẾU cùng ngày từ Aerospike local → định lượng lệch file-vs-aerospike (số tick, symbol set).
5. **Symbol consistency:** symbolId xuất hiện trong funding.bin (wf) decode qua mapper → tên; đối chiếu tập tên với universe_birth_death (~/claudedata/universe_birth_death.csv) → symbol nào trong backtest KHÔNG có trong universe thật (ghost).

## Output bắt buộc
- `docs/reports/wfo_data_validation_20260704.md` — bảng kết quả 5 mục, mỗi mục PASS/FAIL/WARN + số + lệnh.
- Phát hiện bất thường → mục "⚠ CẦN XỬ LÝ" đầu report. Commit report + Kết quả vào task + marker /d/claudedata/CCD125_DONE.

## Kết quả
<CCD điền>
