# OWNER_DECISION_PILOT_1121 - ADD5: owner chon phuong an B sau khi ADD24 R-SIM = FAIL (ghi de he qua cua prereg)

Thoi diem: 2026-11-22 ~21:20 +07. Kenh: owner tra loi truc tiep MASTER trong phien dieu phoi. Nguyen van: "p/a B di".

## 1. Boi canh da trinh owner (21:15)
ADD24 R-SIM chinh thuc quy 3/2026 = FAIL (docs/result/add24_rsim_ow1, commit 15522b6a; A1 xac nhan): phan VAO lenh cua jar trung backtest
(gate 67/67, size 79 lenh, ly do thoat 79/79); phan THOAT khac backtest o 14/79 cum (17,7 % > tran 10 %): jar doi stop theo nhip trong nen
nen thoat som hon 1 phut, chu yeu ngay sap 22/8; gia thoat TB lech +0,53 % (bien +-0,2 %). Day la khac biet THAT giua jar va backtest
(khong phai loi bo kiem, khong phai loi jar); dau cua tac dong tuy thu tu gia trong nen (quy 3: +0,53 % / ~+0,23 %; quy 2: +0,07 % / ~-0,84 %).
Theo prereg ADD24 s10: FAIL => khong pilot. MASTER trinh hai phuong an:
- A (dung luat da ghi): khong tang von; lam bai kiem moi (dua nhip doi stop trong nen vao backtest bang du lieu 1 giay, sua tier luoi, chay lai).
- B (owner ghi de luat bang van ban): pilot o 5 000 thay vi 10 000, chap nhan khac biet o phan thoat; chi len 10 000 sau khi backtest mo phong
  duoc phan thoat. MASTER noi ro: B hop ly NEU bai so voi lenh that (R-LIVE, chay 24/11) dat; neu R-LIVE truot thi chi con A.

## 2. Quyet dinh cua owner: PHUONG AN B
- Owner GHI DE he qua "FAIL => khong pilot" cua ADD24 cho thanh phan R-SIM (khac biet thoat lenh K8 + co S-G2), va chap nhan khac biet nay.
- **Von pilot = 5 000 USDT** (THAY cho 10 000 o OWNER_DECISION_PILOT_1121_ADD1 Q1). Khong len 10 000 cho toi khi backtest mo phong duoc phan
  thoat (nhip trong nen) va sua tier luoi, chay lai theo prereg rieng, va owner quyet lai.
- Cac quyet dinh khac GIU NGUYEN: jar hotfix 01cfbb43...; Q4_OWNER cho g_exec / g_exit; boot guard (da cai 22/11); mien X14 / B2 / C1 (ADD2);
  co SIM_TIER_STALE (ADD3); P1 (ADD4).

## 3. Cach MASTER ap dung (gia dinh neu ro; owner phan doi thi bao)
- Dieu kien "R-LIVE dat" DI KEM phuong an B nhu da trinh: R-LIVE chinh thuc (sang 24/11, ket qua 25/11) = FAIL => KHONG pilot (khong nam
  trong pham vi ghi de nay); R-LIVE = INSUFFICIENT khong phu => MASTER trinh owner truoc khi tao gate.
- Som nhat: 2026-11-26 09:31 +07 (du 7 ngay micro) va sau khi co ket qua R-LIVE.
- Ngay pilot: owner chay LEV_CAP=5000 golive_check_lev.sh; MASTER tao gate PILOT_SIZE=5000 (ref quyet dinh nay); owner chay pilot_on.
- No sau pilot (MASTER): prereg moi cho backtest co nhip trong nen (du lieu 1 giay ngay bien dong manh) + sua tier luoi + chay lai HO5;
  kiem hang ngay lenh that trong pilot (ADD24-M); co BD_ORDER da bao owner 19:40, owner khong phan doi.
