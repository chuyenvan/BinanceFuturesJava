# PROGRAM_SHORT_V3 — Đổi THANG THỜI GIAN và CƠ CHẾ: 3 vòng pre-reg song song

Ngày 2026-10-02 · MASTER Claude · tiếp sau PROGRAM_SHORT_V2 Pha 0 FAIL (`c7a6f4d7`, `c89a84fe`).
Bài học V2: bleed alt là beta+regime, không phải trạng thái coin; gate theo NGÀY không tách được; run LIQ p50 = 2 ngày
⇒ đỉnh pump là sự kiện tính bằng GIỜ. 15 vòng trước đều vào ở nhịp ngày/tick-15' và giữ 1–7 ngày. V3 thử đúng chỗ chưa chạm:
(R1) nhịp giờ, (R2) sự kiện có lịch, (R3) cascade xả. Mỗi vòng có cơ chế "tại sao COIN NÀY giảm".
Chấm chung: net/lệnh sau phí 0,112% RT + funding exact (short nhận khi rate>0, pro-rata theo kỳ 8h thực giữ), CI block
(72h) NREP 2000 seed 20260905, raw và inflate; theo năm 2022–2025; SL-rate; n. Thiếu 1 điều kiện ⇒ NO-GO vòng đó.
DEV 2022-01-01..2025-12-31, 2026 niêm phong. 0 Java trên Oracle. Không sửa .java. Không 242. Lock job nặng (>4G RAM).

## R1 — INTRADAY FADE "bán đỉnh guồng thanh khoản" (1m first-hit) — hướng chính
Dữ liệu: Aerospike `kline_1m_opt` (stream như `short_pathexit_sim.py`), funding store, universe đầy đủ.
Trigger tại phút t (chỉ dùng ≤ t), coin c:
- `r60 = close_t / close_{t-60} − 1 ≥ +0,08`;
- `volclimax`: Σ quoteVol[t-59..t] ≥ 5 × median của các cửa sổ 60' không chồng trong 24h trước (24 cửa sổ);
- `newhigh`: close_t ≥ max(close[t-1440..t-1]) (đỉnh 24h);
- `cooldown`: không trigger lại cùng coin trong 24h sau một entry.
Entry: SHORT tại close phút t+1 (không tại t — tránh look-ahead phút trigger). Notional cố định 1 đơn vị/lệnh.
Exit (lưới KHÓA 6 ô, k=6, inflate √(2 ln 6)=1,89): trailing xuống gap g với arm a + SL cứng s + time-stop TS:
  A: (a 3%, g 2%, s 6%) × TS ∈ {4h, 12h, 24h};  B: (a 5%, g 3%, s 10%) × TS ∈ {4h, 12h, 24h}.
  Quy ước cùng nến: SL ưu tiên (bảo thủ); SL/trailing kiểm trên HIGH/LOW 1m; trailing: khi lãi ≥ a thì SL = min_price_since_entry × (1+g).
Báo: net mean/median, CI raw & inflate, theo năm, SL-rate, win%, n, tail (max loss), theo tier quoteVol (LỚN/VỪA/NHỎ, tercile 30d),
  theo regime BTC>SMA50 hay không (chỉ báo cáo, không chọn), ret-at-trigger phân phối, số trigger/ngày.
Đối chứng bắt buộc: cùng trigger nhưng vào LONG (nếu long cũng dương ⇒ trigger chỉ là volatility, không phải fade).
GO-R1 ⇔ ≥1 ô: net > 0 ngoài CI raw VÀ inflate; ≥3/4 năm dương; n ≥ 1500; SL-rate ≤ 25%; VÀ ô đó không phải ô duy nhất dương
  (≥2 ô dương cùng nhánh A hoặc B) ; VÀ đối chứng long của cùng tập ≤ 0.
Cấm: đổi ngưỡng r60/volclimax/newhigh sau khi thấy số; thêm ô; lọc thêm.

