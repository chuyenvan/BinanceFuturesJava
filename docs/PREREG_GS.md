# PRE-REG GS — tim kiem toan cuc Sobol, wave 1

**Thoi diem chot:** 2026-09-03 10:35 UTC.
**Trang thai luc chot (kiem chung duoc):** 5/5 kernel `chuyendinh/gs-w1-0..4` = RUNNING,
`/home/ubuntu/gs/out/` RONG, chua doc mot dong ket qua nao. Log: `gs_status.sh` 10:34 UTC.
Doc nay duoc viet TRUOC khi thay bat ky ket qua nao. Neu no bi sua sau khi ket qua ve, ban sua
phai ghi ro delta va ly do — sua am tham = huy wave.

## 0. Ly do ton tai cua wave nay

Bo gia tri mac dinh cua C2b di ra tu HPO nhieu vong truoc. HPO cuc bo co the da xoay manh vao
mot chieu va lam mo cac chieu khac: moi thu nghiem sau do (H1 gate, K, BR, RND) deu la **nhieu
loan cuc bo quanh chinh diem do**, nen ve nguyen tac khong the phat hien mot chieu bi che.
Sobol 15 chieu voi range rong la co che pha vong lap do. Day la muc dich duy nhat cua wave 1.

## 1. Khong gian thiet ke

Dinh nghia chinh thuc = `research/kaggle/gsearch/gen_params.py`, bien `SPEC` (da commit,
`f51fd17`). 15 chieu, THU TU CO DINH. N=256, `qmc.Sobol(d=15, scramble=True, seed=42)`,
`random_base2(m=8)`, cong 1 diem neo `id=-1` = C2b.

Doi range / N / seed / thu tu chieu / thang do => day la wave KHAC, phai co doc PRE-REG khac.
Khong duoc sua `SPEC` roi dung lai doc nay.

## 2. Chia du lieu — VALIDATION KHONG bi cham

| tap | khoang | vai tro trong wave 1 |
|---|---|---|
| DEV-A | 2022-01-01 -> 2023-12-31 | tap CHON. Ca 257 diem chay o day. |
| DEV-B | 2024-01-01 -> 2024-06-30 | tap XAC NHAN. Chi <=5 diem finalist o §4 duoc chay. |
| VALIDATION | 2024-07-15 -> 2025-12-31 | KHONG dung trong wave 1. So lan cham giu nguyen = 5. |
| HOLDOUT | 2026 | da xoa + niem phong code (`HoldoutSeal`). |

Moi de xuat cham VALIDATION phai qua GUARDRAIL L3: canh bao nguoi dung 3 lan rieng biet.
Wave 1 khong duoc tu dong buoc sang VALIDATION du ket qua dep den dau.

## 3. Chi so — nguon va dinh nghia

Tat ca chi so lay tu `qret.py` doc `sim.out` (dong `Update <date> HH:MM => b:<bal> ... unP:<unreal>`),
tuc **mark-to-market**, lay gia tri cuoi ngay. PnL realized-only cho maxDD nong hon => khong dung.

`equity_end`, `CAGR`, `maxDD` (mark-to-market), `Sharpe_q` (theo quy), `n_trades`,
`n_quarter_positive`, `underwater_max_days`.

- Chi so CHINH cho xep hang: **CAGR tren DEV-A**.
- Rang buoc rui ro: **maxDD**, xu ly o buoc loc (§4 buoc 1), KHONG tron vao ham muc tieu.

## 4. LUAT CHON — CHOT CUNG

**Buoc 1 — loc tinh hop le.** Giu diem thoa DONG THOI: run hoan tat (co dong ket qua, khong
timeout giua diem), `n_trades >= 300` tren DEV-A, `maxDD >= -25%`, khong NaN. Diem bi loai phai
duoc DEM va bao cao (so luong + ly do), khong im lang bo di.

**Buoc 2 — chuan hoa.** Moi chieu -> `u in [0,1]` bang dung `lo/hi` va dung THANG cua chieu do
trong `SPEC` (chieu `log`/`logint` chuan hoa trong khong gian log). Ket qua: `u in [0,1]^15`.

**Buoc 3 — diem lan can.** Voi moi diem hop le `i`: lay k=10 diem hop le gan nhat theo khoang
cach Euclid trong khong gian `u`, roi
`NS(i) = mean(CAGR cua i va 10 lang can)`.
Khong co he so phat, khong co lambda de tinh chinh (lambda=0 o wave 1 — chot cung).

