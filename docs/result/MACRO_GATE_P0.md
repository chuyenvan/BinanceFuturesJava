# MACRO_GATE Pha 0 — KẾT QUẢ (chỉ đo, không sim)

Prereg vz_e1_wt **24104dd6** (PREREG_MACRO_GATE.md md5 4e45a1bb). SELECTION **cd76944b** (MACRO_GATE_SELECTION.md md5 fa8ccf92, selection.json 46052b47). Code `research/macro_gate/` (macro.py md5 a3d96852, fetch.py, run_job.sh), số liệu `docs/result/macro_gate_p0/{data,selection,confirm}.json`.

## VERDICT: **ĐÓNG** — track R (veto/half theo regime defensive) 0/6 ứng viên ở EXPLORE; track G (relax/veto gate theo V4/V3) 0 ứng viên ở EXPLORE. Không đề xuất Pha 1 (R-VETO / R-HALF / G-RELAX đều không đủ điều kiện).

Lý do cốt lõi: leg mở trong regime vĩ mô "defensive" vẫn LÃI ròng ở mọi kiểm và mọi kỳ (m2 > 0: EXPLORE +1,3k…+11,8k; CONFIRM +9,2k…+34,7k USD/seed) ⇒ veto/giảm size làm mất tiền — lặp lại đúng bài học IND_COMBO (7a1448ca). Ở CONFIRM chiều còn ĐẢO: leg defensive tốt HƠN (S1 m1 +2,40 [+1,19; +3,74], V4 +2,07 [+0,45; +3,42]) — crash-buy kiếm tiền chính ở regime xấu.

## Dữ liệu + validate
Chi tiết trong MACRO_GATE_SELECTION.md §1–§3. Tóm tắt: 2 nguồn (Yahoo chart v8 + Nasdaq api) cho cả 10 mã, return 20 phiên cùng cơ sở lệch ≤ 0,5 pp ở ≥ 99,67 % ngày mọi mã (không cờ); adjclose chỉ Yahoo (Nasdaq không có cổ tức XLP/UUP/GLD); BTC ngày từ store 1h + Vision 1d cho 2026H1. Causal assert 100 %; kiểm tay 10 ngày 10/10. Bảng leg/cụm khớp IND_COMBO (10 256/117 · 11 298/113 · 2 275/29), trùng legs_x.parquet. Bootstrap khối tháng seed 20261115 chạy 2 lần trùng tuyệt đối (track R và G). Bảng năm cộng đúng tổng (assert mọi bảng). Seed 42 cùng dấu gộp 6/6 kiểm EXPLORE.

## EXPLORE 2022–23 (quyết định) — xem SELECTION §5
| Kiểm | m1 [CI90] | m2 | % leg | ep |
|---|---|---:|---:|---:|
| S1 | +0,94 [−1,60; +3,94] | +8 321 | 36,0 | 9 |
| S2 | −3,42 [−6,55; +2,50] | +1 295 | 28,8 | 7 |
| S3 | −4,42 [−6,92; +0,09] | +2 053 | 41,6 | 12 |
| S4 | −0,54 [−4,55; +5,31] | +11 844 | 41,1 | 14 |
| V4 | −2,66 [−5,73; +2,14] | +3 965 | 36,1 | 11 |
| V3 | −2,75 [−5,74; +2,64] | +3 466 | 32,0 | 9 |
Ứng viên: không (mọi CI90 chứa 0, mọi m2 > 0). Track G EXPLORE: V4 relax 0,85 +2,66 [+0,32; +4,90] nhưng band 0,70 CI dưới −1,11 < −1 pp; V3 trượt cả 2 band; veto Δ dương (+3,1/+3,2) ⇒ không ứng viên.

## CONFIRM 2024–25 — CHỈ MÔ TẢ (không ứng viên ⇒ không kiểm; mở sau commit SELECTION)
| Kiểm (defensive) | m1 [CI90] | m2 (2024 / 2025) | % leg | ep (24/25) | seed42 m1 |
|---|---|---|---:|---|---:|
| S1 | +2,40 [+1,19; +3,74] | +24 193 (+9 489 / +14 704) | 28,1 | 16 (7/9) | +1,65 |
| S2 | +1,92 [−0,92; +4,15] | +9 236 (+3 072 / +6 163) | 8,8 | 3 (1/2) | +1,56 |
| S3 | −0,18 [−2,88; +3,09] | +10 018 (+5 142 / +4 876) | 15,8 | 7 (5/2) | −0,36 |
| S4 | +0,29 [−1,30; +2,56] | +34 701 (+10 505 / +24 196) | 59,2 | 15 (7/8) | +0,32 |
| V4 | +2,07 [+0,45; +3,42] | +18 741 (+7 319 / +11 422) | 19,5 | 9 (3/6) | +1,15 |
| V3 | +0,93 [−1,69; +3,44] | +12 781 (+5 142 / +7 639) | 14,7 | 7 (5/2) | +0,82 |
- Track G CONFIRM (mô tả): V4 relax 0,85 +0,59 [−5,51; +5,20], 0,70 −0,92; V3 −0,40 / −2,25; veto V4 +2,80, V3 +1,74 (CI chứa 0). Không có tín hiệu.

