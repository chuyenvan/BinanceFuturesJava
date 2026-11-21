# HO5 luot 5 - dinh nghia cham Lane L (CHOT 2026-11-21 ~08:10 +07, TRUOC khi tai bat ky output sim 2026 nao)
Tham chieu: PREREG_HO5_A3_2026.md (bf3f90a1) muc 2-3 + ADD1 A3 (E0b) ; HOLDOUT_UNSEAL_2026_1121.md (e9095a02, U1).
Prereg KHONG dinh nghia cach tinh equity/maxDD; ADD1 chi noi E0 "nhu HO4". Chon duoi day TRUOC khi thay so, khong doi sau.

## Nguon
- printDone.csv cua kernel ho5-a3-l26-<seed> (start/end = 'YYYYmmdd HH:MM' gio +07; pnl = PnL da tru phi/funding, ghi tai end).
- Equity ngay: dong log sim "BudgetManagerSimple: Update YYYYmmdd 07:00 => b:<b> ... unP:<u>" -> E_d = b + u (MTM 07:00 +07 cua chinh sim).
  (KHAC DEV/HO4: DEV dd_mtm22 = MTM PHUT tu kline Vision; o day MTM NGAY 07:00 -> maxDD NONG hon MTM phut. Ghi ro khi so DEV / R3.)

## Cua so (+07)
W = 2026-01-01 00:00 -> 2026-09-30 23:59 ; Q1 01-01..03-31 ; Q2 04-01..06-30 ; Q3 07-01..09-30 ; OOS = 04-01..09-30 (dung cho luat).
## Chi so (moi seed, moi cua so)
- n = so dong co start trong cua so. SigmaPnL = tong pnl dong co end trong cua so (nhu HO4 score_B).
- E_start = E cua dong Update ngay dau cua so; E_end = E cua dong Update ngay ke sau ngay cuoi cua so (neu khong co: dong Update cuoi cung <= ngay cuoi).
- ROI = E_end/E_start - 1. maxDD = min E/peak - 1 tren chuoi [E_start .. E_end] (peak dat lai dau moi cua so).
- Sharpe = mean(r)/std(r, ddof=1)*sqrt(365), r = E_d/E_{d-1}-1 tren chuoi do. % ngay co lenh = so ngay (+07) co >=1 start / so ngay cua so.
- Trung binh 8 seed = trung binh cong tung chi so.
## Luat (nguyen van prereg + ADD1)
- E0 (OOS): mean_seed SigmaPnL_OOS > 0 VA #seed SigmaPnL_OOS > 0 >= 6/8 => PASS, nguoc lai FAIL.
- E0b: tuan = khoi 7 ngay lien tiep tinh tu 2026-04-01 00:00 +07 (khoi cuoi co the thieu ngay, van tinh); PnL tuan = tong pnl end trong tuan,
  trung binh 8 seed -> vecto w (k tuan). Bootstrap 10 000 lan: rut k tuan co hoan lai, thong ke = tong; numpy default_rng(20261121).
  CI80 = phan vi 10 / 90. Can duoi > 0 => "duong co y nghia"; <= 0 => "chua phan biet duoc voi 0".
- R1-R5 theo prereg (R1 sua boi ADD1 A3). R3: mean maxDD(W) < -22,72 % => canh bao (so MTM ngay; neu mean maxDD(W) trong (-22,72 ; -14,0] ghi
  "gan nguong, MTM phut co the sau hon ~8,7 pp" - CHI ghi chu, khong doi luat).
- Lane W: KHONG CO (ADD1 A3).
## Kiem chung truoc khi doc so 2026 (fail => khong bao cao so seed do)
result.json ok + java_rc nhu r1-a3, date_last >= 20260929, n_trades > 0; md5/sha dau vao trong result.ho5 (pred26, bins26, market, funding DEV prefix,
snapshot funding v3 fb024c40/overlay 207e7c60, mapper); khong NaN trong pnl/start/end; printDone: moi dong end <= max(end) cua r1-a3-<seed> phai TRUNG
nguyen dong (sym,side,entry,start,end,status,pnl...) voi printDone r1-a3-<seed>, cung so dong; dong Update ngay <= 20251230 TRUNG log r1-a3.
## So DEV (mo ta)
DEV r1-a3 8 seed: CAGR22 37,72 % / maxDD MTM phut -22,72 % (R1_SEC4). Them: Sharpe/CAGR/maxDD 2022-01-01..2025-12-30 tinh bang CUNG thuoc MTM ngay
o tren tu log r1-a3-<seed> (de so cung thuoc). Ti le: Sharpe_W/Sharpe_DEV, CAGR quy nam W / CAGR DEV, maxDD_W / maxDD_DEV.
