# FEE0_RESCORE — kết quả: tín hiệu "chết vì phí" dưới phí Binance USDC-M (maker 0 / taker 0,04 %)

- Prereg `docs/prereg/PREREG_FEE0_RESCORE.md` commit a2efaa7b (sha256 d79b8199…a6a6), commit TRƯỚC mọi PnL (kể cả V1).
- Code `research/fee0/`: `f0_listing.py`, `f0_download.py`, `f0_step0.py`, `f0_halfspread.py` (bước 0); `f0_common.py`, `f0_run.py` (S1/S7/S8, V1), `f0_q4.py` (Q4), `f0_x14.py`, `f0_gate.py`; validation `f0_v3_indep.py`, `f0_v45.py`; chẩn đoán mô tả `f0_diag.py`.
- Artefact `docs/result/fee0/*.json`.

## Verdict: NO-GO cả 7 / 7. Không có ỨNG VIÊN, không ghép danh mục.

| tín hiệu | C_M1 Sharpe E \| C | C_M1 %/năm E \| C | maxDD C_M1 E \| C | C_M2 E \| C | C_M0 E \| C (lạc quan) | fill W15 E \| C | corr X14 | DSR (N=96) | G1–G6 |
|---|---|---|---|---|---|---|---|---|---|
| S1_BTC 21→23 UTC | −0,33 \| −0,34 | −6,1 \| −4,1 | −39 \| −19 % | −0,59 \| −0,36 | +0,98 \| +1,92 | 0,97 \| 0,95 | +0,07 | 0,00 | 000110 |
| S1_ETH | −0,17 \| +0,85 | −4,2 \| +15,8 | −53 \| −18 % | −0,36 \| +0,60 | +0,85 \| +2,16 | 0,97 \| 0,97 | +0,08 | 0,03 | 000110 |
| S7_BTC cuối tuần | +0,27 \| +0,61 | +9,0 \| +14,2 | −43 \| −32 % | +0,33 \| +0,47 | +0,46 \| +0,65 | 0,97 \| 0,99 | −0,01 | 0,06 | 000110 |
| S7_ETH | +0,32 \| +0,40 | +13,1 \| +13,5 | −53 \| −50 % | +0,25 \| +0,36 | +0,35 \| +0,49 | 0,97 \| 0,99 | −0,03 | 0,05 | 000110 |
| S8_BTC imbalance 4h | −1,95 \| −4,01 | −131 \| −192 | −99 \| −100 % | −2,53 \| −4,76 | +0,08 \| −1,16 | 0,98 \| 0,96 | −0,03 | 0,00 | 000110 |
| S8_ETH | −1,61 \| −2,62 | −136 \| −178 | −100 \| −100 % | −2,06 \| −3,00 | +0,01 \| −0,46 | 0,98 \| 0,97 | −0,01 | 0,00 | 000110 |
| Q4 M15_12h_imb_dev15 (L/S) | −8,31 \| −6,65 | −46 \| −29 | −60 \| −56 % | −10,0 \| −7,7 | +0,65 \| −0,13 | 0,96 \| 0,96 | −0,17 | 0,00 | 000110 |

G1–G6 theo thứ tự (1 = đạt). G4 (corr X14 ≤ 0,3) và G5 (fill ≥ 60 %, dấu không đổi khi W = 5′/30′) đạt ở mọi tín hiệu; G1, G2, G3, G6 trượt ở mọi tín hiệu. Q4 E = 2022–2023, universe E = 5 symbol proxy; C: universe USDC-M PIT, trung vị 7 symbol/mốc đạt quote_volume ≥ 50 000 (42 348 mốc).

Độ nhạy W (C_M1 Sharpe E | C): S1_BTC W5 −0,45 | −0,35, W30 −0,38 | −0,14; S1_ETH W5 −0,12 | +0,80, W30 −0,17 | +0,86; S7_BTC W5/W30 +0,28 | +0,61; S7_ETH W5 +0,29 | +0,37, W30 +0,24 | +0,40.

