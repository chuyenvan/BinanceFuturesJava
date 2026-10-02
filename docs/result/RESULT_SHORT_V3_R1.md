# RESULT_SHORT_V3_R1 — INTRADAY FADE "bán đỉnh guồng thanh khoản" (1m first-hit)

Pre-reg: `docs/prereg/PREREG_SHORT_V3_R1.md` (`a58f9929`, chốt TRƯỚC đo) · Program: `PROGRAM_SHORT_V3.md` §R1 (`a8eff3fb`)
Script: `research/analysis/short_v3_r1_fade.py` · Số: `docs/result/RESULT_SHORT_V3_R1.json` · per-trade CSV: `~/claude_master/1002/r1_cache/trades_r1.csv` (ngoài repo)
DEV 2022-01-01..2025-12-31 UTC (trigger cuối 2025-12-30 22:38 UTC, mọi exit ≤ 2025-12-31 23:59 UTC; 2026 không đọc). 0 Java, 0 sửa .java, 0 chạm 242.

## Kết luận: **NO-GO** — không ô nào qua G1 (net > 0 ngoài CI raw & inflate); ô tốt nhất S_B24 net +0,170%/lệnh, CI raw [−0,030%; +0,369%].

| ô | G1 CI raw & infl > 0 | G2 ≥3/4 năm + | G3 n ≥ 1500 | G4 SL ≤ 25% | G5 ≥2 ô + cùng nhánh | G6 long ≤ 0 | GO |
|---|---|---|---|---|---|---|---|
| S_A4 | ✘ | ✔ 3/4 | ✔ | ✘ 27,9% | ✔ | ✔ | ✘ |
| S_A12 | ✘ | ✔ 3/4 | ✔ | ✘ 30,8% | ✔ | ✔ | ✘ |
| S_A24 | ✘ | ✔ 3/4 | ✔ | ✘ 31,6% | ✔ | ✔ | ✘ |
| S_B4 | ✘ | ✔ 3/4 | ✔ | ✔ 19,5% | ✔ | ✔ | ✘ |
| S_B12 | ✘ | ✔ 4/4 | ✔ | ✔ 24,9% | ✔ | ✔ | ✘ |
| S_B24 | ✘ | ✔ 4/4 | ✔ | ✘ 27,6% | ✔ | ✔ | ✘ |

Điều kiện gãy chung: **G1** (cả 6 ô CI raw chứa 0). Nhánh A còn gãy G4 (SL 28–32%).

## 1. Lưới 6 ô SHORT (n = 10 991 lệnh sau cooldown, cùng tập cho mọi ô)
| ô | net mean | median | CI raw | CI inflate (×1,89) | 2022 / 2023 / 2024 / 2025 | SL | TRAIL | TIME | win | gross | funding | held h | min | p1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S_A4 | +0,009% | +1,41% | [−0,130; +0,139] | [−0,253; +0,255] | +0,19 / +0,14 / +0,05 / −0,08 | 27,9% | 57,1% | 15,0% | 64,4% | +0,130% | −0,009% | 1,3 | −8,1% | −6,1% |
| S_A12 | +0,030% | +1,51% | [−0,098; +0,146] | [−0,212; +0,249] | +0,18 / +0,15 / +0,03 / −0,03 | 30,8% | 64,8% | 4,4% | 66,5% | +0,152% | −0,010% | 1,9 | −8,1% | −6,2% |
| S_A24 | +0,040% | +1,55% | [−0,087; +0,155] | [−0,200; +0,258] | +0,17 / +0,13 / +0,03 / −0,01 | 31,6% | 67,2% | 1,2% | 67,2% | +0,162% | −0,010% | 2,2 | −8,3% | −6,2% |
| S_B4 | +0,027% | +2,16% | [−0,183; +0,213] | [−0,371; +0,379] | +0,26 / +0,02 / +0,10 / −0,05 | 19,5% | 34,3% | 46,2% | 61,6% | +0,163% | −0,024% | 2,5 | −12,1% | −10,2% |
| S_B12 | +0,101% | +2,53% | [−0,093; +0,289] | [−0,266; +0,455] | +0,45 / +0,07 / +0,05 / +0,07 | 24,9% | 50,9% | 24,3% | 65,1% | +0,247% | −0,033% | 5,2 | −15,3% | −10,3% |
| S_B24 | +0,170% | +2,75% | [−0,030; +0,369] | [−0,207; +0,545] | +0,54 / +0,04 / +0,04 / +0,19 | 27,6% | 60,2% | 12,2% | 66,9% | +0,318% | −0,036% | 7,3 | −15,8% | −10,4% |

