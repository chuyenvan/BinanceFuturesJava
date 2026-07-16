---
id: 100
status: CANCELLED
touches_live_process: false
writes_242_data: false
resource: local+kaggle
---

# TASK-100: Benchmark tốc độ ExportFeaturesForPythonTool — Kaggle vs 226

## Bối cảnh
CCD đang chạy TASK-037 fan-out (ff40-2022..2026) trên Kaggle. Song song đó có thử chạy
`ExportFeaturesForPythonTool` trực tiếp trên 226 và thấy **chậm đáng kể**. Cần đo số cụ thể
để quyết định: 226 có dùng được như phương án dự phòng/song song không, hay dứt khoát Kaggle-only.

## Đo trên 226 (SSH)
Chạy tool với **range 7 ngày** (nhỏ, không gây tải nặng) để đo throughput:

```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 '
  JAR=$(ls /root/java-run/*.jar 2>/dev/null | head -1)
  # hoac tim jar theo path CCD dung khi deploy
  echo "JAR=$JAR"
  START_MS=$(date +%s%3N)
  timeout 300 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp "$JAR" \
    com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool \
    20230101 20230108 2>&1 | tail -5
  END_MS=$(date +%s%3N)
  echo "ELAPSED_MS=$((END_MS - START_MS))"
  # dem record output
  F=$(ls /root/features_export_python_v3/features_*20230101*.bin.gz 2>/dev/null | head -1)
  if [ -n "$F" ]; then
    SZ=$(stat -c%s "$F"); REC=$((SZ / 170))
    echo "FILE=$F SIZE=$SZ RECORDS=$REC"
  fi
'
```

> Lưu ý: tìm đúng path jar CCD đang dùng (có thể khác `/root/java-run/`). Kiểm bằng
> `find /root /home -maxdepth 4 -name "*.jar" 2>/dev/null | head -5` nếu cần.

## Đo trên Kaggle (từ log kernel đã chạy)
Không cần chạy thêm kernel — parse từ log ff40-2022 (hoặc bất kỳ kernel COMPLETE):

```bash
kaggle kernels output chuyendinh/ff40-2022 -p /d/claudedata/ff40-2022-out 2>/dev/null
# tìm dòng log chứa thời gian chạy Tool1 + số record
grep -E "HOAN TAT|records|elapsed|TASK-037|dong x" /d/claudedata/ff40-2022-out/*.log 2>/dev/null | head -20
```

Cần lấy: **#record Tool1** + **thời gian chạy Tool1** (tính từ log STARTED → HOAN TAT).

## Tính throughput
```
throughput_226   = records_226   / elapsed_seconds_226   (rec/s)
throughput_kaggle = records_kaggle / elapsed_seconds_kaggle (rec/s)
ratio = throughput_kaggle / throughput_226
```

Ước tính thời gian full (57.6M record/năm nặng):
```
time_226_full_year_h   = 57_600_000 / throughput_226   / 3600
time_kaggle_full_year_h = 57_600_000 / throughput_kaggle / 3600
```

## Báo lại (CCD điền — 2026-06-17 GMT+7)

| | 226 | Kaggle |
|---|---|---|
| Range đo thực tế | Q1 2021 (tool bắt đầu từ data cũ nhất, không lọc theo arg ngày) | H1 2023 (ff40-2023 COMPLETE) |
| #record | **11,278,346** (Java tool log trực tiếp) | **38,374,777** (validate log) |
| Elapsed (s) | **247 s** (net: sau FundingFeeManager init 20:32:47→20:36:54) | **1,450 s** (04:10:37→04:34:47) |
| Throughput (rec/s) | **45,660 rec/s** | **26,465 rec/s** |
| Ước tính full năm nặng (57.6M) | **0.35 h** (21 min) | **0.60 h** (36 min) |

> **Ghi chú quan trọng về so sánh:**
> - 226 đo trên Q1-2021 (~300-400 symbols active, ít symbol/tick hơn). Kaggle đo trên H1-2023 (~600-700 symbols). Nhiều symbol = nhiều record/tick = chậm hơn/tick.
> - **Lý do 226 nhanh hơn:** đọc Aerospike LOCAL (cùng máy, latency ~0.1ms/call) vs Kaggle đọc Aerospike 226 qua internet (latency ~5-20ms/call). Bottleneck là I/O Aerospike, không phải CPU.
> - Tool trên 226 KHÔNG nhận args ngày `20230101 20230108` — nó luôn bắt đầu từ data cũ nhất trong Aerospike (2021), file output đặt tên theo thực tế data range.
> - File Q1-2021 trên 226: 348 MB compressed / 1.917 GB uncompressed (5.5× ratio). File Q1-2022 trên Kaggle: 1.389 GB compressed → ~45M records ước tính (nhất quán với nhiều symbol hơn năm 2022).
> - Sau đo: đã dọn file tạm `/home/chuyennd/java/simulator/features_export_python/features_20210101_to_20210401.bin.gz` trên 226.

**Kết luận:** **226 nhanh hơn Kaggle ~1.73×** trong workload này do Aerospike local. Cả hai đều hoàn thành 1 năm nặng trong vòng 1 giờ. **226 dùng được song song với Kaggle** — nhưng cần chú ý: (1) job nặng đọc Aerospike nhiều → tránh chạy quá nhiều job song song trên 226 cùng lúc để tránh saturate Aerospike; (2) khi dùng Kaggle, bottleneck là mạng 226→Kaggle chứ không phải CPU Kaggle.

## Ghi chú an toàn
- Trên 226: KHÔNG đụng process live trading/ingest/Aerospike/Redis. Chỉ đọc Aerospike.
- Chạy `timeout 300` để tránh treo. Output vào `/root/features_export_python_v3/` (không đè gì của 037 vì range khác).
- Sau khi đo xong: xóa file test `rm -f /root/features_export_python_v3/*20230101*20230108*.bin.gz`.
