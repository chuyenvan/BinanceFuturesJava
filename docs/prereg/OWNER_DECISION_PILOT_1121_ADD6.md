# OWNER_DECISION_PILOT_1121_ADD6 - owner GHI DE ket qua R-LIVE FAIL, uu tien pilot 5.000
Ghi boi MASTER, 2026-11-25 08:20 (+07). Bo sung cho OWNER_DECISION_PILOT_1121 (c3a9f01b) + ADD1..ADD5 (ADD5 = 7b80604e).

## 1. Quyet dinh cua owner (nguyen van, 2026-11-25 ~08:15 +07, trong phien lam viec voi MASTER)
"ghi de va uu tien pilot 5k vua lay them duoc du lieu verify/audit voi backtest cung nhu kiem cac khau va lam min dan"
Boi canh da trinh owner truoc khi quyet (24/11 21:15 va 25/11 sang): R-LIVE luot #3 = FAIL (cc4a4339, MASTER_CONCLUSION_RLIVE_1124.md) ; ba lua chon (hoan de kiem
bang log live ; ghi de va pilot ; cho jar moi) ; rui ro cua lua chon ghi de (7 bat bien la phan tich SAU ket qua ; time-stop va DCA chua tung chay that).

## 2. Pham vi ghi de
- GHI DE: he qua "R-LIVE FAIL => khong pilot" (dieu kien MASTER neu o ADD5) cho ket qua ADD24 R-LIVE luot #3.
- Owner CHAP NHAN de pilot voi cac khac biet da biet giua jar live va backtest / rig o khau THOAT LENH va size min:
  D1 stop kich theo MARK_PRICE + khop MARKET (backtest: LOW gia last, khop dung SL) ; D2 dinh / arm lay mau 10 s (backtest: HIGH nen 1 phut) ; D8 gia vao = gia khop that ;
  L-S2 lech size < 1e-3 do day chuyen gia khop. Bang chung hien co: vao lenh tai lap 24/24 ; khong co bang chung loi logic jar (nhom E = 0 ; 7 bat bien tren log live 100 % -
  phan tich sau ket qua, CHUA phai bang chung dang ky truoc).
- KHONG doi: von pilot 5.000 USDT (ADD5) ; jar hotfix 01cfbb43 va 3 model live giu nguyen ; cac mien X14 / B2 / C1 (ADD2), SIM_TIER_STALE (ADD3), g_exec / g_exit Q4_OWNER (ADD1) ;
  lop chan sau reboot bat buoc (ADD1) ; len 10.000 CHI sau khi backtest mo phong duoc co che thoat (nhip trong nen + MARK vs LAST + truot + lay mau dinh) va owner quyet lai.
- CHUA co bang chung tren lenh that (owner da duoc bao): DCA ; time-stop 168 h (lan dau du kien 28/11 10:39-11:08) ; X14 ; hanh vi sau restart ; muc stop duoi 1 phut.

## 3. Muc dich pilot theo owner
Vua chay 5.000, vua lay them du lieu de verify / audit voi backtest, kiem tung khau, lam min dan.

## 4. Viec MASTER cam ket thuc hien (KHONG phai dieu kien owner dat ; khong lam cham ngay pilot)
- PILOT-M: prereg kiem lenh that hang ngay trong pilot (bat bien thoat lenh dang ky TRUOC, cham tren du lieu MOI tu 2026-11-24 07:00 ; tai lap tap lenh vao bang rig ; time-stop ;
  DCA khi co ; truot gia vao / thoat) - bao owner moi ngay ; mot bat bien vi pham => bao ngay + de nghi dung mua moi.
- Giam sat nhom A truoc khi bat pilot (canh nguoc Oracle tren 242, tin "con song", canh bao ingestor chet / gia cu) - script da audit, owner chay.
- Nhanh lam min: backtest "kich stop theo last vs mark" ; dua "dinh theo nen 1 phut" + log gia 10 s vao jar W3B (doi jar => audit + parity) ; P15_STAB (on dinh model) ; retrain.
- Ngay pilot som nhat: 2026-11-26 tu 09:31 +07 (du 7 ngay micro) ; trinh tu theo OPS6 (cong pilot + kiem don bay cung ngay).
