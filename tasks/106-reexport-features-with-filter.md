---
id: 106
status: TODO
owner: —
updated: 2026-06-18
touches_live_process: false
writes_242_data: false
resource: kaggle + 226 (read-only Aerospike)
require_review: false
depends_on: [103f]
---

# TASK-106: Xuất lại feature Tool1 với EntrySignalFilter (60G → ~5G) + validate chặt

> ⚠️ **ĐỌC CLAUDE.md TRƯỚC.** Mọi log/output lưu `/d/claudedata`, TUYỆT ĐỐI không ghi ổ C.
> Chỉ 1 CCD làm task này. KHÔNG đụng live trading / ingest / Aerospike-write / Redis / 242.

## Bối cảnh
Tool1 `ExportFeaturesForPythonTool` cũ ghi feature cho MỌI coin × MỌI mốc 1m → **60G** (quá lớn
cho 226 27G-free, Kaggle, RAM). Đã thêm `EntrySignalFilter` (commit 37e875b) — filter CHUNG
train/backtest/hpo/wfo/live: **vol-avg-30m ≥ 2k + top-10% |rate30m| cross-sectional** (2 chiều).
Đã validate đa-giai-đoạn (2026-06-18): %giữ ổn định ~6-10% mọi regime → 60G về **~5G**.

Bản chất: filter này VỐN phải có (selector chỉ học mốc bot thật sự cân nhắc vào lệnh). Bộ 60G
cũ SAI (thiếu filter). Task này xuất lại ĐÚNG.

**OI data (Tool2) KHÔNG xuất lại** — OI không đổi (TASK-103f đã validate đủ+đúng). Chỉ Tool1.

## Việc làm — tuần tự

### Bước 0: Tiền đề — 103f phải DONE trước
`ValidateOiData --quick` đã PASS (CHECK-3a đã nới ngưỡng, commit aee88af). Nếu 103f chưa đóng,
làm 103f trước. Task này KHÔNG đụng OI, nhưng 039 cần cả 2 → đảm bảo OI xong rồi mới tốn công.

### Bước 1: Build jar HEAD (có EntrySignalFilter) + verify filter có trong jar
```bash
cd /e/educa/source/github/20260415/BinanceFuturesJava && git pull
# build jar (theo cách build chuẩn của repo — maven/gradle hoặc script đang dùng cho ff40 kernel)
# Verify class co trong jar:
unzip -l <jar> | grep -i EntrySignalFilter   # phai thay EntrySignalFilter.class
```

### Bước 2: XÓA data Tool1 cũ (60G) — CHỈ Tool1, GIỮ OI/label
- **Trên Kaggle:** các kernel `ff40-2021..2026x` output cũ chứa `features_export_python_v3/`
  (Tool1, 60G). Output kernel ở cloud — chạy lại kernel sẽ GHI ĐÈ, không cần xóa tay. Nhưng nếu
  có dataset riêng chứa Tool1 cũ thì xóa version cũ để khỏi nhầm.
- **Trên local `/d/claudedata`:** xóa các thư mục `oi-ff40-*/features_export_python_v3` đã tải về
  (Tool1 cũ) để khỏi nhầm với bản mới:
```bash
rm -rf /d/claudedata/oi-ff40-*/features_export_python_v3 2>/dev/null
df -h /c | tail -1   # xac nhan KHONG cham o C
```
- **GIỮ NGUYÊN:** `features_oi_percoin_v1` (Tool2 OI — không đổi), data label 024.

### Bước 3: Xuất lại Tool1 với filter — chia năm trên Kaggle (như cũ)
Chạy lại CÁC kernel ff40 (Tool1 phần), mỗi kernel 1 năm/nửa năm, jar HEAD có filter:
`ff40-2021, ff40-2022, ff40-2023, ff40-2024h1, ff40-2024h2, ff40-2025h1, ff40-2025h2x, ff40-2026x`.
- Tham số Tool1: `args[0]=ngày bắt đầu, args[1]=ngày kết thúc` (yyyyMMdd) — giữ ranh giới năm như cũ.
- **Quan trọng:** filter cần warmup history (30m+) → Tool1 đã có warmup 48h sẵn, KHÔNG cần đổi.
- Slot Kaggle ≤5 song song (KAGGLE_RULES §1). Output mỗi kernel ~0.5-0.7G (thay vì 5-6G).
- Tải log mỗi kernel về `/d/claudedata` (KHÔNG /tmp), grep "HOÀN TẤT".

### Bước 4: VALIDATE CHẶT (như TASK-103f đã làm cho OI) — pre-register pass criteria
Trước khi xem kết quả, CHỐT tiêu chí PASS:
1. **Size:** tổng Tool1 mới ~3-7G (giảm ~90% so với 60G). Nếu vẫn >15G → filter KHÔNG áp đúng, DỪNG.
2. **% giữ:** mỗi file, đếm record vs số mốc×coin kỳ vọng. Tỷ lệ giữ phải ~6-12% (khớp đo đa-giai-đoạn).
   Nếu ~100% → filter bị bỏ qua (kiểm jar có class không). Nếu ~0% → filter quá gắt / warmup sai.
3. **Phân bố cột:** đọc 1 file .bin.gz mẫu (script `/d/claudedata/validate_float16.py` đã có, hoặc
   viết lại đọc 170B/record), kiểm vài cột hợp lý: `coinFundingRate` ∈ [-0.01,0.01],
   `rsi1H` ∈ [0,100], `rangePosition24H` ∈ [0,1], `ret15m` cỡ nhỏ. KHÔNG cột nào toàn NaN/toàn 0.
4. **Cross-check số coin/mốc:** vài mốc ngẫu nhiên, xác nhận số coin giữ ≈ 10% số coin có volume
   tại mốc đó (đúng định nghĩa top-10% cross-sectional).
5. **Regime coverage:** có record ở cả giai đoạn crash (2022-05, 2022-11) lẫn bull (2024) — filter
   không được làm rỗng giai đoạn nào (đã đo: mọi regime giữ ~8%).

Ghi report `docs/reports/106.md`: size trước/sau, %giữ từng năm, kết quả 5 tiêu chí, PASS/FAIL.

### Bước 5: Nếu PASS → đóng task
- Set 106 = DONE, ghi commit + report.
- Báo: data Tool1 mới sẵn sàng cho merge 039 (`python/tool/merge_039_features.py` đã chuẩn bị,
  target +6% đã chốt).

## An toàn
- 226 Aerospike READ-ONLY. Không kill PID lạ — chỉ PID kernel của session này.
- Mọi output `/d/claudedata`, không ổ C.
- Nếu bất kỳ tiêu chí Bước 4 FAIL → DỪNG, báo lại, KHÔNG tự sửa filter (tham số filter khóa cứng,
  đổi phải hỏi user vì ảnh hưởng backtest/live).

## (CCD điền)
- Bước 1: jar build hash, EntrySignalFilter có trong jar? (y/n)
- Bước 3: kernel nào chạy, output size mỗi năm
- Bước 4: size tổng trước/sau, %giữ từng năm, 5 tiêu chí PASS/FAIL
- Bước 5: commit + report hash