## Đọc (risk-first)
1. **Phí 0 maker không cứu được tín hiệu nào.** Luật khớp bảo thủ + AS 2 bps + thoát taker 4 bps = ~6 bps/lệnh. Edge thô S1 chỉ ~5 bps/lệnh (BTC: E 5,0, C 6,8 bps) ⇒ âm. Bản C_M0 (maker hai chân, khớp chắc) cho S1 Sharpe 0,98 | 1,92, nhưng đó là giả định không thực tế: thoát đúng 23:00 bằng maker không đảm bảo.
2. **Chi phí chọn lọc của limit xuyên mức là thật.** Lệnh KHÔNG khớp là lệnh giá chạy lên ngay: gross S1_BTC lệnh không khớp +29 bps (E) / +46 bps (C), so với lệnh khớp +4,3 / +4,8 bps (`diag.json`). Tỉ lệ khớp cao (95–99 %), nhưng phần 3–5 % bị lỡ lại chứa phần lãi. Đây là tác động chọn lọc, không phải lỗi.
3. **S7 cuối tuần là tín hiệu duy nhất dương ổn định** (+9…+14 %/năm ở C_M1 cả hai kỳ, Sharpe 0,27–0,61). Nhưng trượt G1/G3/G6: maxDD −32…−53 % khi dùng toàn vốn, DSR 0,06. Funding long ăn ~5–11 bps/lệnh. Không đủ để làm hệ "đều".
4. **S1_ETH C_M1 C = +0,85** nhưng E = −0,17: phân kỳ E/C, không phải edge bền. Lại là chọn hậu kiểm nếu đem ra theo đuổi.
5. **S8 và Q4 không có edge, kể cả gross.** S8 gross E +0,08 | C −1,16. Q4 gross/chân E +0,54 bps, C −2,74 bps (đổi dấu so với E1 2024 USDT-M).
6. G4 đạt ở mọi tín hiệu (corr với X14 trong −0,17…+0,08): đa dạng hoá tốt nếu có edge, nhưng không có edge.

## Bước 0 (chi tiết trong prereg §2)
- **(a) Phí USDC-M.** Chuỗi ưu đãi "limited-time", gia hạn liên tục:
  - 2024-01-03: mở sàn, giảm 10 % so với USDT-M.
  - 2024-04-03 → 2024-07-03: maker 0 / taker 0,017 % (thông báo chính thức Binance).
  - 2025-03: X @BinanceFutures "ZERO maker + 20 % taker discount".
  - Đến 2025-09-03: maker 0 / taker 0,04 % (Coinlive trích thông báo Binance).
  - Cập nhật 2025-09-11: FAQ Binance có liên kết tới thông báo này, nhưng KHÔNG đọc được nội dung.
  - 2026-09-10: Bitsgap (bên thứ ba) ghi 0 / 0,04 %.
  - ⇒ Mức hiện hành và ngày hết hạn **CHƯA XÁC MINH bằng văn bản chính thức**.
- **(b) Symbol.** 40 symbol USDC-M trên Vision (MATICUSDC đã huỷ 2024-09-11). Bar đầu tiên 2024-01-04 (BTC 12:31 UTC). Không có USDC-M trước 2024.
- **(c) Proxy.** BTC/ETH USDC vs USDT: corr 1h 0,9996/0,9998, TE 1h 1,5 bps; lệch mức ±18 bps (tỉ giá USDC/USDT) ⇒ USDT-M làm proxy trước niêm yết.
- **(d) Spread và độ sâu.**
  - Spread đo từ bookTicker 2024Q1: BTC và ETH USDC ~1 tick (hs 0,014 / 0,024 bps). Alt hs 0,5–2,7 bps.
  - Độ sâu ±1 % (bookDepth 2026): BTCUSDC 46–52 tr USD, khoảng 30–35 % so với BTCUSDT.

## Validation
- **V1 PASS.** Tái lập tầng 1 khớp đến 4 chữ số thập phân:
  - Taker: S1 −0,9755 | −0,9286, S7 +0,3032 | +0,4302, S8 −3,1744 | −5,6199; ETH cũng khớp; số lệnh khớp.
  - Maker: S1 +0,20 | +0,78, S7 +0,39 | +0,56 = sw_diag.
