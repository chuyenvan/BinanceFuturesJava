# DIAG_MASTER_DECISIONS_1121 - quyet dinh MASTER tai STOP-D2 (PREREG_RETRAIN_DIAG 436977c1)
Thoi diem: 2026-11-21 20:45 +07 (ban tam, sha256 dau 0f9467853dd11eda) -> 22:00 +07 (ban CHOT sau audit A1).
Dau vao: RESULT_RETRAIN_DIAG.md sha256 71f167790637ccb1087bf5be577c067464b6b285066b0ccd416e2766f8a83a3a (KHONG sua sau audit);
audit doc lap A1_RETRAIN_DIAG.md: PASS-WITH-MINOR (1 MAJOR ve DIEN GIAI - M1, da sua cau chu o D-D2 duoi day; khong doi quyet dinh).

## D-D1. Cach doc cay: (A) = B5 - GIU CA 3 MODEL LIVE, KHONG U4b
- Khong nhanh B1 / B2 / B3 nao kich hoat theo dieu kien da ghi truoc (B1 dk1 = 0,979 [dung cua so: 0,980] nam trong [0,83; 1,2];
  B2 S1 T1 khong kem; B3 net015 T1 khong kem).
- Van ban B5 + muc 8 P7 ("B5 -> khong U4b") la mac dinh da ghi truoc. Khi van ban cay co hai cach doc, MASTER chon cach BAO THU;
  khong chon cach doc theo so da thay. Audit: doc theo tung model thi ca p15, net015 (B4) va S1 (Delta_S -0,49 cung dau Delta_tot,
  ruler khong co y nghia thong ke -> "khong ket luan") deu ve "giu live" -> hai cach doc cho CUNG ket qua.
- Cach doc (B) (ung vien S1-only) bi BAC: bang chung S1 T1 tot hon live = 0.
- He qua: KHONG doi model nao tren live. Quyen U4b (owner 21/11) CHUA dung; du lieu >= 2026-10-01 van CHUA ai doc, van niem phong.

## D-D2. Phat hien ghi nhan (CHAN DOAN tren 1 duong di; KHONG phai xac nhan) - da sua theo audit M1
- Tren thuoc xep hang Tang A, ca 3 model T1 KHONG KEM model live (p15 IC +0,015; net015 AUC +0,002; S1 khong co y nghia thong ke).
- Lane N co nhieu lenh qua gate hon (Q3: 94 -> 142) va thua lo nam o cac lenh chi-co-o-lane-moi. Dieu nay PHU HOP gia thuyet "lech thang
  diem p15 / net015 so voi nguong gate", NHUNG CHUA KIEM va dua tren RAT IT su kien:
  * tuong tac cap PM (-6,74 pp) gan nhu toan bo den tu 2 lan vao lenh: BANK 07-27..08-03 (1 PREDICT + 3 DCA_LEVEL1, ~ -7,4k ~ -4,6 pp)
    va LAB 07-08 (~ -2,9k ~ -1,8 pp); o Lane N 3 lenh te nhat = 71 % phan lo cua lenh chi-o-lane;
  * lenh DCA_LEVEL1 (nhanh nguong p15 TUYET DOI) lo ~ -4,8k o PM / NNN so voi -0,65k o L -> mot phan lo KHONG di qua gate rolling;
  * tuong tac bac 3 = +3,13 pp; Shapley S (+0,76) nguoc dau Delta_S (-0,49) -> quy ket rat nhay voi vai lenh;
  * Q3 = 1 duong di (2 seed cho tap lenh 2026 trung 100 %); Q3 da bi nhin 3 lan.
- "Pass M tang" la co hoc qua sp: P(win) trung binh net015 T1 0,4075 vs 0,4027 (lech hieu chuan TUYET DOI, khong phai xep hang).
- Lech thang p15 T1 thay doi theo thang (median +3,3 % / +3,8 % / +0,6 % thang 7 / 8 / 9); lenh them van nhieu o thang 9 -> khong chi la
  hieu ung chuyen tiep bo dem 90 ngay; mot quantile-map CO DINH co the khong du.
- LOI THIET KE cua MASTER (ghi nhan, KHONG sua sau khi thay so): dk 1 cua B1 do duoi p15 tren DEV Q2 - la IN-SAMPLE cua T1 - nen khong the
  thay dich chuyen duoi ngoai mau (Q3: 1,19 o q99,99; 1,51 o q99,995).

## D-D3. Viec tiep theo cua nhanh retrain (CHUA bat dau; can prereg MOI; uu tien SAU pilot)
- Chi dung DEV 2022-2025 (khong 2026). Hai gia thuyet CANH TRANH phai tach: (H-gate) lech thang diem model moi so voi nguong gate rolling;
  (H-abs) nhanh DCA / nguong p15 tuyet doi + hieu chuan tuyet doi net015 (sp). Do tai NHIEU ranh gioi fold WFO lich su (nhieu duong di,
  khong phai 1 quy): dich thang OOS model moi / model cu co du doan buoc nhay pass gate, so lenh DCA_LEVEL1 va PnL quy sau khong.
- Thanh phan ung vien (chi sau khi do): gieo bo dem gate bang r OOS cua model bong cat som 90 ngay; hieu chuan lai nguong tuyet doi theo
  cong thuc co dinh; kiem gia thuyet nguon feature tron (DEV toi 2025 + Vision 2026H1) bang train mot nguon.
- Chi khi thanh phan qua kiem tren nhieu quy qua khu moi viet prereg U4b (mot lan thu tren 2026-10-01 -> moi nhat).

## D-D4. Don dep
- CHUA xoa out/lane/*/ds (ban local duy nhat cua bins S / M 0701): giu toi khi co manifest sha + xac nhan ban tren Kaggle. Dia hien 16,1 GB.

## D-D5. Loi nho audit ghi nhan (khong doi ket luan)
- m1: rt_dcal.py hang Q2 lech 16 gio (04-01 16:00 +07) -> ti so Q2 0,9793 thay vi 0,9803. B1 khong doi.
- m2: rt_lchk khong so md5 pred 2026 voi gia tri mong doi, kiem bins theo JSON do rt_lane tu sinh (tu tham chieu) -> lan sau phai co gia tri
  mong doi doc lap. Lan nay audit kiem doc lap bang inode + sha: dung.
- m3: log kernel sim-rt-*.log co equity_final nam tren dia truoc CO CHE-2 (CO CHE-2 chi dem gate; B1 da sai tu dk 1) - khong anh huong.
- m4: rt_score_lane.py sua 18:18:57 sau lan cham dau de them Shapley (mo ta); phan luat 2.4 tinh lai khop.
- Lane P push 16:53:59 truoc khi D-cal xong (chi push, chua tai).
- Khong kiem lai duoc doc lap: AUC / lift@8 / IC cua ruler (nhan Q3 chi co trong kernel Kaggle).
