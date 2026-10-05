# PREREG_SHORT_V2_P0A — State map (Pha 0A của PROGRAM_SHORT_V2)

Ngày 2026-10-02 · Chương trình: `docs/research/PROGRAM_SHORT_V2.md` @ d1057bd1 · Executor: research agent · MASTER: Claude.
Pre-reg này commit TRƯỚC khi đo bất kỳ outcome nào. Chỉ đã probe định dạng/độ phủ dữ liệu (không đọc forward return).

## 1. Số quyết định (chép nguyên §1 chương trình)
Short thua không vì thiếu bleed mà vì đuôi phải. Mọi pha chấm bằng bộ 4 số trên cùng cửa sổ giữ T:
- `bleed`  = mean/median `retEnd_T` (âm là tốt), theo năm.
- `pSQ10`, `pSQ20` = P(`maxFav_T` ≥ +10% / +20%) (xác suất bị squeeze; 1h closes ⇒ cận DƯỚI, ghi rõ).
- `netproxy_T` = E[−retEnd_T | không SL]·(1−pSQ10) − (0,10+0,002)·pSQ10 − 0,112% + funding THẬT của chính coin trong T (short nhận khi rate>0; cắt tại thời điểm SL nếu SL).
- `cover` = % coin-ngày DEV thuộc trạng thái (gate không có tác dụng nếu cover < 3%).
Ngưỡng kinh tế cố định: cần `netproxy_7d` > +0,5%/lệnh (≈ 4,5× phí) để còn chỗ cho slippage/liquidation chưa mô hình.

## 2. Kill-criterion 0A (chép nguyên §2)
KILL nếu KHÔNG trạng thái nào có cover ≥3% và `netproxy_7d` > +0,5% ở ≥3/4 năm (2022–2025) với CI block-7d
(k = số trạng thái×T, inflate √(2 ln k)) ngoài 0.

Cách áp (cố định, không đổi sau khi thấy số). Ứng viên = {LIQ, BTCF, BLEED, FLAT, BLEED′}. Một ứng viên PASS khi đồng thời:
- C1 `cover` ≥ 3% (toàn DEV);
- C2 `netproxy_7d` (điểm, theo năm entry) > +0,5% ở ≥ 3/4 năm 2022, 2023, 2024, 2025;
- C3 CI 95% block-7d của `netproxy_7d` toàn DEV có cận dưới > 0 — báo RAW và INFLATE.
Verdict: PASS nếu ≥1 ứng viên PASS với CI INFLATE; "PASS-raw/FAIL-inflate" nếu chỉ đạt với CI RAW; ngược lại FAIL (= KILL chương trình).

## 3. Định nghĩa trạng thái (chép nguyên §3; ngưỡng CỐ ĐỊNH)
Nguồn: ticker ngày toàn universe (close, quoteVolume), 1h closes (`CLOSES_1H.bin`) cho maxFav, funding store, OI nếu có (phụ), BTC ngày.
- `hi60 = max(close[d-60..d])`, `lo60 = min(close[d-60..d])`; `run_up = hi60/lo60 − 1`; `age_hi = d − argmax` (ngày từ đỉnh 60d); `dd_hi = close/hi60 − 1`.
- `tsh = turnover share` = quoteVol_d / Σ_universe quoteVol_d; `tsh_z = (log tsh_d − mean log tsh[d-90..d-1]) / sd` (z so với CHÍNH NÓ) ; `tsh_rank = rank cross-section của tsh_z`.
- `beta60` = β(ret_coin, ret_BTC) OLS 60 ngày; `tier` = tercile quoteVol trung bình 30d (LỚN/VỪA/NHỎ) cross-section.
- `bull` = BTC close > SMA50 BTC (regime thị trường thô, 1 định nghĩa, không quét).
Trạng thái (ưu tiên theo thứ tự; mỗi coin-ngày đúng 1 trạng thái):
1. **LIQ** (đang trong guồng thanh khoản): `tsh_z ≥ 1,5` HOẶC (`run_up ≥ 0,5` VÀ `age_hi ≤ 10`).
2. **BTCF** (alt lớn theo BTC): `tier = LỚN` VÀ `beta60 ≥ 0,8`.
3. **BLEED** (xả dần): `run_up ≥ 0,3` VÀ `age_hi ∈ [11, 60]` VÀ `dd_hi ≤ −0,15` VÀ `tsh_z ≤ 0` (thanh khoản đã rút).
4. **FLAT**: còn lại.
Biến thể cho phép (k=2, khai TRƯỚC): BLEED′ = BLEED ∧ ¬bull. Không ngưỡng nào khác được đổi sau khi thấy số.
Thời lượng chu kỳ: phân phối độ dài run LIQ và BLEED (ngày), theo tier — để kiểm trực tiếp mệnh đề "chu kỳ tăng ngắn".

