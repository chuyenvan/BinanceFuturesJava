# PREREG_X3_1127 - ERRATA1 (27/11/2026 ~13:40 +07)

Viet boi MASTER. Thoi diem viet: grid_b4 CHUA chay tren du lieu that (levz_b4/out rong);
CMB2 va LLV DA co so va da qua A1 (muc E3, E4 la ghi nhan sau khi thay so - noi ro).

## E1 - Phan A (B4), tieu chi V-b khi KHONG DCA khong cham duoc
A1 code (A1_B4_CODE.md, muc 9) bao CHOICES #12 cua DEV ("KHONG DCA khong cham duoc nam Y
=> V-b = False") la SIET luat so voi prereg. Chot TRUOC khi chay that:
- Neu quy trinh WFO cua kieu KHONG DCA khong chon duoc cau hinh hop le cho nam Y (rule tra ve
  rong), thi moc so sanh cua V-b nam Y = 0 (khong giao dich). Tuc V-b(Y) = [trung vi top-20
  cua kieu DCA nam Y > 0].
- Report phai in ro "KHONG DCA khong cham duoc nam Y" va in THEM (mo ta, khong dung trong
  tieu chi) trung vi loi suat nam Y cua toan bo 108 cau hinh KHONG DCA.
- Neu KHONG DCA cham duoc: giu nguyen nhu prereg (so trung vi top-20 voi trung vi top-20).
Ly do: quy trinh khong chon duoc cau hinh = khong giao dich = loi suat 0; day la cach doc
tu nhien cua prereg A6.

## E2 - Phan A, loi nho da biet, KHONG sua truoc khi chay (deu bat loi cho DCA, rat nho)
- Lenh bi dong cuong buc cuoi fold (EOD) bi tru them phi tren phan ngan sach chua khop
  (<= 0,05 % ngan sach mot cho moi lenh; ~70 dong).
- Leg khop dung phut 60h-1 khong duoc tra funding moc do (10 / 3 960 phep so).
- Test h (bao dong gia tren du lieu gia) gan nhu khong do duoc do nhay: KHONG duoc trich
  "bao dong gia 0 / 80" nhu bang chung.

## E3 - Phan B (CMB2), ghi nhan sau audit
Cac so A1 them (Calmar rieng cua so 2024-2025; do tap trung loi nhuan vao 3 lenh; cach ghep
chia 50 / 50 von) la MO TA NGOAI prereg, dan nhan nhu vay khi bao cao. Ket luan theo khuon B4
cua prereg khong doi.

## E4 - Phan C (LLV), phep hoan vi
Prereg C3 ghi "hoan vi nhan nhom giua cac cum trong cung thang" nhung khong noi cach xu ly
cum trung nhau giua 4 seed. Agent phan tich hoan vi doc lap tung seed (p H2 = 0,0008).
A1 chi ra cach do pha cau truc trung lap (91 % cum trung giua seed) va lam p nho gia tao.
Quyet dinh (SAU khi thay ca hai so, chon phia BAO THU): p chinh thuc = hoan vi CHUNG
(cung coin + cung gio quyet dinh thi cung nhan o moi seed): H1 0,26; H2 0,0117; H3 0,0097;
H4 0,14. Khong duoc trich p = 0,0008 / 0,0002. Nguong 0,0125 va tieu chi NHAT QUAN giu nguyen.