## R2 — NIÊM YẾT MỚI (listing effect) — 0-sim daily + 1h
Định nghĩa: `listing_day` = ngày đầu tiên coin có kline 1m trong Aerospike (hoặc ngày đầu trong CLOSES_1H.bin; ghi nguồn).
Chỉ coin có listing_day trong 2022-01-01..2025-12-24. Đo đường giá so với close ngày D0 (ngày listing, close UTC):
  retEnd và maxFav tại D+1, D+3, D+7, D+14, D+30 (1h closes); pSQ10 theo horizon; funding thật D0..D+7.
Chiến lược KHÓA: short tại close D0 (hoặc D1 nếu D0 thiếu <12h dữ liệu), giữ 7 ngày, SL +15% (1h), phí 0,112, funding exact.
Thêm biến thể KHÓA duy nhất: vào tại close D1 thay D0 (k=2, inflate 1,18).
Báo: n listing/năm, net mean/median, CI (block theo tháng vì n nhỏ, NREP 2000), theo năm, SL-rate, tail; so với ALL cùng ngày (excess).
GO-R2 ⇔ net > 0 ngoài CI raw & inflate; ≥3/4 năm; n ≥ 120 listing; excess vs ALL cùng ngày > 0.

## R3 — BREAKDOWN MOMENTUM (cascade xả) — 0-sim daily + 1h (tái dùng harness P0A)
Trạng thái BRK tại ngày d (causal): `close_d ≤ min(close[d-30..d-1])` (phá đáy 30 ngày) VÀ `quoteVol_d ≥ 2 × median quoteVol[d-30..d-1]`
  VÀ `close_d / close_{d-1} − 1 ≤ −0,05`. Cooldown 7 ngày/coin.
Giữ T ∈ {3d, 7d} (k=2), SL +10% (1h), phí 0,112, funding exact. Đối chứng: ALL cùng ngày; và BRK-không-volume (chỉ phá đáy) để tách vai trò volume.
Báo: như P0A (bleed, pSQ10, netproxy, cover, theo năm, CI raw/inflate 1,18) + excess vs ALL cùng ngày.
GO-R3 ⇔ netproxy_T > +0,5% ngoài CI raw & inflate; ≥3/4 năm; excess vs ALL > +0,3%; pSQ10 ≤ 0,8 × pSQ10(ALL).

## Sau vòng
R1 GO ⇒ Pha kế: thêm filter/ranking (OI, funding, taker ratio, listing-age) như selector, rồi sim sổ. R2/R3 GO ⇒ ghép làm gate/sự kiện cho R1.
Cả 3 NO-GO ⇒ short ở nhịp giờ/sự kiện/cascade cũng đóng trên dữ liệu hiện có; chỉ còn data mới (unlock calendar, L2/liquidation forward).

## ADDENDUM 1 (2026-10-02, sau R1/R2/R3) — R1b selector tại trigger, R2b listing chuẩn 1m
Kết quả: R1 `3fea4f50` NO-GO nhưng lệch chiều THẬT (short + cả 6 ô, long − cả 6 ô; B24 net +0,17%, 4/4 năm, CI raw [−0,03;+0,37]);
R2 `38a99bca` GO theo luật 1h nhưng post-hoc SL 1m-high ⇒ CI chứa 0; R3 `0e7aee0b` NO-GO (capitulation → hồi). ⇒ Đi tiếp đúng cách long: thêm SELECTOR.