(CI/năm tính bằng %; năm = năm UTC của entry. Tail min < −s vì khớp gap tại open.)

## 2. Theo năm — ô tốt nhất S_B24 (không ô nào GO ⇒ "tốt nhất" = mean short cao nhất, chỉ báo cáo)
| năm | n | S_B24 net mean | L_B24 net mean (đối chứng) |
|---|---|---|---|
| 2022 | 1 135 | +0,54% | −0,76% |
| 2023 | 1 555 | +0,04% | −0,40% |
| 2024 | 2 468 | +0,04% | −0,33% |
| 2025 | 5 833 | +0,19% | −0,45% |
4/4 năm dương nhưng 2023–2024 ≈ +0,04% (≈ 0); 2025 chiếm 53% số lệnh (universe 1m tăng tới 591 sym).

## 3. Đối chứng LONG cùng trigger, exit đối xứng (G6)
| ô | net mean | median | CI raw | CI inflate | năm + | SL | win | gross | funding |
|---|---|---|---|---|---|---|---|---|---|
| L_A4 | −0,210% | +1,11% | [−0,339; −0,064] | [−0,455; +0,066] | 0/4 | 25,1% | 59,3% | −0,107% | +0,009% |
| L_A12 | −0,240% | +1,25% | [−0,371; −0,098] | [−0,487; +0,029] | 0/4 | 31,2% | 61,7% | −0,139% | +0,010% |
| L_A24 | −0,268% | +1,29% | [−0,405; −0,120] | [−0,528; +0,011] | 0/4 | 34,0% | 62,8% | −0,167% | +0,010% |
| L_B4 | −0,267% | +0,35% | [−0,435; −0,083] | [−0,585; +0,081] | 0/4 | 9,8% | 51,3% | −0,178% | +0,023% |
| L_B12 | −0,346% | +1,85% | [−0,521; −0,167] | [−0,677; −0,009] | 0/4 | 18,1% | 55,1% | −0,265% | +0,031% |
| L_B24 | −0,450% | +2,11% | [−0,645; −0,252] | [−0,819; −0,075] | 0/4 | 24,4% | 58,0% | −0,374% | +0,036% |
Long âm 0/4 năm ở cả 6 ô (CI raw < 0 cả 6) ⇒ G6 đạt: hướng sau trigger nghiêng XUỐNG, không chỉ là volatility.
Nhưng biên độ nhỏ: gross short +0,13…+0,32%, gross long −0,11…−0,37%.

## 4. Phân rã vì sao NO-GO (ô S_B24; số trung bình/lệnh)
gross +0,318% − phí 0,112% − funding 0,036% (short TRẢ: funding tại đỉnh pump trung bình ÂM) = net +0,170%.
Phí = 35% gross, funding = 11% gross. Dịch CI net theo phần cố định (+0,148%) ⇒ gross CI raw ≈ [+0,12; +0,52]% (xấp xỉ),
tức trước phí có lệch dương; sau phí + funding thì CI raw chạm 0, và với inflate ×1,89 cách xa (lo −0,21%).
Tiếp diễn (continuation): 20–32% lệnh dính SL cứng (+6% / +10% ngược hướng trong 4–24h), tail min −15,8% (gap); median
dương (+2,75%) nhưng mean nhỏ ⇒ phân phối lệch trái, lãi nhiều lệnh nhỏ bị vài lệnh SL lớn ăn mất.

