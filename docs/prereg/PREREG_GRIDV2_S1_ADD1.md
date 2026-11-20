# PREREG_GRIDV2_S1_ADD1 - Addendum 1: sua LOGIC KIEM V0 / V4 / V5 cua runner sau khi lan chay 1 bi dung (2026-11-20)
Bo sung docs/prereg/PREREG_GRIDV2_S1.md (commit 4ecc655d, sha256 52aaeab7...). Viet va commit TRUOC khi bat ky so M / PnL nao cua
du lieu that duoc doc. Tac gia: MASTER.

## 1. Vi sao
Lan chay 1 (5 kernel Kaggle chuyendinh/gridv2-s1-shard0..4 v1, code ghim runner 9ddb3cef) DUNG truoc merge theo dung quy tac prereg:
- V0 "so dong doc = metadata" FAIL nam 2021 o ca 5 shard: pass1 khong mo kline1m-2021-01..03 (chi can warm-up tu 2021-04) nhung phep
  kiem so voi metadata CA NAM (doc 48 408 602 vs 60 001 411, thieu 11 592 809). Loi cua phep kiem, khong phai cua du lieu.
- V4 FAIL o 4 shard: phep kiem lay 2 symbol dau theo ten voi moc tc toan cuc; symbol niem yet sau tc -> n_checked = 0 -> FAIL
  (0GUSDT, 1000PEPEUSDT, 1000000MOGUSDT, 1000RATSUSDT, 1000000BOBUSDT, 1000BONKUSDT). Moi phep kiem co don vi deu n_diff = 0.
- V1, V2, V3, V5 (8/8), V6 PASS ca 5 shard. Allowlist PASS. Khong co so M / PnL nao duoc doc: thu muc run1/d*/reduced/ da tai ve nhung
  CHUA TUNG MO (agent chay, dev, 2 agent audit va MASTER deu chi doc validate.json / manifest.json / dong V0-V6).
Bao cao: v12/RESULT_GRIDV2_S1.md (ban dung, sha256 9397d963...), v12/GRIDV2_S1_RUN.progress.

## 2. Thay doi (CHI logic kiem trong runner_kaggle.py; mo phong, feature, mat na, thong ke, merge KHONG doi)
- V0 = V0a + V0b. V0a (nhu cu): tong dong metadata cua MOI file cua nam == registry. V0b: so dong pass1 doc cua nam == tong dong
  metadata cua cac file DA MO; tap file bo qua == tap suy tu quy tac "thang BAT DAU truoc DATA_START - 31 ngay" va (registry that)
  == {kline1m-2021-01, -02, -03}; registry - dong doc == tong dong metadata cac file bo qua (chinh xac); ten + so dong tung file bo qua
  ghi vao validate.json. Ngu nghia: thieu file / thieu dong so voi registry do V0a bat; V0b bat pass1 doc thieu so voi metadata
  (vd symbol co > 1 row group trong 1 file).
- V4: symbol hop le = (ts hop le cuoi - ts hop le dau) >= 90 ngay; lay 2 symbol hop le DAU TIEN theo ten trong shard; tc ngau nhien
  deu (seed co dinh) trong [max(ts dau + 45 ngay, STUDY_START + 45 ngay), ts cuoi - 15 ngay]; khoang rong -> bo qua; symbol bo qua ghi
  v4_skipped kem ly do. Symbol da chon: n_checked == 0 -> FAIL; n_diff != 0 -> FAIL. Shard khong du 2 symbol hop le -> FAIL.
- V5: 8-12 don vi / shard, phu du 6 cap (c,k), co ca BUY va SELL, ca K_OPT va K_PESS, chon tat dinh (khong theo PnL); thieu -> FAIL;
  ghi danh sach (sym, t0, c, k, side, model) da kiem. (Lan chay 1: V5 chi roi vao c0,1.)
  Gioi han da biet (A1 vong 4, J1): cach can bang chon theo cap (K_OPT, BUY) / (K_PESS, SELL); to hop cheo (K_OPT, SELL), (K_PESS, BUY)
  khong duoc V5 kiem tren du lieu that (da duoc phu tren du lieu tong hop: klite vs kref 9 240 don vi, bo mo phong rieng A1 8 024).
  MASTER chap nhan, khong sua.
- Gioi han da biet (J4): V4 van co the FAIL n_checked = 0 voi symbol that co lo du lieu dai -> lan chay lai se DUNG (huong an toan).

## 3. Code ghim moi (thay muc 15 cua prereg cho 2 file + EXPECTED_SHA; klite / kref / stats KHONG doi byte)
  196f458489c5a808754d4afc39c2ad03f9149d57936de7f84c810074b8652680  klite.py          (khong doi)
  6de0e412633658f1d548d28c7a650ff9b0e43b1a5f6cc3e64dbe93c51c928ff2  kref.py           (khong doi)
  975f3a427cd52750018d615b664ab13f899ee216764e5f80fca82192976df3e4  stats.py          (khong doi)
  23a788cf97f69c73aec663572d0f133136e6e872eb64c8251b9641ba0dd14ccf  runner_kaggle.py  (truoc: 9ddb3cef...)
  6f864aaf739fa46bcfd9cafce6dac065bb1bfd2c1cf5dda6134eabb83c7d0521  test_klite.py     (104/104 PASS)
  d933009e0b3adb0dad120c6c41e9d4a7d482157aae0cf4cf17315a9997e39042  EXPECTED_SHA.txt  (truoc: 4f764be8...)
Diff runner R4 -> R5: 280 dong (163 dong +/-), 7 hunk, tat ca thuoc V0 / V4 / V5 + ghi validate / checkpoint lien quan
(w3/gridv2/R5_runner.diff sha256 1c0a2397...).
"Truoc merge BAT BUOC (H1)" cua prereg muc 13 nay la: sha256sum EXPECTED_SHA.txt = d933009e0b3adb0dad120c6c41e9d4a7d482157aae0cf4cf17315a9997e39042.

## 4. Audit doc lap vong 4 (v12/A1_GRIDV2_S1_R4.md): PASS-WITH-MINOR
- 104/104 test PASS (chay lai doc lap). Runner R4 va R5 tren CUNG lake tong hop: 78/78 file agg + reduced GIONG TUNG BYTE
  (549 733 dong) => mo phong khong doi. Thu pha: xoa file thang / bot dong -> V0 FAIL; tach row group -> V0b FAIL; nhin tuong lai
  (sigma dung close ngay D) -> V4 FAIL va V5 FAIL; lech kref 1e-8 -> V5 FAIL. Rao chan cu (allowlist, chan 2026, cam env, assert hang
  so, merge guards) con nguyen. Hook chi-test junk_lead_min khong co duong vao tu CLI / env / run().

## 5. Lan chay 2
- Chay lai CA 5 shard voi code moi (kernel version moi), dung cac quy tac cua prereg (7 dataset allowlist, V0-V6 ALL PASS truoc khi doc M,
  H1 voi sha moi, H2, merge --expected-sha). Lan chay 1 bi HUY (khong dung output cua no cho ket qua).
- Kiem bo sung V7 (chi bao cao, lam TRUOC khi doc M, bang script chi in so dem / True-False): noi dung reduced/ cua lan chay 2 so voi
  reduced/ cua lan chay 1 theo tung shard (bang du lieu bang nhau). Ky vong GIONG HET vi mo phong khong doi. Neu KHAC: DUNG, bao MASTER
  (khong doc M) - dau hieu mo phong khong tat dinh.
- So trial ho grid GIU 72 (chua co outcome nao duoc doc; lan chay 2 khong phai trial moi). Moi dieu khac cua prereg giu nguyen.
