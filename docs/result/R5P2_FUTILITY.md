# R5P2 MAX15 gate — futility sau 4 seed (prereg PREREG_R5P2_MAX15_GATE f2222d05) — 2026-11-12: **M1 DỪNG (3/4 ΔCalmar ≤ 0)**

Hợp lệ: G0q (jar af97f2ae, mọi cờ tắt) byte-identical n4f-b0-a1 (printDone md5 d03d320d, equity_summary trùng), mapper 863 + funding 831/2 394 587 từ FILE, 0 lần chạm Aerospike. 8 run: result ok, jar sha khớp, override (pct, SMOOTH 15:12 max, Q_MINUTE) vào profile, AS_FILE OK; MTM r3-mtm-r5a ok, missing 0, đối chứng khớp. Log sim M1: SMOOTH agg=max noCov=0.
Chấm `research/r3_gate/r3_score.py` (CAGR22 equity MTM cuối ngày; maxDD MTM phút DEV); báo cáo `research/r3_gate/r5p2_report.py`. pct: M1 0.999955654, M0 0.999949515 (`r5p2_iso.json`, 4df182c5).

| arm | seed | ΔCalmar | ΔCAGR22 (pp) | ΔmaxDD (pp, + nông hơn) | leg / A0 | leg năm 22/23/24/25 ÷A0 | skipFull arm / A0 | trễ trung vị (p25–p75), bắt đợt A0 |
|---|---|---|---|---|---|---|---|---|
| M1 | 42 | −0,400 | −9,40 | +0,38 | 3 062 / 3 935 | 0,90/0,74/0,73/0,78 | 0 / 0,4 % | 1′ (0–6), 70,6 % |
| M1 | 7 | +0,196 | −5,74 | +5,48 | 2 784 / 4 037 | 0,67/0,61/0,72/0,79 | 0 / 3,8 % | 2′ (0–9), 59,9 % |
| M1 | 21 | −0,177 | −8,39 | +2,97 | 3 101 / 4 030 | 0,82/0,76/0,72/0,82 | 0 / 20,4 % | 1′ (0–7), 70,1 % |
| M1 | 99 | −0,445 | −13,08 | +2,40 | 2 958 / 4 111 | 0,70/0,70/0,67/0,73 | 0 / 0,4 % | 2′ (0–9), 66,5 % |
| M0 | 42 | +0,013 | +0,36 | −0,04 | 3 924 / 3 935 | 1,01/1,01/1,01/1,01 | 0,4 / 0,4 % | 0′, 100 % |
| M0 | 7 | −0,021 | −0,47 | 0,00 | 4 063 / 4 037 | 1,00/1,01/1,01/1,01 | 3,8 / 3,8 % | 0′, 100 % |
| M0 | 21 | +0,006 | +0,10 | +0,03 | 4 062 / 4 030 | 1,00/1,01/1,01/1,03 | 20,3 / 20,4 % | 0′, 100 % |
| M0 | 99 | −0,010 | −0,22 | 0,00 | 4 125 / 4 111 | 1,01/1,01/1,00/1,00 | 0,4 / 0,4 % | 0′, 99,5 % |
Quota offline (cell, median 8 seed) M1 22/23/24/25 = 0,99/1,10/1,07/0,91; M0 1,01/1,01/1,01/1,02. skipFull = tỉ lệ ứng viên PREDICT bị bỏ vì sổ đầy / (pass + skipFull) từ log GATE-RATIO.

Kết luận theo luật: M1 có 3/4 seed ΔCalmar ≤ 0 ⇒ **DỪNG**, không chạy 4 seed còn lại. M1 vào ít hơn 18–31 % (dù quota offline ≈1) ⇒ CAGR22 −5,7…−13,1 pp; ΔPnL 2023–25 âm mọi seed; DD nông hơn. HO 2026 (mô tả) ΔPnL âm 4/4.
M0 (chẩn đoán): q theo phút một mình gần như KHÔNG đổi gì (leg ±1 %, ΔCalmar −0,02…+0,01, cùng phút vào) ⇒ tác động của M1 đến từ tín hiệu MAX15, không phải nhịp q.
Ghi chú (suy đoán): MAX15 làm r̃ dai 15′ ⇒ q phút nâng nhanh trong đợt ⇒ ít ô pass hơn ở phút đỉnh; ô cell offline không chuyển thành leg do coin đã giữ/K-cap.
