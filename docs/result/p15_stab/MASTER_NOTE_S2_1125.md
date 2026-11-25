# MASTER_NOTE_S2_1125 - P15_STAB Tang S2 (prereg dea45002 muc 4) - sau audit A1 (PASS-WITH-MINOR)
MASTER, 2026-11-25 10:10 (+07). 8 lane sim DEV (C0-PROD x4: c0s42/c0s7/c0s123/c0s13 ; E8 x4: e8g1..e8g4), kiem khong-PnL PASS truoc khi cham.
## Ap luat ghi truoc: E8 KHONG DAT S2
- (e) DISP (trung vi theo quy cua sd ROI quy giua 4 lan lap): C0 0,981 pp ; E8 0,712 pp ; ti so 0,726 > 0,6 => KHONG DAT. (E8 nho hon o 13/16 quy.)
- (f) CAGR22 trung binh: C0 37,51 [35,05 ; 39,84] ; E8 35,48 [33,82 ; 36,30] ; hieu -2,03 pp < -1,5 => KHONG DAT. maxDD22: C0 -22,52 ; E8 -23,51 (hieu -0,99, dat).
=> Ung vien E8 KHONG duoc chon. Khong ung vien nao cua prereg nay qua S2. KHONG sua nguong / khong chay lai de doi ket luan.
## Dung muc bang chung (audit)
- DUOC noi: E8 giam ~27 % dao dong ROI quy theo chi so ghi truoc (chua toi 40 %) ; so lenh vao KHAC NHAU giua hai lan train giam ~40 % (126 -> 77 / quy tren ~170) ;
  chi phi CAGR -2 pp CHUA phan biet duoc voi nhieu (SE hieu 1,23 pp ; CI95 tho [-5,3 ; +1,2] ; 4 lan lap).
- KHONG duoc noi: "E8 kem 2 pp" ; "ensemble khong giup on dinh".
- Ti so (e) rat nhay theo cach tong hop (0,52 RMS-sd .. 0,73 trung vi sd ; bootstrap CI95 [0,41 ; 1,08]) => phep do voi 4 lan lap KHONG du luc ca hai chieu. Loi thiet ke cua MASTER:
  dat nguong 0,6 / -1,5 pp voi 4 lan lap la qua it lan lap de phan biet.
- Phat hien phu: ngay trong sim day du, hai lan train C0 khac seed lech nhau ~126 / 170 lenh vao moi quy (74 %) va CAGR22 trai 35,1 .. 39,8 - xac nhan do bat on cua quy trinh hien tai.
- 91-106 leg dong 00:00 UTC / lane la do lop X14 trong template (baseline r1-a3 cung co) ; anh huong DD22 = 0. Moc so sanh dung ho: r1-a3 8 seed cu CAGR22 TB 37,7 [34,9 ; 40,5].
## Tiep (moi huong prereg rieng ; chua bat dau)
H1 tang so lan lap (8-16 / ho) cho C0 vs E8 de SE hieu <= 0,7 pp - tra loi dut khoat E8 co mat hieu nang khong. H2 on dinh o tang quyet dinh (gate theo trung vi K model / theo rank).
H3 do Jaccard theo nhieu muc quantile gate (phu thuoc duoi cuc tri). H4 tach dao dong do pool / S1 rebuild khoi phan do p15. Khong dung DD22 de chon (chi 1 su kien LUNA).
Bai hoc van hanh: quota dataset private Kaggle (xoa s2-* bang s2/code/s2_dsdel.py) ; template sim r1-a3 cu can Aerospike cong 3222 (da dong) => dung template ho5 snapshot.
