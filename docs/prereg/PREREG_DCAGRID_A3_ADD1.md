# PREREG_DCAGRID_A3 - ADDENDUM 1 (CHOT 2026-11-20 02:00 +07, MASTER)

Khai ro thoi diem: viet SAU khi Pha 0 da co ket qua (P0-PASS: leg KHONG khop o 10-13/10/2025 = 13,41 % < 30 %; PnL_alt/seed +6 037 > 0)
va SAU khi cong G-ZERO cua Pha 1 FAIL o seed S7 (3 dong DCA_LEVEL1 leg>0: LUNA 2022-05-12, vi LUNA giam > 99,9 % nen muc -0.999 van
kich). Tai thoi diem viet, MASTER CHUA xem bat ky chenh lech A3 - N nao (chi biet: S7 arm N co 3 472 lenh, equity 129 814; G-ZERO FAIL).

1. Theo prereg goc: Pha 1 voi DCA_GRID_LEVELS=-0.999 la VOID. Cac output do chi duoc dung MO TA, KHONG duoc dung cho nhan ket luan.
2. Chay lai Pha 1 (8 seed) voi DCA_GRID_LEVELS=-1.0,-1.0,-1.0 (gia <= firstEntry x 0 khong the xay ra voi gia duong). Truoc khi push:
   xac nhan tu code sim (DcaUtils.shouldDcaGrid / noi parse DCA_GRID_LEVELS) rang -1.0 duoc parse va dieu kien khong bao gio dung;
   neu code tu choi -1.0 hoac co nhanh khac => dung, bao MASTER (khong tu chon gia tri khac).
3. Moi cong va luat cua prereg goc giu nguyen (G-SIZE, G-ZERO, chi so chinh dCAGRID22, CI95 paired, nhan ket luan muc 5). May cham
   dg_score.py da chot luc 00:55 (truoc khi thay so N) giu nguyen.
4. Pha 0 da xong va giu nguyen ket qua (P0-PASS) - khong chay lai.
