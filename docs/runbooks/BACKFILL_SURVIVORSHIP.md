# RUNBOOK — Backfill survivorship (39 coin delist) → dữ liệu chuẩn Aerospike Oracle → export .bin

> **Ngày:** 2026-07-07 · **Trạng thái:** kế hoạch đã duyệt hướng (Uni), GATE 0 PASS. Thực thi có checkpoint.
> **Tài liệu liên quan (KHÔNG lặp):** ADR-0007 (survivorship material), ADR-0009 (pivot rebuild — đây là P1→P3 của nó),
> PIPELINE_PROVENANCE.md (luồng end-to-end + kế hoạch leak-free mục 7), db/index.md (topology), DATA_CHUNKING_STANDARD.md.

## 0. MỤC TIÊU (Uni chốt 2026-07-07)
Bộ dữ liệu CHUẨN đi theo pipeline CHUẨN: **Aerospike Oracle = nguồn chuẩn dữ liệu test**. Backfill 39 coin delist vào
Oracle → validate luồng Aerospike sạch → **export ra .bin phục vụ master-worker trên mọi tài nguyên** (Oracle/Kaggle).
Cho phép cách thực dụng: fill vào .bin trước rồi rewrite ngược Aerospike cũng OK (nhưng hướng chuẩn = Aerospike-first).

## 1. VÌ SAO KHẢ THI BÂY GIỜ (khác ADR-0007 hoãn)
ADR-0007 hoãn vì "sim đọc 242 → backfill phải ghi 242 tiền-thật = rủi ro". **Nay đã đổi:** Oracle đọc ticker từ
Aerospike LOCAL (`config.properties`: `AEROSPIKE_READ_CLUSTER=226` + `AEROSPIKE_HOST_226=127.0.0.1` → "226" trỏ localhost
Oracle). ⇒ Backfill vào Aerospike Oracle local NÉ được rủi ro 242. 242/226-vật-lý KHÔNG đụng.

## 2. GATE 0 — FEASIBILITY (ĐÃ PASS 2026-07-07)
Tool `Gate0BackfillFeasibility` (HTTP read-only, không đụng Aerospike). Kiểm 3 nguồn cho LUNA/FTT/ANC quanh lúc sập:
| Coin | Kline 1m | Metrics(OI) | Funding |
|---|---|---|---|
| LUNA (2022-05) | ✅ 17691 | ✅ 289 | ✅ 10 |
| FTT (2022-11) | ✅ 43201 | ✅ 289 | ✅ 26 |
| ANC | ✅ 17682 | ✅ 289 | ✅ 10 |
→ Backfill được CẢ giá+OI+funding cho coin delist. ĐI TIẾP.

## 3. ⚠️ CẠM BẪY ĐÃ PHÁT HIỆN (đọc trước khi code)
1. **`writeMinuteBatch`/`writeFundingMap`/`writeOpenInterestMap` trong `DataManagerAerospikeFloatSim` HARDCODE `getClient242()`.**
   → KHÔNG tái dùng nguyên trạng để backfill vào Oracle (sẽ ghi 242!). Phải viết tool ingest MỚI trỏ client Oracle local,
   HOẶC set `Configs.AEROSPIKE_HOST_242 = 127.0.0.1` trên Oracle lúc chạy backfill (kiểm kỹ không rò sang box khác).
2. **Format ticker đích:** proto `MinuteDataFinal` = map `symbol→KlineObjectOptimized{priceOpen,maxPrice,minPrice,priceClose,totalUsdt}`,
   Snappy, bin `data`, set `kline_1m_opt`, key `yyyyMMdd-HHmm` **GMT+7**. Convert kline vision (12 cột) → 5 field: totalUsdt = cột quote-volume (idx 7).
3. **Chunk chuẩn:** ticker key theo MỐC PHÚT (không per-symbol) → dùng `writeMinuteBatch` pattern (merge coin mới vào record phút đã có).
   OI/LS/taker per-symbol → chunk NGÀY nếu ≥5m (theo DATA_CHUNKING_STANDARD). Funding per-symbol → set `funding_data`.
4. **Provenance test-only:** 39 coin sống ở Oracle ns=test, TÁCH khỏi 242-source. GHI RÕ manifest. Lên live phải backfill lại vào 242 đường chính thức.

## 4. LUỒNG 7 BƯỚC + NODE + TÀI NGUYÊN + CHECKPOINT

