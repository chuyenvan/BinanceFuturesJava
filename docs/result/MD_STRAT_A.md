# MD_STRAT tầng A — kết quả (2026-10-20): ĐÓNG (1 ô đạt D, trượt C)

Prereg `docs/prereg/PREREG_MD_STRAT.md` (142c87fb). Raw Oracle `~/claude_master/md_strat/{ms_a.py, ms_a.json, ms_a_clusters.parquet}` (agent Opus, MASTER duyệt).

## Validate
V1: printDone ghi `order.marketData.rateDownAvg/rateUpAvg/rateDown15MAvg` của tick vào lệnh; đối chiếu market.bin 5 438/5 438 đợt khớp đúng phút vào. symbolPred = pNoPump S1, sim xếp TĂNG dần (nhỏ = tốt) — prereg ghi "giảm dần" là sai chiều, đã dùng thứ tự sim thật như prereg cho phép. V2 cụm khớp ENTRY_CONFIRM 27 962/27 962, ΣPnL lệch 0. V3 r ≤ 24, khớp selRank 100 %. V4 cutoff/ô chọn chỉ từ D.
Mẫu: 5 438 đợt / 25 978 cụm selector (1 984 cụm BIG_DOWN không có hạng bị loại). D = 2021-07..2023-12, C = 2024–2025 (năm theo +07).

## ΣPnL/seed nhóm hạng 6–24 theo tercile (D | C; số seed âm)
| Biến | T1 (sâu nhất) | T2 | T3 |
|---|---|---|---|
| dow (rateDownAvg) | +10,2k \| +17,0k | +0,7k (4/8) \| +3,3k | +4,7k \| +2,9k |
| up (rateUpAvg) | +10,7k \| +16,0k | **−1,9k (6/8) \| +2,1k (0/8)** | +6,8k \| +5,1k |
| dow15m (rateDown15MAvg) | +12,1k \| +14,5k | +2,8k \| +7,7k | +0,7k \| +1,0k |
Nền (không cắt): PnL/cụm R1/R2/R3 = D +22,5/+19,0/+15,7, C +51,0/+40,8/+26,6 — mọi nhóm hạng đều lãi.

## Luật
Ứng viên D duy nhất: up T2 (−1,9k, 6/8). Xác nhận C: +2,1k, 0/8 seed âm, ΔPnL −2,1k ⇒ TRƯỢT ⇒ ĐÓNG (biến trạng thái MarketDataObject không giúp chọn K).

## Mô tả
Spearman theo đợt (biến vs PnL/cụm): dow −0,08/−0,06, up −0,05/−0,07, dow15m −0,22/−0,10 (D/C) ⇒ đợt sập sâu hơn lãi/cụm cao hơn, nhưng đều cho mọi nhóm hạng (không phải tín hiệu chọn K). Hướng "nới K khi sập sâu" đã có bằng chứng ngược: K32_CONFIRM NO-GO, ISO_RISK V1K32 Calmar 1,05.
Phân bố đợt theo cutoff D lệch mạnh trên C (dow T3 17,5 %, up T3 56 %) ⇒ regime đổi.
Mở (không chạy, cần prereg mới nếu muốn): hạng theo selRank trong pool top-24 (≈ SELECTOR_RANK_TOPK) khác hạng trong cụm thực vào ở 45,8 % cụm; với mọi nhóm hạng đều lãi ở cả D và C, kỳ vọng không đổi kết luận.