**Buoc 4 — chon.** Xep hang giam theo `NS`. **Diem duoc chon la argmax cua `NS`, KHONG phai
argmax cua CAGR.** Day la co y: lay TAM cua vung tot rong nhat thay vi lay dinh nhon. Neu dinh
CAGR cao nhat khong nam trong top-5 `NS` thi dieu do la KET QUA, khong phai loi.

**Buoc 5 — finalist.** Top 5 theo `NS`, loc trung: hai finalist phai cach nhau `>= 0.15` trong
khong gian `u` (giu diem co `NS` cao hon). Toi da 5.

**Buoc 6 — xac nhan tren DEV-B.** Chay <=5 finalist tren DEV-B DUNG MOT LAN. Finalist duoc
coi la CONFIRMED khi: `CAGR(DEV-B) >= 0.6 * CAGR(DEV-A)` VA `maxDD(DEV-B) >= -20%`.

**Buoc 7 — cach doc ket qua, chot truoc:**

- **(a)** Co >=1 finalist CONFIRMED va `CAGR(DEV-A) > CAGR(neo) + 3pp`
  => luan diem "HPO xoay vao 1 chieu, che cac chieu khac" DUOC CHUNG MINH. Diem do thanh ung
  vien **C3**. Buoc tiep theo la de nghi cham VALIDATION theo L3 — khong tu dong chay.
- **(b)** Co finalist CONFIRMED nhung khong diem nao vuot `neo + 3pp`
  => C2b DANG NAM TRONG vung tot nhat. Vong HPO cu co the that nhung khong gay hai.
  KET LUAN: dung lai, KHONG re-baseline, khong lam wave 2 tren cung khong gian.
- **(c)** Khong finalist nao CONFIRMED
  => xep hang tren DEV-A la nhieu. Wave 1 THAT BAI. Khong re-baseline. Leo len wave 2 (N=512
  hoac thu hep range) HOAC ket luan bottleneck khong nam o tham so ma o feature/label.

Khong duoc doc theo cach khac. Khong them bo loc hau kiem, khong doi chi so chinh, khong doi k,
khong doi nguong 0.6 / -20% / 3pp sau khi thay so.

## 5. Diem neo — dieu kien VOID

`id=-1` phai tai lap **equity 60395** (KHONG phai 60390 — xem `/home/ubuntu/gs/BASELINE_NOTE.md`:
duong doc ticker `aerospike` vs `file` lech 1 lenh / 970, +5 USDT = 0.008%).

Neu `id=-1` khong ra 60395 (sai so cho phep: 0 — phai dung so): **toan bo wave VOID**, ket qua
bi loai, khong chon gi. Khong duoc "dieu chinh" neo cho khop.

Moi so sanh so hoc giua run Oracle va run Kaggle chi dang tin toi ~0.01%. Chenh lech nho hon
nguong nay KHONG duoc coi la tin hieu. Trong noi bo 256 diem thi khong bi anh huong (cung moi
truong, cung `TICKER_SOURCE=file`).

## 6. Phan ra phuong sai — CHAN DOAN, khong dung de chon

Canh bao ky thuat, ghi ro de khong tu lua: 256 diem tu **mot** day Sobol KHONG cho phep uoc
luong chi so Sobol bac 1 / tong. Muon chi so Sobol dung phai co thiet ke Saltelli (ma tran
A, B, AB_i) — wave 1 KHONG co. Vi vay:

- Cai duoc phep lam: fit mot surrogate (gradient boosting) tren 256 diem, roi bao cao
  permutation importance + partial dependence theo tung chieu; hoac main-effect binning tho.
- Dieu kien bao cao: phai in **CV R^2 cua surrogate TRUOC** moi con so importance. Neu
  `CV R^2 < 0.3` thi KHONG bao cao phan ra — surrogate khong du tot de noi chieu nao quan trong.
- Ket qua phan ra la CHAN DOAN de thiet ke wave sau. Tuyet doi khong duoc dung de chon diem,
  khong duoc dung de bo chieu ra khoi wave 2 ma khong co doc PRE-REG moi.

## 7. Wave 1 KHONG tra loi dieu gi

Wave 1 chi quet 15 tham so cua may giao dich hien co. No khong noi gi ve: feature moi (H4 spike
15m), label lien tuc (H5), exit theo vol (H6), sleeve short thuc su (H7). Neu ket qua la (b) hoac
(c) thi ket luan hop ly nhat la **bottleneck o feature/du lieu, khong o tham so** — dung lan
feature, khong quet tiep tham so.
