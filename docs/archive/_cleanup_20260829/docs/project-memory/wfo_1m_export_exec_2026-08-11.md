# EXEC LOG — full 1m unfiltered export + disk +50G — 2026-08-11

## Disk
- Boot volume expand 150→200GB (OCI Console, Uni làm, vẫn Always Free — trần always-free = 200GB block).
- OS-side (Oracle, sudo OK): rescan `/sys/class/block/sda/device/rescan` → `growpart /dev/sda 1` → `resize2fs /dev/sda1`. Root p1 là partition CUỐI nên grow sạch, không reboot.
- Kết quả: `/` từ 146G → **194G, free 53G** (đủ cho full ~20-25GB).

## Export tool (chốt cách chạy)
- Class `com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool` args `<startYYYYMMDD> <endYYYYMMDD> <outDir>`.
- Env: `FF_UNFILTERED=1 FF_GRID_MIN=1`. Config `TICKER_SOURCE=aerospike` (Oracle Aerospike CÒN market data gốc: 2,774,140 records, 863 symbols — KHÔNG cần Kaggle ticker, KHÔNG cần 226).
- Jar: `/home/ubuntu/java/simulator/binance-fresh-20260809.jar` (có class, code_sha 8741f85). cwd = `/home/ubuntu/java/simulator`.
- RAM ~2GB (market-data load một lần + batch flush 100k) → KHÔNG OOM (Oracle 23GB). Đây KHÔNG phải nguyên nhân crash cũ (crash cũ = 2 WFO worker 32GB).
- Gotcha: mỗi lần gọi để lại 1 file "stub" ~10KB cho chunk kế (tool mở file chunk mới ở mốc biên). Fix: export vào thư mục TẠM/quý rồi chỉ move file `features_<qstart>_to_*` ra, xóa temp (bỏ stub).

## Smoke (đo biên, 3 quý)
| Quý | Size | Thời gian | Ghi chú |
|---|---|---|---|
| 2023Q1 (ít) | 545 MB | ~10.6' | ~158 coin/phút = unfiltered thật |
| 2023Q3 (ít-vừa) | 703 MB | ~14.7' | |
| 2025Q4 (đông nhất) | ~2 GB | ~45'+ | nhiều coin + sự kiện Oct-2025 |

## Full export ĐANG CHẠY
- Driver `/home/ubuntu/full_export.sh` (pid 19836, detached), 21 quý 2021Q1→2026Q1, skip 3 quý smoke đã có.
- Output: `/home/ubuntu/tool1_1m_unf/features_<qstart>_to_<qend>.t1c.gz`. Log: `tool1_1m_unf/FULL_STATUS.txt`.
- ETA ~3-4h. Ước tổng ~20-25GB. Đây là kho **full 1m unfiltered để tối ưu sau** (Uni: sau này cắt bớt features hoặc kiến trúc mới để nuốt full 1m).

## Tiếp theo (sau khi full export xong)
1. (tuỳ chọn) upload per-quý lên Kaggle `funding-tool1-1m-unf-<q>` để pipeline predict-1m dùng.
2. Sửa gen script: PRED_GRID_MIN, đọc per-quý-file + per-month expand cho predict 1m; LABEL_MODE=net NET_THR=0.008 (train đọc grid-filter→15m dùng label 15m net đã có).
3. predict 1m (2023-2025) → build_ds → fanout WFO 12w → so 15m@0.008 (+10,942).
