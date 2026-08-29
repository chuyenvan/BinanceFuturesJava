# NEXT SESSION — Entry Alpha (Phase 1) handoff

> Live + concise + TRIM. Xoá mục xong. Chi tiết số → outputs JSON, không nhét vào đây.
> Cập nhật lần cuối: 2026-07-25, cuối phiên điều tra entry-alpha.

## MỤC TIÊU
Trả lời: entry có ALPHA thật (tách khỏi beta/artifact) không, và monetize được không. Chưa build/đổi model production.

## ĐANG CHẠY (job nền — CHECK ĐẦU PHIÊN)
- **Unfiltered feature export** trên Oracle (161.118.212.3): PID **19781**, `java -Xmx18g ExportFeaturesForPythonTool 20210101 20260701 FF_UNFILTERED=1 FF_SAMPLE_RATE=0.5`.
  - out: `/home/ubuntu/claudedata/ff_unfiltered_v1/full/` (features_*.bin.gz, struct `>q h 40f`, lưới 15m)
  - symbol map: `/home/ubuntu/claudedata/ff_unfiltered_v1/symid_map.csv` (781 sym)
  - log: `/home/ubuntu/claudedata/ff_unfiltered.log`
  - ⚠️ Phóng bằng SSH nohup (SAI quy trình) → CE `bg_*` KHÔNG track. Check bằng: `ce sys_health` / hoặc ssh ps -p 19781. Disk Oracle chỉ còn ~9G — theo dõi.
  - Lúc handoff: đang ghi ~2022Q4 (~1/3). ETA vài chục phút.

## VIỆC KẾ (THEO CE — KHÔNG hand-roll SSH/poll nữa)
1. Export xong → `ce kaggle_push <dir>` tạo dataset `chuyendinh/funding-tool1-features-unfiltered` (kèm symid_map.csv). Dùng `ce kaggle_status/kaggle_output`, KHÔNG powershell kaggle tay.
2. **Re-probe selectability trên universe UNFILTERED** (đo edge THẬT, tách artifact extreme-mover). Tái dùng script `entry-alpha-phase1c2/1f/1g` (ở outputs), đổi dataset sang unfiltered. YÊU CẦU: **walk-forward toàn quý** (KHÔNG split 70/30 recent như phiên này — OOS chỉ phủ 2025Q2–2026Q2). Pre-register gate trước khi xem.
3. Có edge magnitude thật → quyết: (A) build track A trailing sim; (B) pivot mean-reversion; hay dừng.

## TRACK A — ĐÃ DRAFT, chưa build
Tool Java `ExportEventPath` (export path OHLC 1m sau mỗi event, int16 relative, ~430MB/24h gz) + Python trailing simulator (activate +3% / lock +1% / quét trail width → net EV top-decile). Skeleton + format spec trong transcript phiên này. Chỉ build/run SAU khi có selector đáng tin trên unfiltered.

## ĐÃ CHỐT (đừng đo lại)
- **Bias gốc:** `ff_*.bin` bị `EntrySignalFilter` gate = top-10% |rate30m| (extreme movers). Merge label×ff = subset thiên kiến → **tự sinh mean-reversion (regression-to-mean)**. File `funding_label.csv` SẠCH (all alt × 15m), lưới 15m do `SAMPLE_STEP_MS`.
- **1a (universe sạch 47.8M):** continuation THẬT — reach+3%@4h=16.6%; trong nhóm reached: median retEnd_4h +2.78%, run-further ≥3pp = 26/43/63% @12/24/72h. MAE|4h| p90≈4% (set initial stop). Nền bleed ~0, âm mọi quý/regime.
- **selectability (subset thiên kiến):** OOS IC 0.078 (full)/0.064 (bỏ hết feature recent-move) → **có structure thật ngoài reversion** (funding/volume/OI). Nhưng top-decile vẫn **net ÂM** dưới exit endpoint+stop.
- **1g regime/quý:** edge mạnh nhất DOWN/CHOP, ~0 ở UP → **KHÔNG phải uptrend-beta**. Nhưng OOS chỉ 5 quý gần → cần walk-forward.
- **Label semantics:** triple-barrier path-thô maxFav/maxAdv/tHitFav/tHitAdv/retEnd/nBars @{4h,12h,24h,72h}. Nghi lệch pha feature(:00) vs label-price(~:14) — cần verify.

## RỦI RO TREO
- Disk Oracle ~9G; export chưa track bởi CE bg.
- Lưới 15m vs production 1m: train/serve skew. Giữ 15m để đo edge tồn tại; nếu edge sống → re-label 1m kiểm transfer (nặng ×15) trước deploy.
- Edge net-âm dưới endpoint exit → sống/chết phụ thuộc trailing (track A) monetize được đuôi phải không.
- Cost giả định 10bps; funding drag hold dài CHƯA trừ.

## ARTIFACTS (outputs phiên này)
Scripts: `entry-alpha-phase1{,b,c,c2,d,f,g}.py`, `entry-alpha-phase1e-meanrev.py`.
Kết quả: `phase1_entry_alpha.json`, `phase1c2_reprobe.json`, `phase1d_selected_continuation.json`, `phase1f_beyond_reversion.json`, `phase1g_regime_quarter_summary.json`.

## LUẬT NHẮC
- CE-FIRST: mọi việc ≥2 lần → nút/pipeline (`ce kaggle_push/bg_run/...`). Cấm SSH inline quote phức tạp.
- Dispatch job = cuối turn; đọc kết quả turn sau (không poll → tránh vỡ cache ×10-20).
- Model alloc: Opus cho task nhiều bước/side-effect; không Fable 5.