### B1 — Backfill 39 coin (kline + funding + OI) → Aerospike Oracle local
- **Node:** Oracle (có internet tải vision + Aerospike local). **Tài nguyên:** master-worker chia coin (39 coin, nhẹ).
- **Tool cần viết:** `BackfillDelistCoin` — mỗi coin: tải kline (SurvivorshipBac0 pattern) + convert→MinuteDataFinal→ghi Oracle;
  tải OI/LS/taker (VisionMetricsClient.fetchSymbol); tải funding (fapi). Trỏ client Oracle local (xem cạm bẫy #1).
- **CHECKPOINT 1a (VALIDATE SMALL):** backfill CHỈ LUNA trước → đọc lại từ Oracle → xác nhận đúng format (số phút, giá khớp vision).
  PASS mới mở 39 coin. ← Uni duyệt.
- **CHECKPOINT 1b:** sau 39 coin, đếm coverage Oracle (kỳ vọng 711→~750). Validate không hỏng ticker cũ.

### B2 — Convert + verify format (gộp vào B1 cho từng coin)
- Verify: `CoverageScan` (TASK-125 tool) đọc lại ngày có coin delist → symbol xuất hiện đúng, giá khớp klines vision.

### B3 — Export lại toàn bộ MarketObject (market.bin)
- **Node:** Oracle. **Vì:** universe đổi → feature market-level (rateDownAvg…) tính lại trên universe mới.
- **Tool:** re-run market export đọc ticker Oracle → set `market_data_object` (hoặc file). ⚠️ ADR-0009: re-export 100%, không chèn lẻ.
- **CHECKPOINT 3:** so market.bin cũ vs mới — feature 2022 (quanh LUNA/FTT sập) PHẢI đổi rõ (nếu không đổi = backfill chưa vào feature). ← Uni duyệt.

### B4 — Xuất features gate + selector
- **Node:** Oracle/Kaggle (đọc-only 226-local). **Tool:** `ExportFeaturesForPythonTool`→ff_*.bin (40 feat #1-45); `ExportFundingOiPerCoin` (source=vision hoặc Aerospike)→OI.
- **CHECKPOINT 4:** feature coin delist có mặt trong ff_*.bin (grep symbolId LUNA/FTT).

### B5 — Train 2 model (GPU, vài phút)
- **Node:** Oracle GPU (venv xgb-env) hoặc Kaggle GPU. **Tool:** `train_funding_selector.py` (per-fold leak-free, PIPELINE_PROVENANCE mục 7) + gate.
- **CHECKPOINT 5 (CỔNG IC, PIPELINE.md):** rank-IC dương, lift>1.0. FAIL→dừng, sửa feature/label. ← Uni duyệt verdict.

### B6 — Generate lại prediction full-history theo 2 model mới
- **Node:** master-worker mọi tài nguyên (NẶNG — inference lịch sử 2021-2026 × universe mới). **Tài nguyên:** Oracle + Kaggle 5 kernel.
- **Tool:** inference gen → set pred mới (version wf) + sidecar provenance.
- **CHECKPOINT 6:** đếm pred coverage; coin delist có pred 2022.

### B7 — Export .bin cho master-worker + WFO baseline mới THẬT
- **Node:** Oracle (ExportWfoDataset). **Tool:** `ExportWfoDataset`→ wfo_dataset_wf_v2/{market,pred,funding}.bin + manifest (provenance đầy đủ mục 6 PIPELINE_PROVENANCE).
- **CHECKPOINT 7:** WFO trên dữ liệu sạch, CÙNG ngưỡng pre-reg (WFE≥0.5, %OOS+≥70%, maxDD≤50%). So verdict với kết quả cũ (giờ chỉ là THAM KHẢO).

## 5. SNAPSHOT TRƯỚC KHI GHI ĐÈ (bắt buộc — đo survivorship định lượng)
Trước B3 (ghi đè market.bin/features/model): snapshot dataset cũ có version rõ (vd `wfo_dataset_wf_pre_survivorship/`).
→ Giữ mốc TRƯỚC/SAU backfill = phép đo survivorship định lượng (golden CRASH trước +5507 vs sau — kỳ vọng xấu đi rõ).

## 6. RANH GIỚI (Claude giữ)
- Mọi bước GHI (B1 convert+ghi Oracle, B3 đè market, B6 gen pred) = báo Uni ở CHECKPOINT, KHÔNG chạy một mạch.
- KHÔNG đụng 242/226-vật-lý. Chỉ Aerospike Oracle local.
- Validate small (LUNA) trước full (39). Snapshot trước ghi đè.

## 7. TRẠNG THÁI
- [x] GATE 0 feasibility (2026-07-07) — PASS
- [ ] B1 pilot LUNA → CHECKPOINT 1a
- [ ] B1 full 39 coin → CHECKPOINT 1b
- [ ] B3 re-export market → CHECKPOINT 3
- [ ] B4 features → B5 train → B6 generate → B7 WFO baseline mới