## Chiều bullish (mô tả; owner không muốn tăng size)
- EXPLORE: leg bullish tốt hơn (S2 +4,25 [+1,20; +6,86], S1 +2,64, V3 +2,81, V4 +2,60 [−0,00; +4,84]).
- CONFIRM: ĐẢO dấu — bullish kém hơn (S2 −1,86 [−3,40; −0,33], V4 −1,72 [−3,91; +0,17], V3 −1,54). ⇒ không ổn định giữa kỳ; không có gì để Pha 1.

## E — dòng ETF BTC (mô tả, chỉ 2024+)
- CONFIRM: outflow m1 +0,96 [−1,04; +2,43], m2 +17 052, 24,3 % leg, 14 ep; inflow m1 +0,70 [−1,12; +2,31], m2 +17 969, 25,3 % leg. Không phân biệt được.
- HO 2026H1: outflow 76 % leg, m1 +2,62 [−0,41; +6,44], m2 +17 111; inflow 0,1 % leg.

## HO 2026-01..06 (mô tả; 2 275 leg / 29 cụm / 6 khối tháng — CI không đáng tin)
- Defensive: S1 88,7 % leg (m1 −0,75, m2 +16 367); V4 40,8 % leg (m1 −0,38 [−1,48; +8,23], m2 +6 806, 4 ep); V3 30,8 % (m1 −0,16, m2 +5 380, 2 ep); S2 4,4 %, S3 39,4 %, S4 39,6 % — mọi m2 > 0. Bullish V4 0 % leg. ⇒ Cùng kết luận: nhóm defensive vẫn lãi, veto không cứu HO.

## Tài nguyên
- Oracle CPU ≈ 0,003 h (data 2×1,3 s, explore 2,5 s, confirm 2,9 s, tải dữ liệu ~3 phút wall chủ yếu chờ mạng). RSS đỉnh 0,47 GB (systemd-run --user --scope MemoryMax=2500M MemorySwapMax=0, cgroup memory controller có delegate). flock oracle_heavy, nice 19/ionice c3, mem_avail ≥ 20 GB, không tiến trình deploy.
- Kaggle: 0. Dữ liệu mới ~2 MB (raw ETF JSON + BTC 1d CSV) trong ~/claude_master/macro1114/raw (giữ để tái lập); đã xoá trung gian parquet + script tạm. Đĩa Oracle 17 GB trống trước và sau.

## Sai lệch so với prereg (khai đủ)
1. Nguồn 2: stooq bị chặn (JS challenge trên Oracle, proxy 403 trên cloud) ⇒ dùng Nasdaq api. Nasdaq không có cổ tức cho XLP/UUP/GLD ⇒ đối chiếu 2 nguồn trên close CHƯA điều chỉnh (cùng cơ sở); adjclose dùng cho tín hiệu chỉ có 1 nguồn (Yahoo). Độ nhạy: tín hiệu từ Nasdaq chưa điều chỉnh trùng trạng thái 97–99,9 % số ngày.
2. Close Yahoo và Nasdaq trùng gần tuyệt đối (cùng consolidated tape) ⇒ "độc lập" ở mức nhà cung cấp, không ở mức dữ liệu gốc.
3. BTC 2026H1 tải từ data.binance.vision 1d (store 1h hết 2025-12; nến 2026 của IND_COMBO không còn). Store thiếu 1 ngày ⇒ S1/V4 NaN 8 ngày quyết định, xếp vào N.
4. Khối tháng = tháng (+07) có leg: EXPLORE 21, CONFIRM 22, HO 6.
5. Track G bootstrap khối tháng (theo §3 prereg này) thay cho cụm của IND_COMBO; Holm G cố định m = 4. Không có ứng viên nên không ảnh hưởng.
6. Bảng leg/cụm/G tái dùng: load_legs của IND_COMBO chạy lại (rẻ) + g2_S*.npz còn trên đĩa (không phải dựng lại); khớp tuyệt đối.
7. Năm/kỳ theo mốc +07 như IND_COMBO; trạng thái theo ngày UTC của phút đầu cụm.
8. Mô tả CONFIRM gồm cả 6 kiểm defensive (không chỉ ứng viên) — chạy SAU khi khoá SELECTION, chỉ để tham khảo, không đổi verdict.
