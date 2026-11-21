# HOLDOUT_UNSEAL_2026_1121 - owner duyet TRUC TIEP mo niem phong holdout 2026 (AGENT_RUNBOOK muc 1, dong 10-12)
Thoi diem: 2026-11-21 ~07:20 +07, trong phien chat voi MASTER (Claude-Session https://claude.ai/code/session_01KcMsGUgBnZquZL84M8evnp).
Boi canh: owner nhan "ok. sang retrain cho pilot di". MASTER hoi lai bang cau hoi lua chon (nguyen van, bo dau):
  "Retrain cho pilot bat buoc phai dung du lieu 2026 (model moi train toi 30/6/2026 de kiem tren quy 3, ban production train toi
   30/9/2026). Theo AGENT_RUNBOOK, mo niem phong holdout 2026 can anh duyet truc tiep va khong hoan tac duoc. Anh duyet mo o muc nao?"
Owner chon: "Mo toan bo 2026 (Recommended)" = "Chay HO5 truoc (kiem cau hinh + model dang live tren 2026), roi retrain: train toi 30/6,
  kiem tren Q3; ban production train toi 30/9, kiem them tren 1/10 -> nay (7 tuan chua ai nhin). Sau do khong con du lieu qua khu sach;
  kiem chung tiep chi con du lieu tuong lai va micro/pilot live."
Cau hoi 2: thoi gian shadow song song truoc khi doi model tren 242 -> owner chon "7 ngay (Recommended)".

## Pham vi duoc mo (CHI cac muc dich sau; moi muc dich khac van phai hoi owner)
U1. HO5: chay PREREG_HO5_A3_2026.md (bf3f90a1) + ADD1 (5803ca82) + ADD2 (2725f216) + ADD3 (499700bd) tren cua so 2026 - dung luat da ghi,
    khong doi gi. Buoc "DUNG truoc moi buoc 2026 cho owner mo niem phong" cua ADD2 / ADD3 nay duoc go.
U2. RETRAIN truoc PILOT: train p15 / S1 / net015 voi du lieu 2026 theo prereg rieng (PREREG_RETRAIN_PILOT - MASTER commit TRUOC khi chay):
    tang kiem chung cut 2026-07-01 (OOS = 2026Q3), tang san xuat cut 2026-10-01, kiem mo ta tren 2026-10-01 -> ngay cuoi du lieu.
U3. Du lieu 2026-10-01 -> nay: duoc dung cho kiem mo ta cua U2 (va cho HO5 neu prereg HO5 cho phep cua so toi ngay cuoi du lieu).
KHONG nam trong pham vi: bat ky nghien cuu moi nao khac (grid, alpha moi, tinh chinh tham so chien luoc) tren du lieu 2026.

## He qua da noi ro voi owner
Sau U1-U3, 2026 khong con la holdout sach. Kiem chung ve sau = forward (du lieu sau ngay chay) + micro / pilot live.
