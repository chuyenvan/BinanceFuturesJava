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
