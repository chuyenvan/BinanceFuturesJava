# PREREG_SHORT_V3_R1 — INTRADAY FADE "bán đỉnh guồng thanh khoản" (1m first-hit)

Ngày 2026-10-02 · research engineer (agent) dưới MASTER Claude · nguồn: `docs/research/PROGRAM_SHORT_V3.md` §R1 (commit `a8eff3fb`).
Chốt TRƯỚC khi đo. Mọi ngưỡng trigger/exit/luật GO chép NGUYÊN từ PROGRAM; phần "bổ sung" chỉ cụ thể hoá cách tính
(dữ liệu, missing, fill, funding, CI) — không thêm ô, không thêm filter. Sau khi thấy số: KHÔNG đổi gì trong file này.

## 1. Chép nguyên PROGRAM §R1
Trigger tại phút t (chỉ dùng ≤ t), coin c:
- `r60 = close_t / close_{t-60} − 1 ≥ +0,08`;
- `volclimax`: Σ quoteVol[t-59..t] ≥ 5 × median của các cửa sổ 60' không chồng trong 24h trước (24 cửa sổ);
- `newhigh`: close_t ≥ max(close[t-1440..t-1]) (đỉnh 24h);
- `cooldown`: không trigger lại cùng coin trong 24h sau một entry.

Entry: SHORT tại close phút t+1 (không tại t). Notional cố định 1 đơn vị/lệnh.
Exit (lưới KHÓA 6 ô, k=6, inflate √(2 ln 6)=1,89): trailing xuống gap g với arm a + SL cứng s + time-stop TS:
- A: (a 3%, g 2%, s 6%) × TS ∈ {4h, 12h, 24h};  B: (a 5%, g 3%, s 10%) × TS ∈ {4h, 12h, 24h}.
- Quy ước cùng nến: SL ưu tiên (bảo thủ); SL/trailing kiểm trên HIGH/LOW 1m; trailing: khi lãi ≥ a thì SL = min_price_since_entry × (1+g).

Chấm: net/lệnh sau phí 0,112% RT + funding exact; CI block 72h NREP 2000 seed 20260905, raw và inflate; theo năm 2022–2025; SL-rate; n.
Báo: net mean/median, CI raw & inflate, theo năm, SL-rate, win%, n, tail (max loss), theo tier quoteVol (LỚN/VỪA/NHỎ, tercile 30d),
theo regime BTC>SMA50 hay không (chỉ báo cáo, không chọn), ret-at-trigger phân phối, số trigger/ngày.
Đối chứng bắt buộc: cùng trigger nhưng vào LONG (nếu long cũng dương ⇒ trigger chỉ là volatility, không phải fade).

**GO-R1 ⇔ ≥1 ô thoả TẤT CẢ:** (G1) net > 0 ngoài CI raw VÀ inflate; (G2) ≥3/4 năm dương; (G3) n ≥ 1500; (G4) SL-rate ≤ 25%;
(G5) ô đó không phải ô duy nhất dương (≥2 ô dương cùng nhánh A hoặc B); (G6) đối chứng long của cùng tập ≤ 0.
Cấm: đổi ngưỡng r60/volclimax/newhigh sau khi thấy số; thêm ô; lọc thêm.

## 2. Dữ liệu
- Giá/volume: Aerospike `test.kline_1m_opt` (127.0.0.1:3222), key `YYYYMMDD-HHMM` = giờ MỞ phút theo TZ+7, bin `data` snappy-raw + protobuf
  {sym: [O,H,L,C,V]} (field 1..5, float32). **V = field 5 = `totalUsdt` = QUOTE volume (USDT)** — xác minh: `DataMigrator.java`
  copy `setTotalUsdt` vào field 5; số đo BTCUSDT phút 2024-03-15 00:00 UTC V = 2,39e7 (≈ USDT, không phải BTC). ⇒ quoteVol = V, không nhân close.
- Thời gian: chỉ số phút m = floor(unix_ms/60000) UTC (giờ mở). Close phút m biết tại (m+1)·60000−1 ms.
- Universe: mọi symbol có trong bản ghi 1m (toàn USDT-M, gồm coin đã delist), trừ stable {USDCUSDT, BUSDUSDT, TUSDUSDT, FDUSDUSDT, USDPUSDT}.
- Funding: `/tmp/fund_cache.npz` (cache funding store dùng ở P0A; 831 sym, 1,81M sự kiện, fundingTime thật tới 2025-12-31 23:00 UTC,
  gồm cả coin kỳ 4h/1h). Sự kiện ts ≤ 0 bỏ.