### R1b — SELECTOR tại phút trigger (model tier + per-trade net), tái dùng per-trade R1 (`~/claude_master/1002/r1_cache/`)
Tập: đúng n = 10 991 trigger của R1 (không đổi trigger). Target: `net_B24` (ô B24 của R1) — chính; `net_B12` phụ (báo cáo).
Feature tại t (chỉ dùng ≤ t), KHÓA danh sách (bỏ feature nếu dữ liệu không có, ghi rõ, không thay bằng feature khác):
  f1 `r60`; f2 `r15` (close_t/close_{t-15}−1); f3 `ext24 = close_t/close_{t-1440}−1`; f4 `volratio = W0/M` của volclimax; f5 `wick = (high_t − close_t)/(high_t − low_t)` của nến t (nếu có H/L);
  f6 `fund_now` (rate kỳ hiện hành/dự kiến tại t, dấu: rate<0 ⇒ short trả); f7 `fund_sign` (= f6<0); f8 `dOI_60` (OI_t/OI_{t-60}−1 từ derivs_store nếu có độ phân giải ≤5'); f9 `takerLS` (long/short ratio nếu có);
  f10 `tier` (tercile quoteVol 30d); f11 `listing_age` (ngày từ listing_day, cap 365); f12 `btc_bull` (BTC>SMA50 ngày); f13 `btc_r60` (BTC 60' cùng lúc); f14 `n_trig_day` (số trigger khác trong 24h trước — đo "ngày sập/pump toàn thị trường").
Model: LightGBM (nếu không có thì sklearn HistGradientBoosting) hồi quy `net_B24`, tham số CỐ ĐỊNH (num_leaves 15, lr 0,05, 300 cây, min_child 100, feature_fraction 0,8, seed 20260905) — KHÔNG tune.
WFO theo NỬA NĂM: fold h ∈ {2023H1, 2023H2, 2024H1, 2024H2, 2025H1, 2025H2}: train trên mọi trigger có exit kết thúc trước đầu h − 72h, test h. (2022 chỉ train.)
Chấm (trên ghép 6 fold OOS): rank-IC(score, net_B24) theo fold; net tercile-TOP vs ALL; SL-rate tercile-top; theo năm; CI block-72h NREP 2000 seed 20260905 trên tercile-top, raw và inflate k=2 (B24 chính + B12 phụ) = 1,18; stress: net tercile-top − 0,10% (slippage spike) ; đối chứng: permutation (xáo nhãn 1 lần seed 20260905) ⇒ IC phải ≈ 0.
Báo thêm: importance; net theo decile score; ablation KHÓA 3 nhóm (bỏ f6–f9 "crowding"; bỏ f10–f14 "context"; chỉ f1–f5 "giá/vol") — chỉ báo cáo, không chọn.
GO-R1b ⇔ tất cả: rank-IC OOS > +0,05 và dương ≥5/6 fold; net tercile-top (B24) > 0 ngoài CI raw & inflate; ≥3/4 năm (2023–2025 + 2022-không-tính ⇒ 3/3); SL-rate tercile-top ≤ 25%; stress −0,10% vẫn > 0 ở điểm ước lượng; permutation IC ∈ [−0,02;+0,02].
GO ⇒ Pha kế: sim SỔ short (vốn, size, đồng thời, MTM phút) + đo slippage thật tại spike từ 1m volume; rồi engine.

### R2b — LISTING chuẩn 1m (cùng tham số R2, đổi CHUẨN đo)
Chiến lược y hệt R2 (short close D0/D1, 7d, SL +15%, phí 0,112, funding exact) nhưng SL kiểm trên HIGH 1m (fill tại mức SL; nếu open 1m vượt SL thì fill tại open). k=2 (D0/D1), inflate 1,18. Thêm: cột "bỏ 10% lệnh tốt nhất" (fragility), và SL-rate.
GO-R2b ⇔ net > 0 ngoài CI raw & inflate; ≥3/4 năm; n ≥ 120; excess vs ALL > 0; VÀ "bỏ 10% tốt nhất" vẫn > −0,5% (không sống chỉ nhờ đuôi).
Ghi rõ survivorship (file không có coin delist 2025) — chiều lệch: coin delist thường sập ⇒ thiếu chúng làm KÉM short (bias chống lại chiến lược), nêu nhưng không "sửa".

## ADDENDUM 2 (2026-10-02, sau R1b/R2b NO-GO) — R1c: lớp EXECUTION của fade (vòng cuối trên dữ liệu hiện có)
R1b `f4bfba27`: 13 feature tại t không tách continuation (SL-rate ~28% mọi tercile, IC OOS 0,019). R2b `53a2479f`: listing NO-GO dưới chuẩn 1m.
Phần còn lại chưa chạm ở R1: (i) phí taker 0,112% RT ăn 35% gross; (ii) entry tại close t+1 = đúng điểm spike; (iii) mean nhánh B tăng theo TS (4h→24h).
### R1c — 2×2 ô KHÓA (k=4, inflate √(2 ln 4)=1,67), cùng trigger R1 (n=10 991), cùng exit nhánh B (arm 5%, gap 3%, SL +10%)
Entry E ∈ {TAKER: short tại close t+1, phí vào 0,056% (nửa RT R1) ; LIMIT: đặt sell limit tại close_t × (1+δ), δ = 0,7%, hiệu lực 15 phút (t+1..t+15), fill khi high_1m ≥ giá limit (fill tại giá limit), phí vào MAKER 0,02%; không fill ⇒ không lệnh (ghi fill-rate)}.
Time-stop TS ∈ {24h, 48h}. Phí ra taker 0,056% mọi ô. Funding exact. Slippage: cột stress −0,10%/lệnh (ghi cả raw & stress).
Lưu ý so sánh: ô LIMIT có tập lệnh con (chỉ lệnh fill) ⇒ báo thêm ô TAKER trên ĐÚNG tập con fill để tách "chọn lệnh" khỏi "giá vào".
GO-R1c ⇔ ≥1 ô: net > 0 ngoài CI raw & inflate; ≥3/4 năm; n ≥ 1500; SL-rate ≤ 25%; stress −0,10% > 0; đối chứng LONG cùng ô ≤ 0.
NO-GO ⇒ ĐÓNG short trên dữ liệu hiện có (20 vòng pre-reg); giữ R1 như "tín hiệu mỏng có thật" để kiểm forward khi có fill thật/L2.

## ADDENDUM 3 (2026-10-02, sau R1c) — R1d: CONFIRMATION ENTRY (chờ 15' không đỉnh mới rồi mới vào)
Nguồn giả thuyết (POST-HOC, ghi rõ): R1c `e7c3e09d` cho thấy tập trigger mà high[t+1..t+15] < close_t×1,007 (limit không fill, 2 703 lệnh)
có TAKER net ≈ +1,5%/lệnh, còn tập fill −0,27%. Tức edge của fade nằm ở lệnh ĐẢO CHIỀU NGAY sau spike; thông tin đó không có tại t
nhưng CÓ tại t+15 (causal). Vì giả thuyết sinh ra sau khi thấy số, bar cao hơn: bắt buộc qua CI inflate, k=2, và báo cả stress.
### R1d — 2 ô KHÓA (k=2, inflate 1,18), cùng trigger R1 (tập 10 977 của R1c), exit nhánh B (arm 5%, gap 3%, SL +10%, TS 24h tính từ entry)
Điều kiện xác nhận tại t+W: `max(high[t+1..t+W]) < close_t × (1+δ)`, δ = 0,7% (giữ nguyên R1c, KHÔNG tune); W ∈ {15, 30} phút.
Entry: short TAKER tại close t+W+1 (phí vào 0,056%, ra 0,056%); funding exact; cooldown như R1. Không điều kiện ⇒ không lệnh (ghi tỉ lệ vào lệnh).
Báo: 2 ô (net mean/median, CI raw & inflate, theo năm, SL-rate, win, n, tail, stress −0,10%); đối chứng (a) LONG mirror cùng điều kiện (low không thủng close_t×(1−δ) ⇒ long tại t+W+1) phải ≤ 0; (b) tập BỊ LOẠI (có đỉnh mới) short tại t+W+1 — kỳ vọng xấu hơn rõ; (c) "no-fill" R1c vào tại t+1 (+1,5%) để thấy phần edge mất đi do vào trễ W phút.
GO-R1d ⇔ ≥1 ô: net > 0 ngoài CI raw VÀ inflate; ≥3/4 năm; n ≥ 1500; SL-rate ≤ 25%; stress −0,10% > 0; LONG mirror ≤ 0; tập bị loại < ô chính.
GO ⇒ Pha kế: sim SỔ (vốn/size/đồng thời/MTM) + slippage từ volume 1m; sau đó engine Java (PLAN_SHORT_ENGINE). NO-GO ⇒ đóng short trên dữ liệu hiện có.
