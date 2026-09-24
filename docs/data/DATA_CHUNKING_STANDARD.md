# Chuẩn hóa chunk dữ liệu metric trong Aerospike (ts → float per-symbol)

> Áp dụng cho mọi set lưu chuỗi thời gian per-symbol dạng `Map<Long,Float>` nén Snappy
> (OI, LS, taker, funding pred, selector pred...). KHÔNG áp cho set per-minute-all-coin
> (kline `kline_1m_opt`, market_data) vốn key theo mốc phút.

## Nguyên tắc

Aerospike có **giới hạn record size** (mặc định ~1MB, tối đa cấu hình tới 8MB). Một record =
1 chunk = toàn bộ điểm của 1 symbol trong 1 khoảng thời gian, nén Snappy. Chọn độ rộng chunk
theo **mật độ điểm**, sao cho 1 chunk KHÔNG bao giờ vượt record size:

| Cadence dữ liệu | Điểm/tháng | Chunk chuẩn | Key | Hàm |
|---|---|---|---|---|
| ≥ 5 phút (OI, LS, selector-15m) | ≤ ~8.9k | **THÁNG** | `SYMBOL_yyyyMM` | `writeMetricMap226` / `getMetricMap226` |
| 1 phút (selector-1m, funding-1m) | ~43k | **NGÀY** | `SYMBOL_yyyyMMdd` | `writeMetricMapDay226` / `getMetricMapDay226` |

**Lý do ngưỡng:** chunk-tháng với data per-phút (~43k điểm) khi nén Snappy + JSON vẫn vượt
record size → lỗi `Record too big` (đã gặp thực tế khi convert funding v5 per-phút sang
chunk-tháng: 16,075 chunk lỗi). Chunk-ngày per-phút chỉ ~1440 điểm → an toàn tuyệt đối.

## Quy tắc "chuyển dần về NGÀY khi có tác động lớn"

Khi một set đang chunk-THÁNG bắt đầu nhận dữ liệu **dày hơn 5 phút** (vd nâng selector từ
15m lên 1m, hay thêm cadence mới), PHẢI chuyển set đó sang chunk-NGÀY. Không cố nhồi data dày
vào chunk-tháng. Tiêu chí quyết định = mật độ điểm/tháng, KHÔNG phải loại metric:
- Ước lượng điểm/tháng = (số phút trong tháng) / (cadence phút). Nếu > ~9k → dùng NGÀY.
- Khi nghi ngờ (cadence hỗn hợp, hoặc sẽ dày lên trong tương lai) → chọn NGÀY cho chắc.

## Bất biến kỹ thuật (giữ khi thêm biến thể chunk mới)

- **TZ = GMT+7** (`OI_METRIC_TZ`) cho cả month/day formatter — đồng nhất với key tháng của
  kline/15m/4h để reader iterate nhất quán.
- **Merge-guard**: mỗi chunk read-merge-GUARD-write (record có blob nhưng đọc rỗng → nghi lỗi
  đọc, KHÔNG ghi đè). Bất biến này dùng chung qua `writeMonthChunk` cho cả month lẫn day.
- **Reader phải khớp writer**: data ghi bằng `writeMetricMapDay226` (key ngày) CHỈ đọc đúng
  bằng `getMetricMapDay226`. Đọc nhầm bằng `getMetricMap226` (key tháng) → rỗng. Khi đổi
  cadence của 1 set, đổi ĐỒNG THỜI cả đường ghi và mọi đường đọc + backtest reader.
- Quét đọc: month [202001..nay] (~70 key), day [20200101..nay] (~2000 key) — vẫn 1 batch-get
  chia theo `BATCH_CHUNK_SIZE`, chi phí đọc không đáng kể.

## Checklist khi tạo/đổi set metric

1. Ước lượng điểm/tháng theo cadence → chọn THÁNG hay NGÀY theo bảng trên.
2. Ghi bằng đúng hàm (`writeMetricMap226` hoặc `writeMetricMapDay226`).
3. Mọi nơi đọc (tool, validator, **backtest reader**) dùng hàm getter KHỚP granularity.
4. Verify: đọc lại 1 symbol, đối chiếu số điểm + giá trị với nguồn; 0 chunk-lỗi trong log.