## 5. Theo tier quoteVol 30d và regime BTC>SMA50 — ô S_B24 (CHỈ BÁO CÁO, không chọn)
| lát | n | short mean | median | CI raw | SL | năm + | long mean |
|---|---|---|---|---|---|---|---|
| tier LỚN | 4 021 | +0,047% | +2,68% | [−0,276; +0,372] | 27,8% | 2/4 | −0,372% |
| tier VỪA | 3 624 | +0,257% | +2,76% | [+0,011; +0,504] | 26,6% | 4/4 | −0,575% |
| tier NHỎ | 2 625 | +0,266% | +2,82% | [−0,020; +0,558] | 28,1% | 3/4 | −0,491% |
| tier NA (<20 ngày lịch sử) | 721 | +0,067% | +2,81% | [−0,436; +0,583] | 30,2% | 2/4 | −0,104% |
| BULL (BTC d−1 > SMA50) | 6 078 | +0,220% | +2,80% | [+0,006; +0,439] | 28,0% | 4/4 | −0,440% |
| BEAR | 4 913 | +0,109% | +2,69% | [−0,246; +0,436] | 27,1% | 2/4 | −0,463% |
Lát là post-hoc (7 lát × 6 ô): CI raw > 0 của VỪA/BULL KHÔNG đủ để kết luận (chưa inflate, SL > 25%).

## 6. Trigger: phân phối và tần suất
- Đếm: r60 ≥ 8% (phút-coin, có entry) 813 724 → ứng viên thô (đủ 3 điều kiện) 85 903 → sau cooldown 24h **10 991**; mất entry t+1: 0.
- r60 tại trigger: p10 8,1% · p25 8,3% · p50 8,8% · p75 10,2% · p90 13,7% · p99 31,4% · max 200,8% ⇒ đa số trigger sát ngưỡng 8%.
- W0/Mnền: p50 7,7× · p90 23,5×.
- Trigger/ngày (1 460 ngày): mean 7,5 · median 4 · p90 19 · max 124 (2025-04-09) · 9,7% ngày không có trigger.
  Theo năm: 2022 1 135 · 2023 1 555 · 2024 2 468 · 2025 5 833.
- Funding: 100% lệnh có coin trong store; cửa sổ exit thiếu > 10% phút: 0,18% lệnh.

## 7. Sanity (PASS cả 3)
- (c) Ngày mẫu 2024-03-05 (nhiều ứng viên thô nhất tháng thử): vectorized 271 = loop thuần 271, tập (sym,t) trùng khít,
  lệch feature tương đối 0; exit 3 252 phép so (271 trigger × 12 cấu hình): lệch pnl 0, lệch phút/lý do exit 0.
- (b) Entry assert chỉ số t+1 (P = close t+1, đường giá từ t+2); hàm loop nhận list CẮT tại t+1; test nhiễu tương lai
  300 ứng viên (dữ liệu > t thay rác): 0 lệch feature/trigger.
- V = field 5 `totalUsdt` = quoteVol (BTCUSDT 1m ≈ 2,4e7 USDT) ⇒ không nhân close.
- Thời gian: tháng thử 2024-03 98s (1 proc); full 48 tháng 3 proc ≈ 27 phút (Σ 4 582s), lock `oracle_heavy.lock` = R1 lúc chạy.
- (a) 10 trigger mẫu (5 đầu 2024-03 + 5 ngẫu nhiên seed 20260905); đọc lại Aerospike độc lập phút t−60/t/t+1: khớp 10/10 cả 3 giá.

