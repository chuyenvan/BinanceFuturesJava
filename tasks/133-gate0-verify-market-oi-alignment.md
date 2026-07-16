---
id: 133
status: DONE
depends_on: []
touches_live_process: false
writes_242_data: false
resource: heavy_226
checkpoint: false
max_retry: 1
report: docs/reports/133.md
require_review: true
---

# TASK-133: GATE-0 — Verify alignment market_data_object (mới) ↔ OI feature (reused) TRƯỚC khi re-export ff

- **status:** TODO
- **Bối cảnh:** 4 tầng data vừa chốt (SESSION_START.md §"Trạng thái"): `market_data_object` **GEN MỚI** (thêm coin
  delist + đuôi sập), nhưng `OI feature` là bản **REUSED** (validate từ context trước). Bước kế của pipeline
  (SESSION_START §3.1) là re-export `ff_*.bin` — bước này **JOIN market ↔ OI theo `symId`**. Nếu regen market đã
  xáo/thêm ánh xạ `symId` (thêm coin delist gần như chắc có), OI cũ join market mới có thể **lệch symbol hoặc rớt
  câm** — không lỗi, không log. Đây là GATE-0: ĐO alignment trước, KHÔNG export gì.
- **Vì sao là GATE:** mọi bước 1→5 (ff → funding pred → wfo_dataset → validate → WFO baseline) kế thừa cái join này.
  Sai ở đây = rác toàn chuỗi. Rẻ hơn nhiều nếu đo trước 1 lần.

## ⛔ HÀNG RÀO
1. **CHỈ ĐO, KHÔNG EXPORT / KHÔNG GHI.** Read-only trên Aerospike (Oracle/226) + đọc bin OI reused + `symbol_map`.
   Không chạy `ExportFeaturesForPythonTool`, không gen ff, không đụng market/OI/live/config.
2. **Đọc code trước, không đoán schema.** Xác định `symId`→symbol mapping mà market mới dùng, và mapping mà OI reused
   dùng, từ CODE + file map thật (SurvivorshipBac0/SurvivorshipFeatureCheck + tool gen market + `symbol_map.csv` của OI).
   Ghi rõ nguồn từng con số.
3. Không đụng Oracle compute nặng (vế D có thể đang chạy — RAM budget AGENTS.md). Chỉ đọc-đếm Aerospike, nhẹ.
4. SLF4J only nếu phải viết enumerator tạm; ưu tiên script đọc-đếm, không thêm code production.
5. Quyết định "làm gì nếu lệch" (regen OI vs thu hẹp universe) = **NEEDS_HUMAN → Uni**, KHÔNG tự chọn.

## Đo đúng 3 câu (pre-register — chốt TRƯỚC khi nhìn số)
**Q1 — Coverage symbol:** Universe symbol trong `market_data_object` mới (tập sẽ vào WFO) so với universe symbol có
trong OI feature reused. Xuất bảng: `symbol | in_market | in_OI | symId_market | symId_OI | khớp?`. Đếm:
- `N_market` = số symbol trong market mới
- `N_OI` = số symbol có OI
- `N_missing_OI` = số symbol ∈ market NHƯNG ∉ OI (con này >0 = join rớt câm ở bước 1)
- `N_symId_mismatch` = số symbol có symId khác nhau giữa market vs OI (con này >0 = join LỆCH — nguy hiểm hơn thiếu)

**Q2 — Range thời gian:** với 3–5 symbol mẫu (gồm ≥1 DEAD như LUNA + ≥1 sống), so [firstTs, lastTs] của market vs OI.
Lệch range = feature NaN/thiếu ở rìa. Ghi rõ có purge/pad không.

**Q3 — Survivorship đã vá thật chưa (con số quyết định):** trong 62 DEAD (symbol_lifecycle), đếm bao nhiêu con
**ĐỒNG THỜI**: (a) ∈ universe WFO tradable, (b) có OI feature, (c) có CSV/ticker backfill. Xuất `N_dead_fully_ready`
và liệt kê con DEAD nào **thiếu** ở cột nào. Làm rõ "38 CSV vs 62 DEAD" (DATA_STATE): 24 con chênh có ∈ universe WFO
không? Nếu có mà thiếu backfill → survivorship vá MỘT PHẦN, WFO baseline mới vẫn "an toàn giả".

## Pass/Fail (factual — KHÔNG phải verdict PnL)
- **CLEAN** (STATUS=DONE): `N_missing_OI = 0` VÀ `N_symId_mismatch = 0` VÀ range khớp (Q2) → pipeline bước 1 join sạch,
  seed chuỗi 1→5 được.
- **LỆCH** (STATUS=NEEDS_HUMAN): bất kỳ `N_missing_OI>0` / `N_symId_mismatch>0` / range lệch / `N_dead_fully_ready`
  thấp bất ngờ → DỪNG, báo số + đề xuất (regen OI theo market mới? thu hẹp universe? backfill 24 con?) cho Uni quyết.
  KHÔNG tự sửa, KHÔNG seed bước 1.

## Output
- `docs/reports/133.md`: bảng Q1 (hoặc link CSV nếu dài) + Q2 + Q3 + 4 con số đếm + kết luận CLEAN/LỆCH.
- Kết thúc report bằng block (để supervisor harvest được):
```
=== RESULT ===
STATUS: DONE|NEEDS_HUMAN
COMMIT: <hash|->
ARTIFACTS: docs/reports/133.md[, coverage_133.csv]
VERIFY: N_market=.. N_OI=.. N_missing_OI=.. N_symId_mismatch=.. N_dead_fully_ready=../62
DECISIONS: <|->
QUESTIONS: <nếu LỆCH: đề xuất hướng cho Uni|->
=== END ===
```
