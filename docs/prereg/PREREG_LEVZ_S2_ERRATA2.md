# PREREG_LEVZ_S2_ERRATA2 - sau A1 audit code (PASS-WITH-MINOR, A1_S2_CODE.md); chot TRUOC khi chay that, chua co loi suat nao cua S2
Chot boi MASTER 2026-11-26. Prereg goc 74ec941e + ERRATA1 5f917679.
F1 (NHO-1 cua A1). p_wfo: mot luot ngau nhien chi duoc cong tong WFO tren DUNG cac nam ma tap THAT cham duoc. Luot nao khong cham duoc mot
   trong cac nam do thi tinh la KHONG >= that. (Truoc khi sua, luot ngau nhien cong tren cac nam cua rieng no => co the so tong 1 nam voi
   tong 3 nam.) DEV sua rand_s2 / select_s2 + test; A1 kiem lai phan sua truoc khi chay.
F2 (NHO-2 cua A1 - he qua cau truc, KHONG sua luat). Vi "gop nam train = min qua cac fold train", mot cau hinh phai hop le o Y22 moi duoc chon
   cho bat ky nam kiem nao. Tap REF (D0 z 3,0) nam 2022 chi co 25 ung vien / 5 dot => nhieu kha nang KHONG cham duoc nam nao qua quy trinh S2.
   Khi do so doi chieu cua REF lay tu B1 da audit (WFO top-20: 2024 -23,0 %, 2025 +6,1 %; khong co 2023) va ghi ro hai quy trinh khac nhau.
F3. Test bo sung truoc khi chay: dem so luong rand doc lap voi ham bi kiem; kiem dinh nghia top-20; kiem S-a (>= 2 / 3 nam).
