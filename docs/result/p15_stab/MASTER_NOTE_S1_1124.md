# MASTER_NOTE_S1_1124 - P15_STAB Tang S1 (prereg dea45002) - sau audit A1 (PASS-WITH-MINOR)
MASTER, 2026-11-24 18:50 (+07). Ap luat ghi truoc: E4 KHONG DAT (CVN x0,662 > 0,6) ; E8 DAT (a)(b)(c)(d) ; DET KHONG DAT (c').
- E8 so voi C0 (trung vi 16 quy, ho SEED): sd log q99,995 0,0109 vs 0,0408 (x0,27 ; trung vi ti so theo quy 0,37 ~ 1/sqrt(8)) ; Jaccard tap pass 0,893 vs 0,711 ;
  CV so pass 0,055 vs 0,115 ; so su kien pass KHAC NHAU giua hai lan train: trung vi 21 / quy (E8) vs 61 / quy (C0), tren ~160 su kien / quy. dIC +0,0009 (khong kem).
  E8 hon C0 o TAIL 16/16 quy, J 16/16, CVN 14/16.
- GIOI HAN (audit MAJOR ve dien giai): dieu kien (c) ve mep cut chi dat theo chu luat (E8_EDGE 2 lan lap vs C0_EDGE 4) ; so khop cung cap e0/e2 thi ti so 0,763 (se truot).
  => DUOC noi: "E8 giam manh nhieu SEED". KHONG duoc noi: "E8 on dinh voi mep cut / du lieu" ; "89 % lenh live giong nhau" (J la so lac quan, replay khong phan hoi duong di).
- DET (bo sampling) KEM hon C0 duoi EDGE (x1,28) => bo ngau nhien khong lam model on dinh ; do nhay nam o du lieu, khong chi o seed.
- Tiep: Tang S2 CHI cho E8 (prereg muc 4): C0-PROD 4 seed dau (42, 7, 123, 13) vs E8 4 nhom roi theo SEED_PLAN.json ; pool / ledger S1 DUNG LAI (rebuild) theo p15 cua tung lan lap
  (lam ro chu "dung lai" trong prereg = DUNG LAI nhu rt_lane, khong phai dung chung) ; bao them so lenh khac nhau tuyet doi giua cac lan lap tu sim.
