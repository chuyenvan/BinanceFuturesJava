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

**HOÀN TẤT cả 5 mục (2026-07-04, CCD opus lượt 2).** Report đầy đủ: `docs/reports/wfo_data_validation_20260704.md`. Tất cả READ-ONLY, tool `nice -n 15 -Xmx2g`, file tạm chỉ `~/claudedata/validate125/`.

| Mục | Trạng thái | Tóm tắt |
|---|---|---|
| 1. Coverage ticker Aerospike | **PASS** | 1886 ngày; 0 ngày mất; 1 partial (`20210101`=1020 phút, đúng boundary GMT+7); `20251231`+`2025Q2` sạch 1440 phút; symbol/phút min/median/max = 75/195/1131 |
| 2. 3 bộ WfoDataset (md5/count/range/funding-quý) | **PASS** (2 WARN) | 9/9 md5 khớp manifest; count khớp; funding-quý trùng audit; WARN: lệch cửa-sổ range funding giữa 3 bộ |
| 3. Gate `ai_pred_market_gate_wfo` | **PASS** | count=1,795,680 khớp CSV; range khớp; mẫu 1001 record decode: mismatch=0 missing=0 NaN=0 |
| 4. Ticker file `kaggle_data_hpo/` | **PASS** | export bù ĐÃ XONG trong phiên (🎉 1886 file, 11G); liên tục 0 gap vs day-list mục 1; gunzip 1886/1886 bad=0; 3 spot-check (2021/2023/2025) DIFF-0 khớp Aerospike bit-count |
| 5. Symbol consistency | **PASS** (1 WARN) | funding wf: 669 symbolId → 669 tên (0 orphan); WARN: 4 ghost cặp-USDC (`…USDCUSDT`) do lỗi normalize `endsWith("USDT")` |

**Không phát hiện mất/hỏng dữ liệu.** 2 WARN (4 ghost USDC-pair; lệch range funding) đã ghi mục "⚠ CẦN XỬ LÝ" đầu report — tác động nhỏ, cần quyết định normalize symbol / xác nhận cố ý. Mục 3 & 5 đã re-run độc lập lượt 2 → tái lập chính xác số liệu lượt 1.

Ghi chú: process export JVM (pid 467639) vẫn treo pgrep sau khi in 🎉 (lỗi non-daemon-thread thiếu `System.exit(0)` đã biết) — DATA hoàn chỉnh & bất biến nên đo mục 4 an toàn. KHÔNG kill (ngoài hàng rào READ-ONLY/không-đụng-process).