- Daily quoteVol (cho tier) + BTC close ngày (cho regime): cache P0A `~/claude_master/1002/p0a_cache/qv/*.parquet`
  (Σ field-5 theo ngày UTC từ cùng `kline_1m_opt`, từ 2021-09; cột `lastc` = close phút cuối ngày UTC). Chỉ đọc.
- DEV: trigger t ∈ [2022-01-01 00:00, …] UTC với điều kiện t+1+1440 ≤ 2025-12-31 23:59 UTC (mọi cửa sổ exit, kể cả TS 24h, kết thúc
  ≤ 2025-12-31 23:59 UTC). Stream đọc từ 2021-12-30 (warm-up 1500') tới 2025-12-31 23:59 UTC. 2026 không đọc.

## 3. Định nghĩa chính xác (bổ sung, khoá)
Mảng theo coin trên trục phút: O,H,L,C,QV; phút thiếu bản ghi = NaN (QV thiếu tính 0 trong tổng). `Cf` = close forward-fill.
- **Điều kiện dữ liệu tại t:** coin có bản ghi phút t (C[t] hữu hạn > 0).
- **r60** = C[t] / Cf[t−60] − 1 (Cf[t−60] phải hữu hạn) ≥ 0,08.
- **newhigh:** C[t] ≥ max các close CÓ MẶT trong [t−1440, t−1]; yêu cầu ≥ 1368/1440 (95%) phút có mặt (⇒ coin đã có ≥ ~24h dữ liệu).
- **volclimax:** W0 = Σ QV[t−59..t]. Cửa sổ nền k = 1..24: Wk = Σ QV[t−60k−59 .. t−60k] (24 cửa sổ 60' liền nhau, không chồng, phủ
  [t−1499, t−60], ngay trước cửa sổ hiện tại). Cửa sổ nền hợp lệ nếu ≥ 30/60 phút có mặt; cần ≥ 20/24 cửa sổ hợp lệ;
  Mnen = median các Wk hợp lệ; yêu cầu Mnen > 0 và W0 ≥ 5·Mnen.
- **Ứng viên thô** = (c, t) thoả cả 3 + điều kiện dữ liệu + phút t+1 có bản ghi (giá entry tồn tại).
- **Cooldown:** theo từng coin, duyệt ứng viên theo t tăng; nhận ứng viên nếu chưa có entry trước, hoặc t ≥ t_prev + 1 + 1440
  (24h kể từ phút entry t_prev+1). Tập trigger sau cooldown DÙNG CHUNG cho 6 ô short và 6 ô long (cooldown 24h ≥ TS max ⇒ không chồng lệnh cùng coin).
- **Entry:** P = C[t+1] (assert chỉ số entry = t+1). Mọi feature tính từ lát mảng có cận trên ≤ t.

### Exit SHORT (a, g, s, TS) trên 1m first-hit
runmin₀ = P. Với j = t+2 … t+1+TS theo thứ tự (phút thiếu: bỏ qua kiểm tra):
- mức stop dùng cho phút j tính từ dữ liệu ĐẾN j−1: nếu runmin_{j−1} ≤ P(1−a) (đã arm) thì level = runmin_{j−1}·(1+g) (luôn < P(1+s)),
  ngược lại level = P(1+s);
- nếu H_j ≥ level ⇒ thoát tại fill = max(level, O_j) (gap qua mức ⇒ khớp ở open, bảo thủ); lý do = SL nếu chưa arm, TRAIL nếu đã arm;
- sau đó mới cập nhật runmin_j = min(runmin_{j−1}, L_j) (low cùng nến KHÔNG được dùng để siết trailing cho chính nến đó ⇒ SL/stop ưu tiên).
- không chạm ⇒ TIME: thoát tại Cf[t+1+TS]. pnl_gross = 1 − exit/P.
### Đối chứng LONG (đối xứng, cùng trigger, cùng a/g/s/TS)
runmax₀ = P; arm khi runmax ≥ P(1+a) ⇒ level = runmax·(1−g), ngược lại level = P(1−s); chạm khi L_j ≤ level, fill = min(level, O_j);
TIME tại Cf[t+1+TS]; pnl_gross = exit/P − 1.
### Phí + funding
net = pnl_gross − 0,00112 + F. F_short = +Σ rate các sự kiện funding của coin có fundingTime ∈ (entry_ms, exit_ms], entry_ms = close phút t+1
= (t+2)·60000−1, exit_ms = (j_exit+1)·60000−1 (short NHẬN khi rate>0); F_long = −Σ rate. Kỳ settle theo dữ liệu thật (00/08/16 UTC cho coin 8h,
dày hơn cho coin 4h/1h). Coin không có sự kiện trong store ⇒ F = 0 (báo tỉ lệ). (PROGRAM ghi "pro-rata theo kỳ 8h thực giữ"; giữ ≤24h nên
dùng dòng tiền settle thực — theo chỉ thị MASTER; không chạy biến thể pro-rata.)

### Thống kê
- Theo ô: n, net mean, net median, win% (net>0), SL-rate (tỉ lệ lệnh thoát lý do SL), tỉ lệ TRAIL/TIME, held mean, gross mean, funding mean,
  tail = net min và p1, theo năm UTC của entry (mean net, đếm năm dương 2022..2025).
- CI: block bootstrap trên chuỗi net THEO LỆNH, block = floor(entry_ms / 72h) (cluster theo thời điểm entry), lấy lại block có hoàn lại,
  thống kê Σsum/Σcount, NREP 2000, seed 20260905, phân vị 2,5/97,5 = CI raw. CI inflate: nửa-độ-rộng mỗi phía × 1,89
  (= √(2 ln 6) như PROGRAM ghi; lưu ý: ZK/1,96 = 0,966 < 1 sẽ KHÔNG phải inflate ⇒ dùng hệ số 1,89 nhân trực tiếp, bảo thủ hơn).
- G1: mean > 0 VÀ CI raw lo > 0 VÀ CI inflate lo > 0. G2: ≥3 năm có mean net > 0. G3: n ≥ 1500. G4: SL-rate ≤ 25%.
  G5: trong cùng nhánh (A hoặc B) có ≥2 ô mean net > 0 (kể cả ô đang xét). G6: LONG cùng (a,g,s,TS) trên cùng tập trigger có mean net ≤ 0.
  GO ⇔ ≥1 ô thoả G1..G6. "Ô tốt nhất" để báo theo năm/tier/regime = ô đạt GO có mean cao nhất; nếu không ô nào đạt = ô short có mean cao nhất (chỉ báo cáo).
- Tier (chỉ báo cáo): ngày UTC d của t; qv30 = mean daily quoteVol d−30..d−1 (≥20 ngày có số); xếp hạng mọi coin universe có qv30 ngày d;
  tercile trên = LỚN, giữa = VỪA, dưới = NHỎ; thiếu = NA.
- Regime (chỉ báo cáo): BULL nếu BTC close ngày d−1 > SMA50(close d−50..d−1), ngược lại BEAR.
- Báo thêm: phân phối r60 tại trigger (p10/25/50/75/90/99, max), W0/Mnen (p50/p90), số trigger/ngày (mean, median, p90, max; theo năm),
  số ứng viên thô, số bị cooldown, số mất entry.

## 4. Sanity bắt buộc (phải PASS trước khi báo cáo)
(a) In 10 trigger mẫu (5 đầu tháng thử 2024-03 + 5 ngẫu nhiên seed 20260905 trên full DEV): sym, t UTC, Cf[t−60], C[t], r60, C[t+1]=P,
    max close 24h trước, W0, Mnen, W0/Mnen, kết quả 1 ô — để kiểm tay; ghi vào RESULT.
(b) Assert: chỉ số entry = t+1; hàm feature tham chiếu (loop) nhận mảng CẮT tại t+1 (không có phần tử > t); test nhiễu tương lai:
    thay toàn bộ dữ liệu > t bằng rác cho ≥ 200 ứng viên ⇒ feature/trigger không đổi.
(c) Ngày mẫu = ngày UTC có nhiều ứng viên thô nhất trong tháng thử 2024-03: tính ứng viên bằng (i) vectorized và (ii) loop thuần Python
    ⇒ tập (sym,t) trùng khít và feature lệch tương đối < 1e-5; exit 12 cấu hình (6 short + 6 long) vectorized vs loop ⇒ pnl lệch < 1e-6.
Chạy thử tháng 2024-03 trước (ước thời gian + sanity), rồi full DEV. Per-trade CSV ở `~/claude_master/1002/r1_cache/` (không vào repo).

## 5. Ngoài phạm vi / giới hạn đã biết
Không mô hình slippage tại spike (khớp ở close t+1 và ở mức stop/open); spread/impact thực tế quanh pump có thể lớn hơn đáng kể ⇒ net là
CẬN TRÊN. Không giới hạn vốn/số lệnh đồng thời. Tick xấu (H/L outlier) có thể kích SL giả — không lọc (cấm lọc thêm).
Ý tưởng amend sau khi thấy số chỉ ghi vào mục riêng của RESULT, KHÔNG chạy trong vòng này.
Script: `research/analysis/short_v3_r1_fade.py` → `docs/result/RESULT_SHORT_V3_R1.json` + `.md`.
