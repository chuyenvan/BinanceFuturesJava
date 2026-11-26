# PREREG_LEVZ_S2_ERRATA1 - lam ro cach cham khi co nam KHONG cham duoc (chot truoc khi chay that; chua co loi suat nao cua S2)
Chot boi MASTER 2026-11-26. Prereg goc 74ec941e. Tai thoi diem nay S2 moi co tap ung vien, bang thoat, code + test tren du lieu gia.
E1. Mot nam kiem Y "cham duoc" khi tap co it nhat mot cau hinh hop le tren cac fold < Y (theo ham hop le cua select_b1). Nam khong cham
    duoc KHONG duoc tinh la 0. Bao ro so nam cham duoc cua tung tap.
E2. S-a: neu ca 3 nam cham duoc: > 0 o >= 2 / 3 nam VA tong 3 nam > 0 (nhu goc). Neu chi 2 nam cham duoc: CA 2 nam > 0. Neu < 2 nam: truot.
E3. S-d, S-e tinh tren cac nam cham duoc; < 2 nam cham duoc thi truot. S-c: tap that khong cham duoc nam nao => truot; luot ngau nhien
    khong cham duoc nam nao tinh la KHONG >= that.
E4. "Gop nam train" trong luat chon = min qua cac fold train (dung cach B1 gop F1 + F2). P6b dung z kieu D1 nhu P6a. Dieu kien "< 40 coin
    xep hang duoc" tinh tren tap coin co z hop le (thuc te khong doi so ung vien: 131 gio do deu co 0 coin).
E5. So ung vien / dot (ep72) theo nam sau khi dung lai (2022 / 2023 / 2024 / 2025): REF 5 / 86 / 207 / 87 dot; P5 101 / 124 / 265 / 199;
    P5b 118 / 129 / 243 / 202; P6a 147 / 247 / 268 / 210; P6b 237 / 378 / 422 / 345.
