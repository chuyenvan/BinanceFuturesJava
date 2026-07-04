# TASK-124: Bộ ticker daily → dataset Kaggle — mở khoá 5-slot full-range (GĐ3 scale N)

- **status:** doing (master 2026-07-04 — export bù đang chạy nền Oracle, pid 467269)
- Phát hiện: kaggle_data_hpo/ đã có 554 ngày (~2MB/ngày gzip); toàn range 20210101–20260301 chỉ ~3.7GB.
- Bước: (1) 🔄 export bù 1332 ngày (ExportHpoDataKaggle, log ~/claudedata/export_ticker_full.log);
  (2) upload dataset `chuyendinh/hpo-ticker-daily`; (3) ✅ path-logic smoke PASS qua dataset mini (kernel ticker-file-smoke: symlink CWD + copy config + auto-unzip .gz→.bin — learning ghi §3b-bis); (4) kernel worker chế độ
  TICKER_SOURCE=file (bỏ sed aerospike; hết giới hạn 2-concurrency + hết trần 2024-04) + smoke 1 kernel;
  (5) replication full 17 window × 5 slot. Node-type mới "kaggle-file" — chỉ so Δ nội bộ (phụ lục pre-register đã phủ).
## Kết quả
<master điền theo bước>