- **V2 PASS.**
  - ts int64 ms; lưới exec 1m đủ 3 022 560 bar (assert).
  - USDC BTC/ETH phủ 100 %; moc table ts unique.
  - Q4-E 5 symbol: BTC/ETH/BNB 1 051 200 bar (đủ 730 ngày); SOL/XRP 1 044 000 (thiếu 5 ngày trong raw).
- **V3 PASS.** Script độc lập (Python thuần, zoneinfo, csv; không import pipeline) cho PnL ngày S7_BTC C_M1: max |Δ| = 2,6e-16 trên 2 098 ngày.
- **V4 PASS.** 8 lệnh kiểm tay, gồm 5 lệnh khớp (r khớp đến 1e-16; S7 chênh đúng phần funding) và 3 lệnh không khớp. Trong 3 lệnh không khớp có ca **chạm đúng** P0 (min low = P0 = 43 026,2) ⇒ không khớp, đúng luật strict.
- **V5 PASS.**
  - S8: dấu imb tính trên dữ liệu cắt tại t trùng 200/200.
  - Q4-E: imb_dev15, cửa sổ fwd (chỉ nến ≥ ts+1′) và giá exit tái tính từ raw trùng 150/150.
  - Lần đầu V5 báo 1 lệch lo15. Nguyên nhân là phép kiểm thiếu tháng kế tiếp ở biên tháng (lỗi của phép kiểm, không phải pipeline). Đã sửa phép kiểm.

## Lệch thiết kế (như prereg §8)
1. Q4: kỳ E chỉ 2022–2023, universe E là proxy 5 symbol.
2. Tín hiệu Q4 ở C tính trên kline USDC-M.
3. hs đo ở 2024Q1, áp cho cả kỳ.
4. Funding tính cho mọi tín hiệu.
5. ETH chấm riêng.

Không có lệch nào phát sinh sau khi thấy kết quả.

## Rủi ro / điểm tự nghi ngờ
- **Phí là giả định phản thực tế cho toàn lịch sử.** Ưu đãi có thể kết thúc bất cứ lúc nào. Kết luận NO-GO không phụ thuộc điểm này, vì đã NO-GO ngay cả với phí 0.
- **AS 2 bps lấy từ MM_Q1** (markout 60 s, tier lớn) và áp đồng loạt. Có thể nặng tay với lệnh giữ 2h. Nhưng:
  - Nếu bỏ hẳn AS, lệnh S1_BTC đã khớp có gross 4,3 bps (E) / 4,8 bps (C), so với chi phí thoát 4,0 bps ⇒ net ~+0,3…+0,8 bps/lệnh, tức gần 0. Sharpe ước ~0,1 (ước tay: sd ngày ≈ 5 bps·√365/0,98 ≈ 97 bps theo C_M0; không chạy thêm phép thử).
  - S1 chỉ sống nếu thoát cũng bằng maker và khớp chắc (C_M0), điều không bảo đảm được.
- **Q4 trên USDC-M có ít symbol** (trung vị 7 symbol/mốc). Quintile thực chất là top 1–2 trừ bottom 1–2 ⇒ phép thử Q4 có power thấp, nhưng đã âm cả gross ở C.
- **Đa kiểm định:** ledger 89 + 7 = 96 test. DSR mọi tín hiệu ≤ 0,06.

## Vận hành (nếu sau này vẫn muốn dùng USDC-M, ví dụ cho chân X14 — giảm phí, không phải alpha)
- Hợp đồng USDC-M ký quỹ bằng USDC. Có hai cách:
  - Single-Asset Mode: phải giữ số dư USDC riêng trong ví USDⓈ-M, chuyển USDT → USDC qua spot.
  - Bật Multi-Assets Mode để USDT cross làm margin cho hợp đồng USDC. Chế độ này áp cho toàn tài khoản, chỉ cross. Đây cũng là điều kiện để dùng BFUSD (research_1023).
- Lệch USDC/USDT ±18 bps/ngày là rủi ro tỉ giá nhỏ trên ký quỹ.
- Chỉ 40 symbol có USDC-M. Crash-buy X14 vào alt không có USDC-M thì vẫn phải dùng USDT-M.
- Phí ưu đãi chưa xác minh được hiện hành.

Ledger +7 (tổng 96).
