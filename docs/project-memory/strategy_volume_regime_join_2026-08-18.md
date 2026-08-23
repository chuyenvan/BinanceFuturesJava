# Test hypothesis volume-shape + regime cho nuôi — join data (2026-08-18)

Test giả thuyết user: (a) label 15m quá ngắn cho nuôi; (b) pattern volume "baseline đều 12-24h → spike đột biến
15-30' trước → 15' gần nhất về trung bình → điều chỉnh xong → trend mạnh tới". Join `wfo_feature_store.csv`
(market-level per-phút 2021-2026, 33 V3Full feat, có sẵn volumeSpike/basketVolSpike/momentum term-structure) vào
`entry_pathstats_g008.csv` (170,790 entry thật × forward path 4h/12h/24h/72h). Script: vol_regime_test.py, vol_regime_test2.py.
⚠️ Raw price excursion, KHÔNG fee/funding — đo edge-shape, không phải PnL net.

## KẾT QUẢ 1: hypothesis volume-shape KHÔNG được ủng hộ
Baseline ALL: retEnd72 +0.109, win72 68.5%, maxAdv72 −0.141.
- Pattern spike≥2 & revert≤1.3 (n=74k, 43% entry): retEnd72 +0.1113, win 69.8% → **+0.2pp ret, +1.3pp win = nhiễu.**
- spike≥3 & revert≤1.2: retEnd72 +0.0949 → TỆ HƠN baseline.
- spike_ratio decile 9 (spike gần đây LỚN nhất): retEnd72 +0.0837, win 60.9%, maxAdv72 −0.151 = XẤU nhất.
- vs_now>2 (đang spike NGAY BÂY GIỜ): retEnd72 +0.060, win 56.6% = xấu.
- Spearman(vs_now, retEnd72) = **−0.049** (yếu, dấu ÂM).
→ Vào NGAY/ngay-sau spike volume = đuổi froth, hơi XẤU. Dấu NGƯỢC với "spike báo trend mạnh". "Revert" thêm ~0.

## KẾT QUẢ 2: lever THẬT tìm được = momentum24H (euphoria filter)
Spearman(retEnd72): **momentum24H −0.196** (mạnh nhất) > momentum15M −0.083 > vs_now −0.049 > momentum1H −0.005.
- momentum24H>0 (thị trường đã chạy lên 24h): retEnd72 **+0.016, win 47.9%**, maxAdv72 −0.189.
- momentum24H≤0: retEnd72 **+0.112, win 69.1%**, maxAdv72 −0.140.
Per-year (ỔN ĐỊNH ở regime nguy hiểm):
| year | m24>0 ret72/win | m24≤0 ret72/win |
|---|---|---|
| 2021 | −0.085 / 38% | +0.104 / 67% |
| 2022 | −0.069 / 24% | +0.075 / 62% |
| 2025 | −0.015 / 45% | +0.136 / 70% |
| 2023 | +0.037 / 67% | +0.047 / 68% (biến mất) |
| 2024 (bull) | +0.299 / 77% | +0.119 / 79% (ĐẢO dấu) |
→ Ở bear/choppy (21/22/25): vào pump khi market đã lên 24h = đảo chiều, giữ = lỗ. Ở bull 2024: ngược lại.
Khớp goforward doc: "bull pump giữ&chạy; crash pump đảo&dump — entry PHẢI biết regime."

## Froth filter (vs_now>2 OR momentum24H>0): bỏ 11.4% entry, gánh 17% bad-loss
KEPT (calm): retEnd72 +0.116, win 70.3%, badloss(ret72<−10%) 13.0% (vs ALL 13.9%). Cải thiện MODEST (+0.7pp ret).

## SYNTHESIS — nối 2 ý của user
- momentum24H ĐÃ là 1 trong 33 feature của gate. Nhưng gate train label **basketMaxGain 15m** (ngắn) → model
  KHÔNG học được "m24>0 → pump này đảo chiều trong 72h". Feature CÓ, nhưng LABEL ngắn khiến nó vô dụng cho
  reversal-avoidance. ĐÂY là chỗ ý "label dài hơn" của user trở nên đúng: relabel horizon dài (24h/72h) để model
  HỌC được reversal signal từ momentum24H → mới bật nuôi an toàn.
- Volume-shape (spike-then-revert) không phải lever. Nếu dùng volume thì chỉ ở dạng FILTER tránh froth (vs_now cao),
  không phải positive signal.

## CAVEAT (flaws-first)
- Raw excursion, chưa net. Exit-sweep đã cho thấy nuôi lỏng SỤP net (−4587) — nên "label dài + nuôi" PHẢI validate
  WFO net-sim, không tin raw.
- Hiệu ứng MODEST; momentum24H>0 chỉ ~2.8% entry → giá trị là feature/regime-scaler liên tục, không phải hard gate.
- Regime-conditional (2024 đảo dấu) → cần regime-relative, không global threshold cứng.

## NEXT khả thi
1. (rẻ) Test label dài: build label maxFav/retEnd 24h/72h cho gate/selector, đo OOS lift của momentum24H dưới label mới.
2. (vừa) WFO A/B: selector/gate relabel 24h + exit nuôi (SL rộng theo ATR) — so PnL net vs config lướt hiện tại.
3. Book B "nuôi trend" tách riêng, chỉ bật khi momentum24H≤0 (không euphoric).

## Files
- /home/ubuntu/vol_regime_test.py, vol_regime_test2.py (Oracle)
- input: wfo_feature_store.csv (gate 33 feat market-level), entry_pathstats_g008.csv (170k entry × path)
