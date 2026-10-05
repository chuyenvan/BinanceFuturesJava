# PREREG_SHORT_STATE — GATE STATE THEO TỪNG COIN cho SHORT (0-sim trước)

Chốt: **2026-10-01**, branch `module`. Commit **TRƯỚC** đo; sau đo KHÔNG sửa thiết kế.
Hướng MỚI (khác `RESULT_SHORT_REGIME` NULL): gate theo **STATE của từng coin** (market-wide regime đã NULL).
Nền: `RESULT_PUMPDUMP_DETECT` + path-aware **đã NULL** ⇒ chỉ có giá trị nếu dùng đúng **STATE + tier + volume-decay**.

## 1. Ràng buộc
DEV ≤ 2025-12-31 · không `.java`/ONNX/242/LIVE/2026 · không push dữ liệu · **0-sim** (chỉ sim 1m nếu (B) rõ) ·
chỉ `git add` file của mình · output nhỏ · disk ~82 %.

## 2. State EX-ANTE cho `(coin,t)` — tham số CỐ ĐỊNH (không quét mũ)
Từ `CLOSES_1H.bin` (chart ≤ t): `ret7`(168h) · `ret30`(720h) · `vol7`/`vol30`(std lợi suất giờ) ·
`vol_decay = vol7/vol30` · `dd30`(close/đỉnh 720h−1) · `pump_age_d` = số ngày kể từ nến có **ret24h ≥ +15 %**
(`PUMP_X=0,15`). **tier** = hạng `notional` (proxy `Σ V·C` phút, lấy mẫu mỗi **14 ngày** từ Aerospike
`kline_1m_opt`); big-alt ≥ p70, rac ≤ p30. ⚠️ tier xấp xỉ (mẫu 14 ngày) — ghi rõ.

## 3. Forward + luật (0-sim)
Nguồn forward = nhãn `.pb` (universe ticker đầy đủ, 15m grid, `nBars_72h≥288`): `retEnd_24h/72h`, `maxFav_24h/72h`.
- **Tập (B) "xả dần"**: `pump_age_d > 7` **và** `vol_decay < 1,0` **và** `ret30 < 0` **và** `dd30 < −0,15`.
- **Tập (A) "gương thanh khoản"** (nghi AVOID): `pump_age_d ≤ 2` **hoặc** `vol_decay > 1,5`.
- Báo: n · `ret24/72` mean (→ short drift) · **short_net24 = −mean(ret24) − 0,21 %** · **hit-rate** · **tail**
  (`maxFav` mean/p95, tỷ lệ `maxFav ≥ +10 %` = SL-rate) · **theo năm 2022–2025** · **CI95 block-72h**.
- Đối chiếu baseline: short S1 d0 = **−0,033 %/24h**; universe ALL.

## 4. Luật kết luận
**GO** chỉ khi **tập (B)** có short_net24 **> 0 ngoài CI** (raw **và** ×1,21) **và** ≥3/4 năm dương.
Nếu **> 1** biến thể đều GO ⇒ nghi **overfit** (báo rõ). Ngược lại ⇒ **NULL** (chốt đóng short).

## 5. Sản phẩm
`research/analysis/short_state_0sim.py` · `docs/result/RESULT_SHORT_STATE.md` (+`.json`).
