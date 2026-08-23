# Fix selector feature parity (#33-45) — live 37/45 → 45/45 (2026-08-17)

Reconcile phát hiện live selector chạy **37/45 feature** (8 feature luôn NaN): #33-35 cross-sectional
rank + #41-45 OI/LS/taker. Nguyên nhân: chỉ implement ở pipeline export/train, chưa port sang live
inference (base extractor cố tình set NaN). Fix 2 phần, deploy full parity.

## Part A — #33-35 cross-sectional rank (commit b0c1c5c)
- `FundingCrossSectional.apply()` — COPY CHÍNH XÁC `ExportFeaturesForPythonTool.percentileRanks/applyCrossSectional`.
- Wire trong `predictAllCandidates`: rank `coinFundingRate/volumeZCoin/momentum24H` trên population
  **`EntrySignalFilter.selectCoins`** (GIỐNG export — không rank bừa toàn candidate), mutate trước predictBatch.
- Thuần compute, không data ngoài. Chạy ngay khi deploy.

## Part B — #41-45 OI/LS/taker (commit 5fb003f + a7b483b)
Thiết kế: **compute trên Oracle (full canonical), push rolling sang 242, live lookup** — giống backtest bake OI vào predict_wf.
- `ComputeOiFeat2Live242` (CHẠY ORACLE): tính exact (copy `SelectorOiProvider`: oiDelta24h, oiZ EXPANDING,
  ls, takerBuy) từ merge(OI full **226** ∪ recent **242** forward), push rolling 14 ngày → 242 set
  `OiFeatLiveSets` (oi_feat_delta24h/z/lsg/lst/takerbuy, per-coin Snappy map). Bỏ NaN khi ghi (Gson reject NaN).
- `LiveOiFeatProvider`: live chỉ lookup merge_asof backward 2h từ 242 → **zero compute/RAM** (tránh OOM;
  `SelectorOiProvider` nạp full = 3GB+ sẽ giết bot 7GB).
- Config: `getClientOracle`→key `AEROSPIKE_HOST_226`→226 (full); `getClient242`→`AEROSPIKE_HOST`→242.

## Vì sao thiết kế này (chốt với Uni)
- Full parity oiZ cần TOÀN lịch sử (expanding) → phải compute từ canonical (226 full). Seed-approach có
  drift (242 forward ingest độc lập). ⇒ compute full trên Oracle.
- 242 KHÔNG chứa nổi full: namespace ticker **34.8/50GB (~15GB free)**, memory-size 1G index, disk 14GB.
  ⇒ chỉ push rolling (vài trăm MB), chừa margin cho ingress. Backfill/compute KHÔNG đụng 242.

## Verify (dry-run PASS)
`OI_FEAT_DRY=1`: fullPts 174k-321k/coin (226 có full), recentPts ~4024 (14d merge 242, lastTs Aug 17),
oi5 sane: oiDelta ±0.04, oiZ ±1, ls 0.7-3.7, takerBuy 0.3-0.7 — non-NaN, đúng khoảng. Nguồn+merge+công thức đúng.

## Trạng thái deploy (2026-08-17 20:18)
- Live jar A+B: pid 9246, init sạch (All Models loaded, Funding Ready, ThreadManagerOrder up, no exception).
  Backup `binance-java-sdk-1.2.4.jar.bak_ab_20260817`.
- Oracle real run (PID ~237814) đang populate 242 oi_feat_* (0 lỗi write sau fix NaN), ETA ~20:46.
- CS rank (#33-35) chạy ngay. OI (#41-45) non-NaN dần theo run + mỗi tick 15m lookup.

## CÒN LẠI (phải làm)
1. **Verify tick 20:30/20:45**: dump live có #33-45 non-NaN.
2. **Re-run reconcile** xác nhận predict divergence giảm (trước 20-83%).
3. **Oracle cron 15m** cho `ComputeOiFeat2Live242` (giữ oi_feat_* tươi; nếu không, OI stale sau rolling window).
   Dùng crontab Oracle (server job), KHÔNG phải Claude scheduled-task.
4. Warmup/z-score divergence (root-cause-2 của reconcile: volumeZCoin đảo dấu) — CHƯA fix, là vấn đề riêng.

## Commits (branch module)
a7b483b (NaN fix) ← 5fb003f (OI Part B) ← b0c1c5c (CS rank Part A) ← 27ce68d (gate runbook) ← 3ba86f6 (15m grid)