## 4. Nguồn dữ liệu (đã xác minh định dạng 2026-10-02, chưa đọc outcome)
- **1h closes**: `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (struct `>i8 ts, >i2 sym, >f4 close`; 10 322 386 dòng, 627 sym,
  2021-01-01 01:00 → 2026-01-01 00:00 UTC). `ts` = thời điểm close được biết (đã đối chiếu: BTC ts 2023-01-01 00:00 = 16537,6
  = close phút cuối 23:59 UTC của Aerospike 1m). Sym id → tên: `/home/ubuntu/claudedata/oi/symbol_map.csv`.
- **quoteVolume ngày + universe**: Aerospike `test.kline_1m_opt` (127.0.0.1:3222), key `yyyyMMdd-HHmm` giờ GMT+7 = open phút,
  bin `data` = snappy-raw(`MinuteDataFinal` proto: map symbol → {open,high,low,close(f4),totalUsdt(f5)}); parse bằng
  `parse_all_min` của `research/analysis/short_state_0sim.py`. `quoteVol_d` = Σ totalUsdt 1440 phút của ngày UTC d
  (key d 07:00 → d+1 06:59 GMT+7). Universe ngày d = các symbol có mặt trong các record phút của ngày d (590 sym cuối 2025;
  khớp CLOSES_1H trừ 2). Đọc từ 2021-09-01 (warm-up ≥ 90 ngày trước 2022-01-01). Ghi chú: thư mục `ticker_*.bin.gz`
  (Java-serialized) cùng nội dung 1m nhưng không đọc được hiệu quả bằng Python ⇒ dùng Aerospike 1m (cùng gốc dữ liệu).
- **Daily close** của ngày d = CLOSES_1H tại ts = (d+1) 00:00 UTC (= close phút 23:59 UTC ngày d). BTC = BTCUSDT cùng nguồn.
- **Funding**: `/tmp/fund_cache.npz` (syms/ts/rt/sid; scan Aerospike `test.funding_data` bởi `funding_sign_reconcile.py`;
  đọc theo lớp `Fund` của `short_v3_score.py`). Phủ 590/590 sym universe cuối 2025. Quy ước: rate > 0 ⇒ SHORT NHẬN.
- OI: KHÔNG dùng (phụ, bỏ để giữ đơn giản).

## 5. Chi tiết triển khai (chốt trước khi đo)
**Đơn vị quan sát** = coin-ngày d ∈ [2022-01-01, 2025-12-31] (ngày UTC): 1 "lệnh" short giả định vào tại close ngày d
(t0 = (d+1) 00:00 UTC, giá P0 = daily close), giữ T ∈ {3, 7, 14} ngày, exit t0 + 24T giờ. Chỉ giữ quan sát có
t0 + 24T h ≤ 2026-01-01 00:00 UTC (cửa sổ kết thúc ≤ 2025-12-31 23:59:59; 2026 không chạm).
**Tập coin**: symbol kết thúc `USDT`, không chứa `_`; loại BTCUSDT (benchmark, vẫn nằm trong mẫu số Σ quoteVol) và
stable {USDCUSDT, BUSDUSDT, TUSDUSDT, FDUSDUSDT, USDPUSDT}.
**Chỉ báo tại d** (chỉ dùng ngày ≤ d, lưới ngày lịch đầy đủ, ngày thiếu = NaN):
- hi60/lo60 trên 61 close [d-60..d], yêu cầu đủ 61 giá trị; `age_hi` = d − ngày của đỉnh GẦN NHẤT đạt hi60.
- `tsh_z`: mean/sd(ddof=1) của log tsh trên [d-90..d-1], yêu cầu ≥ 60/90 giá trị hợp lệ và sd > 0.
- `beta60` = cov/var của 60 log-return ngày [d-59..d] coin vs BTC, yêu cầu ≥ 45/60 cặp hợp lệ.
- `tier`: mean quoteVol [d-29..d] (≥ 20/30 hợp lệ), tercile cross-section ngày d trên tập coin có giá trị:
  LỚN = rank pct > 2/3, NHỎ = ≤ 1/3, VỪA còn lại.
- `bull_d` = BTC close_d > mean(BTC close [d-49..d]).
Coin-ngày thiếu bất kỳ chỉ báo nào ⇒ trạng thái NA (loại khỏi mọi bảng; báo số lượng). ALL = hợp 4 trạng thái.
**Forward (1h closes)**: ma trận dày giờ × sym. Với lệnh (coin, t0, T): đường giá c_k = close tại t0 + k·1h, k = 1..24T.
- `maxFav_T` = max_k c_k / P0 − 1 (bỏ NaN); `retEnd_T` = c_{24T}/P0 − 1 (nếu c_{24T} NaN: close hợp lệ cuối cùng trong
  cửa sổ — coin delist/gap; đếm `n_trunc`; không có close forward nào ⇒ loại).
- SL: k* = giờ đầu tiên c_k ≥ 1,10·P0 (⇔ maxFav_T ≥ 10% ⇒ đồng nhất với pSQ10). Exit tại t0 + k*·1h.
- `fund` = Σ rate của chính coin có ts ∈ (t0, t_exit] (t_exit = SL time nếu SL, ngược lại t0+24T h); coin không có trong
  store ⇒ 0 và đếm.
- pnl lệnh: `pnl = (−retEnd_T nếu không SL; −0,102 nếu SL) − 0,00112 + fund`. `netproxy_T` = mean(pnl) — đúng bằng công
  thức §1 (E[−ret|¬SL](1−pSQ10) − 0,102·pSQ10 − 0,112% + E[fund]).
- `bleed` = mean/median retEnd_T THÔ (không cắt SL). `P(ret≤−10%)` trên retEnd_T thô. `excess` = retEnd_T − mean
  retEnd_T của ALL cùng ngày d (tách gate khỏi beta rổ).
**CI**: bootstrap khối 7 ngày lịch liên tiếp (cluster theo thời gian), NREP 2000, seed 20260905; mỗi rep rút khối có
hoàn lại, thống kê = Σpnl/Σn của các khối rút (pooled mean, nhất quán với điểm ước lượng). CI raw = percentile 2,5/97,5.
k = 4 trạng thái × 3 T + BLEED′ = 13 ⇒ z_k = √(2 ln 13) = 2,265; CI inflate = mean − (mean−lo)·(2,265/1,960),
mean + (hi−mean)·(2,265/1,960). Ghi cả raw lẫn inflate.
**Run length**: run = chuỗi ngày lịch liên tiếp cùng coin cùng trạng thái (ngày NA/thiếu cắt run); run tính nếu ngày đầu
∈ DEV; run chạm 2025-12-31 bị kiểm duyệt phải (báo số lượng). Tier của run = tier ngày đầu. Báo p25/p50/p75, n.
**Chuyển trạng thái**: P(s_{d+1} | s_d) trên cặp ngày liên tiếp cùng coin, cả 2 ngày hợp lệ.

## 6. Sanity BẮT BUỘC (chạy và in TRƯỚC bảng chính)
- S-a: số coin-ngày DEV hợp lệ, số NA, % mỗi trạng thái theo năm 2022–2025; số lệnh/T, `n_trunc`, % lệnh có funding.
- S-b: causal — với 3 ngày cắt (2022-06-15, 2023-09-01, 2025-03-10): thay toàn bộ close/quoteVol SAU ngày cắt bằng giá trị
  ngẫu nhiên, tính lại chỉ báo + trạng thái; assert trạng thái và chỉ báo của mọi ngày ≤ ngày cắt GIỐNG HỆT bản gốc.
- S-c: in tay chuỗi 60 ngày của CFXUSDT 2023-02-01 → 2023-04-01 (close, tsh_z, run_up, age_hi, dd_hi, tier, beta60,
  trạng thái) — pump nổi tiếng: kỳ vọng LIQ trong pha pump, sau đó chuyển BLEED/FLAT.
- S-d: BTC daily close khớp CLOSES_1H; đối chiếu Σ tsh = 1 mỗi ngày.
Nếu S-b fail ⇒ dừng, sửa bug, không đọc bảng chính.

## 7. Bảng đầu ra cố định
- **A** [LIQ, BTCF, BLEED, BLEED′, FLAT, ALL] × T ∈ {3,7,14}: n, cover, bleed mean, bleed median, excess mean, pSQ10, pSQ20,
  P(ret≤−10%), funding mean, netproxy, CI raw, CI inflate.
- **B** theo năm 2022–2025, mỗi [trạng thái × T]: n, bleed mean, pSQ10, funding mean, netproxy (+ CI raw block-7d cho T=7).
- **C** độ dài run LIQ, BLEED: p25/p50/p75/n theo tier (LỚN/VỪA/NHỎ/tất cả), số run kiểm duyệt.
- **D** ma trận chuyển trạng thái 4×4.
- **E** BLEED, T=7: netproxy/bleed/pSQ10 theo tier và theo bull/¬bull (bull/¬bull ¬bull = BLEED′).
- **F** bảng điều kiện kill-criterion C1/C2/C3(raw)/C3(inflate) cho từng ứng viên → verdict.
Output: `research/analysis/short_v2_p0a_statemap.py` → `docs/result/RESULT_SHORT_V2_P0A.json` + `.md`.
Cache dữ liệu trung gian (ngoài repo, không push): `/home/ubuntu/claude_master/1002/p0a_cache/`.

## 8. Cấm
Không thêm ngưỡng/biến thể/T sau khi thấy số. "Giá như đổi X" ⇒ ghi mục "đề xuất amend cho pha sau", KHÔNG chạy.
Không đọc 2026. Không Java. Không sửa `.java`. Lock `~/claude_master/1002/oracle_heavy.lock` cho job > 1 phút.
