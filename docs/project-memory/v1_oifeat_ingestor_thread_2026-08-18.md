# OI-feat compute = scheduled thread trong INGESTOR 242 (2026-08-18)

Theo yêu cầu Uni "viết java schedule compute chạy cùng ingres": bỏ job Oracle thủ công (không schedule → OI stale →
selector live 40/45), chuyển compute oi_feat_* thành thread định kỳ NGAY TRONG BinanceDataIngestor (242).

## Thiết kế
- `ComputeOiFeat2Live242`: tách `runOnce(days, dry)` (bỏ System.exit) — logic compute 5 feature GIỮ NGUYÊN
  (= SelectorOiProvider.buildCoin: oiDelta24h, oiZ expanding, lsGlobal, lsToptrader, takerBuy), per-coin đọc
  226-full ∪ 242-recent (một coin/lúc → không giữ full history cả 881 coin → không OOM).
- `OpenInterestIngestor2AerospikeNew.startOiFeatComputeLoop()`: thread mới, cadence **60'** (env OI_FEAT_INTERVAL_MS),
  rolling push **2 ngày** (OI_FEAT_ROLL_DAYS), delay đầu 5' (raw OI ghi trước). Gọi runOnce → push oi_feat_* 242.
- 242→226:3222 THÔNG (test) → oiZ expanding tính đúng trên full history 226.
- Config: thêm `AEROSPIKE_READ_CLUSTER=242` vào collectData/config.properties (SimpleSymbolMapper cần; trước thiếu).

## Validate (dry-run trên 242 trước khi deploy)
- 881 coin, đọc 226-full (fullPts 174k–321k/coin) + 242-recent (~569 điểm ~2 ngày). Feature non-NaN sane
  (vd CGPT d=-0.0197 z=-0.276 lsg=2.976 lst=3.866 tk=0.039), lastTs tươi (~08:30).
- Timing ~2s/coin → ~29'/881 coin. → cadence 60' (dry ~29' << tol 2h LiveOiFeatProvider) để giảm tải mạng 242→226.

## Deploy
- Rebuild jar (99640425). Backup collectData/target jar (bak_preoifeat_20260818_085304, jar cũ Jun16 98.8MB).
- scp → collectData/target + restart ingestor (daemon). pid 22689→11609. Ticker/Funding/OI/Kline-roller + OI-Feat-Compute-Loop up.
- KHÔNG đụng jar trading bot (v_t_m riêng).

## ⚠️ RỦI RO đang theo dõi: 242 RAM nhỏ (7G, available ~2G)
- Ingestor Xmx 2g. Compute transient ~150-200MB/coin (một lúc, GC sau mỗi coin) → trong 2g heap, không tăng commit box.
- catch(Throwable) nuốt OOM → bỏ cycle, KHÔNG crash. Nhưng box chật → theo dõi RSS/GC/ticker lần compute đầu (08:58).
  Nếu OOM-killer đe doạ trading bot → REVERT (redeploy jar cũ collectData/target + restart, hoặc OI_FEAT_INTERVAL_MS lớn).

## Verify còn lại
- 08:58 first compute: pushed oi_feat_*? OOM? ticker vẫn chạy? timing?
- Sau đó: trading bot selector đọc oi_feat_* non-NaN (parity 45/45) — check log DetectEntrySignal / dump feature.
- Rollback: collectData/target/binance-java-sdk-1.2.4.jar.bak_preoifeat_20260818_085304 + daemon restart.