| sym | t UTC | close t−60 | close t | r60 | P = close t+1 | max close 24h trước | W0 (USDT) | Mnền | W0/M | S_B24 net | lý do |
|---|---|---|---|---|---|---|---|---|---|---|---|
| YGGUSDT | 2024-03-01 01:07 | 0,6552 | 0,7318 | +11,7% | 0,7273 | 0,7243 | 1,44e7 | 2,75e6 | 5,2 | −10,07% | SL |
| AGIXUSDT | 2024-03-01 04:30 | 0,7714 | 0,8931 | +15,8% | 0,8867 | 0,8904 | 5,13e7 | 8,84e6 | 5,8 | +5,43% | TRAIL |
| OMUSDT | 2024-03-01 04:34 | 0,25364 | 0,2798 | +10,3% | 0,28152 | 0,27863 | 4,31e6 | 8,52e5 | 5,1 | +2,23% | TRAIL |
| CYBERUSDT | 2024-03-01 05:13 | 9,032 | 9,774 | +8,2% | 9,675 | 9,716 | 8,97e6 | 1,30e6 | 6,9 | −10,11% | SL |
| IDUSDT | 2024-03-01 07:06 | 0,5978 | 0,6474 | +8,3% | 0,6583 | 0,6372 | 1,33e7 | 2,26e6 | 5,9 | +6,21% | TRAIL |
| CRVUSDT | 2022-11-26 10:38 | 0,689 | 0,747 | +8,4% | 0,743 | 0,741 | 5,22e7 | 8,22e6 | 6,3 | +4,94% | TIME |
| 1000XUSDT | 2024-12-01 16:05 | 0,20095 | 0,21978 | +9,4% | 0,2168 | 0,21856 | 3,14e6 | 5,53e5 | 5,7 | +3,16% | TRAIL |
| 1000RATSUSDT | 2025-09-15 18:24 | 0,01932 | 0,02096 | +8,5% | 0,02098 | 0,02086 | 1,25e6 | 1,30e5 | 9,6 | −7,29% | TIME |
| ZKUSDT | 2025-11-14 15:36 | 0,04811 | 0,05221 | +8,5% | 0,05258 | 0,05185 | 9,39e6 | 1,87e6 | 5,0 | +2,71% | TRAIL |
| IRYSUSDT | 2025-11-29 20:59 | 0,035577 | 0,03951 | +11,1% | 0,039491 | 0,039314 | 1,43e7 | 2,82e6 | 5,1 | +5,27% | TRAIL |
Kiểm tay: r60 = close t/close t−60 − 1 khớp; close t ≥ max 24h trước khớp cả 10; W0/M ≥ 5 cả 10.

## 8. Giới hạn
- **Slippage tại spike CHƯA mô hình**: khớp ở close t+1 và ở đúng mức stop (hoặc open nếu gap). Spread/impact quanh pump trên
  coin NHỎ/VỪA thực tế có thể lớn hơn nhiều ⇒ net ở đây là CẬN TRÊN. Với gross chỉ +0,13…+0,32%/lệnh, slippage 0,1–0,2%
  mỗi chiều đủ xoá hết.
- Không giới hạn vốn/số lệnh đồng thời (max 124 trigger/ngày); không xét khả năng borrow/OI limit.
- Tick xấu H/L có thể kích SL giả (không lọc, theo pre-reg). Universe = mọi symbol trong `kline_1m_opt` (đã gồm coin delist).
- Inflate dùng hệ số 1,89 nhân nửa-độ-rộng (đã ghi pre-reg); với ZK/1,96 = 0,966 kết luận vẫn NO-GO (G1 gãy ngay ở CI raw).

## 9. Ý tưởng amend (KHÔNG chạy trong vòng này; mỗi ý cần pre-reg mới + holdout)
1. Lệch hướng có thật nhưng nhỏ: short−long gross ≈ 0,34–0,69%/cặp ở nhánh B (0,24–0,33% nhánh A) ⇒ nếu tiếp, cần selector tách continuation
   (OI tăng/taker-buy tại trigger, funding đã âm = short crowded) thay vì nới exit.
2. Funding tại đỉnh trung bình âm (short trả) — có thể dùng như filter loại trigger short-crowded.
3. Mean tăng đơn điệu theo TS ở nhánh B (+0,03 → +0,10 → +0,17%): drift có thể kéo dài > 24h — chỉ là quan sát, chưa kiểm.

## 10. Tái lập
`python3 research/analysis/short_v3_r1_fade.py scan --months 202403 --sanity --procs 1` → `scan --months all --procs 3` → `report`
(cache tháng ở `~/claude_master/1002/r1_cache/cand_YYYYMM.parquet` + `meta_*.json`; funding `/tmp/fund_cache.npz`; tier/regime từ `p0a_cache/qv`).
