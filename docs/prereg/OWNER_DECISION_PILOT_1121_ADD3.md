# OWNER_DECISION_PILOT_1121 - ADD3: owner chap nhan co SIM_TIER_STALE cua ADD24 (P5) + ghi nhan tra no sizing_iv

Thoi diem: 2026-11-22 ~18:50 +07. Kenh: owner tra loi truc tiep MASTER trong phien dieu phoi.

## 1. P5 - owner chon "cach 1" (nguyen van tra loi: "cach 1 nhe")
Cau hoi MASTER da trinh (16:50): backtest (sim) cap nhat bang xep hang thanh khoan (TIER) "luoi" nen khong DCA voi coin moi niem yet / chua
co hang, con bot that (jar pilot) cap nhat moi gio va SE DCA. Do lon uoc tinh tren 9 thang 2026: bot that DCA THEM khoang 3 lenh so voi
backtest (quy 1: 1 lenh ~0,7 % von; quy 2: 2 lenh ~3,8 % von; quy 3: 0); chieu nguoc lai khong co; lai lo cua cac lenh them CHUA biet;
con so ky vong ~23 %/nam khong phan anh dung phan DCA cua bot that.
- Cach 1 (owner CHON): owner CHAP NHAN bang van ban rang bot that DCA nhieu hon backtest co 3 lenh / 9 thang; pilot khong bi cham vi viec
  nay; SAU pilot MASTER sua backtest (tier theo gio) va chay lai de co con so ky vong dung (prereg rieng).
- Cach 2 (khong chon): sua backtest va chay lai truoc roi moi kiem tiep.
He qua: dieu kien (ii) cua ERRATA4 muc 1c (PREREG_PARITY_V12_DRY_ADDENDUM24_ERRATA4.md, 03bb65e0) DA THOA cho co SIM_TIER_STALE. Cac dieu
kien khac cua ADD24 GIU NGUYEN (moi chi so bat buoc phai dat; FAIL => khong pilot).
Chua trinh owner (se bao kem ket qua ADD24): co BD_ORDER (ERRATA5: khi >= 2 lenh BIG_DOWN cung phut, bot that chia size tung lenh lech
khoang +-4 % so voi backtest, tong khong doi).

## 2. P1 - CHUA co tra loi
Owner chua tra loi cau hoi P1 (cho R-LIVE dung log van hanh bot + gia coin lien quan 2026-11-18..11-24, khong PnL). R-LIVE chinh thuc van bi chan.

## 3. Tra no sizing_iv (T9; ADD22 s3 (iv)) - owner chay, MASTER ghi nhan
Owner chay tren Oracle luc 2026-11-22 18:50:31 +07 (chi doc log 242, khong goi san, khong ghi):
  DRY=1 FT_DIR=/tmp/ft_backfill_1122 bash ~/claude_master/w3/c3_ops6/ops/c3live/golive_first_trade_check.sh   (c3_ops6 HEAD 082c10f5, da ghim)
Ket qua (output owner dan lai cho MASTER): cua so tu 19/11 09:31:09; jar 01cfbb4324fb4a10b615dc3c976ddc73; C3_CAPITAL=1000; 24 dong SUBMIT
(21/11 10:39:08 -> 11:08:21, deu PREDICT_SYMBOL_TRADE, legIdx 0), REJECT 0; ca 24 dong DAT so voi 0,0225 x C x (1 - U_before / 0,6)
(dung sai cong cu 2 %): lech 0,000 % (1 dong), -0,017 % (7 dong, cap ngam 999,83), -0,162 % (16 dong, cap ngam 998,38);
"sizing_iv: DAT (dong SUBMIT cham: 24, lech: 0, REJECTED: 0)". Phan doi chieu san (b) khong chay trong DRY.
Ghi chu: cron first_trade_check (cai 17:22) chi doc 6 MB log cuoi nen khong thay 24 lenh nay; tu nay lenh moi duoc cham tu dong.
LUU Y KY LUAT: tu thoi diem nay MASTER DA THAY kich thuoc 24 lenh that (budget, U_before). Moi nguong / dung sai cua R-LIVE (L-S, L-S2 ...)
da chot trong prereg 6ee84f17 + ERRATA1-5 (commit truoc thoi diem nay) va KHONG duoc sua nua.
