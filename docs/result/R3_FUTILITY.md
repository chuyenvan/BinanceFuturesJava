# R3 G3 MTF-OR + R3b B2 MEAN60 — futility sau 4 seed (42/7/21/99) — 2026-11-11 — CẢ HAI DỪNG

Hợp lệ: G0 (jar R3, Aerospike) và G0' (jar AS-FILE d10bdbae) và G0s (jar SMOOTH 26581b54, smooth TẮT) đều **byte-identical n4f-b0-a1** (printDone md5 d03d320d, equity_summary trùng); G0'/G0s: mapper 863 + funding 831/2 394 587 từ FILE, 0 lần chạm Aerospike, không preflight TCP. MTM: missing 0, ok, đối chứng dd_dev −22,2029 (lệch 7,6e-7 pp). B2: override SMOOTH 60:48 + PCT 0.999968052 vào profile, result ok 4/4.
Chấm `research/r3_gate/r3_score.py`: CAGR từ equity MTM cuối ngày (+07); DD = dd_dev phút (cửa sổ DEV) hoặc DD equity cuối ngày (cửa sổ 2023–25); Calmar = CAGR/|DD|. Raw `docs/result/r3_g3_futility.json`, `r3b_b2_futility.json`.

## G3 MTF-OR (prereg b901016e, DEV 2022–25) — ≥2/4 ΔCalmar ≤ 0 ⇒ **DỪNG**
| seed | ΔCalmar | ΔCAGR22 (pp) | ΔmaxDD (pp, + = nông hơn) | leg G3 / A0 |
|---|---|---|---|---|
| 42 | −0,052 | −8,20 | +4,11 | 3 256 / 3 935 |
| 7 | −0,093 | −7,01 | +3,12 | 3 389 / 4 037 |
| 21 | +0,180 | −5,78 | +5,97 | 3 436 / 4 030 |
| 99 | +0,069 | −5,62 | +3,57 | 3 321 / 4 111 |
Đọc: ít lệnh hơn 16–19 % (offline quota 1,05 nhưng sim ít hơn), lợi nhuận thấp hơn mọi năm 2023–25, DD nông hơn ⇒ Calmar ~ hoà. HO 2026 ΔPnL âm 4/4.

## R3b B2 MEAN60 (prereg 3ea5df40, chấm 2023–25) — 4/4 ΔCalmar ≤ 0 ⇒ **DỪNG**
| seed | ΔCalmar | ΔCAGR (pp) | ΔmaxDD (pp) | leg B2 / A0 |
|---|---|---|---|---|
| 42 | −7,01 (3,95 vs 10,96) | −21,81 | −2,57 | 2 610 / 3 935 |
| 7 | −7,06 | −21,64 | −2,72 | 2 482 / 4 037 |
| 21 | −5,43 | −20,74 | −1,89 | 2 510 / 4 030 |
| 99 | −7,98 | −25,26 | −2,79 | 2 501 / 4 111 |
Đọc: lệnh −36–39 % dù quota offline 1,13 (pass dồn cụm ⇒ va trần U_MAX/skipFull — đúng rủi ro đã khai §8), CAGR −21–25 pp, DD sâu hơn ⇒ khớp prior âm (trễ vào).
Không chạy 4 seed còn lại; không đổi luật/tham số.
