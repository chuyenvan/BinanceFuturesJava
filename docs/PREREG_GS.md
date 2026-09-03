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

## 9. SUA DOI 1 — 2026-09-03, TRUOC khi co ket qua

**Trang thai luc sua (kiem chung duoc):** 5/5 kernel `gs-w1-*` con RUNNING, `/home/ubuntu/gs/out/`
con rong. Chua doc mot so ket qua nao. Doc goc yeu cau ghi ro delta + ly do — day la delta.

### 9.1 DEV-B khong con la holdout theo DU LIEU

Phat hien khi cai `analyze_wave1.py`: ha tang `gs-w1-*/run.py` tinh CA devA VA devB trong CUNG
mot pass JVM cho MOI 256 diem (cat lat tu cung mot chuoi equity 2022-01-01 -> 2024-06-29). Vi vay
§2 ("DEV-B chi chay cho <=5 finalist") KHONG thuc hien duoc: so devB cua ca 256 diem da ton tai
san trong file ket qua. Bang chung: `/home/ubuntu/gs/smoke/out_gs_smoke.jsonl` — moi diem deu co
san khoi `devB`.

**Sua:** DEV-B chuyen tu holdout-theo-du-lieu thanh **holdout theo THU TUC**, niem phong bang
THU TU COMMIT:

1. `analyze_wave1.py` chi doc truong `devA`. CAM doc `devB` (tru buoc 8, chi in goi y lenh).
   Script phai duoc commit TRUOC khi co ket qua — dieu kien nay da thoa.
2. Khi ket qua ve: chay `analyze_wave1.py` -> xuat `finalists.json` (id + tham so + NS + CAGR devA)
   -> **COMMIT file do NGAY**, truoc khi bat ky ai (nguoi hay agent) doc bat ky so devB nao.
3. Chi SAU khi `finalists.json` da commit moi duoc doc devB, va chi doc devB cua dung cac finalist
   trong file do. Doc devB cua diem khong phai finalist = VI PHAM, phai bao cao.
4. Bang chung kiem tra duoc: timestamp commit `finalists.json` phai TRUOC moi log/analysis chua
   so devB.

**Ghi thang mat mat:** thu tuc nay YEU HON holdout that. Neu wave 1 ra ket qua (a) thi muc tin cay
la "da tien-cam-ket luat chon", KHONG phai "da xac nhan tren du lieu chua tung chay". Bat buoc ghi
gioi han nay khi bao cao ket qua. Nguong 0.6 va -20% o §4 buoc 6 giu nguyen.

### 9.2 Chot cach doc §4 buoc 5 (finalist)

"Top 5 theo NS, loc trung >= 0.15" cai theo **greedy**: di tu tren xuong theo NS giam dan, bo qua
diem cach mot finalist da chon < 0.15, dung khi du 5. Script phai in ca `raw top-5` de doi chieu.

### 9.3 Hai cho ghi mot 60390 loi thoi (khong anh huong ket qua)

- Kernel dang chay co hang `ANCHOR_EQUITY = 60390`, chi dung cho dong log `ANCHOR_CHECK`
  => log Kaggle se in MISMATCH cho diem neo DU KET QUA DUNG. Khong anh huong `equity_final`.
- Docstring dau `gen_params.py` cung ghi 60390.

Moc dung van la **60395** (§5 + `BASELINE_NOTE.md`). Kiem neo phai lam bang `analyze_wave1.py`,
KHONG tin dong log ANCHOR_CHECK cua kernel.

## 10. SUA DOI 2 — 2026-09-03, TRUOC khi co ket qua

**Trang thai luc sua:** `/home/ubuntu/gs/out/` con rong, 5/5 kernel con RUNNING.

### 10.1 Phat hien: moi so sanh truoc gio dung do chinh xac GIA

Nguon: `/home/ubuntu/leakprobe/LEAK_L1_REPORT.md` (do ngay 2026-09-03).

Mau lay theo grid 15 phut nhung horizon nhan la 4h, va nhan `g1lite` co tam 72h => cac mau chia
nhau cung tuong lai. **n hieu dung = 302 khoi 72h, KHONG phai 15,442,092 dong.**

| dai luong | CI naive | CI that (block-bootstrap 400 rep, khoi 72h) |
|---|---|---|
| spearman G015 vs outcome | 0.1675 +/- 0.00050 | 0.1675, CI [0.1260, 0.2005] |

=> CI that **rong hon 74 lan**. Diem uoc luong khong doi (do lai tren mau khong chong lan: 4h ->
0.1676, 24h -> 0.1676, 72h -> 0.1718 — khop trong nhieu). Cai sai la **thanh do tin cay**, khong
phai con so.

Hau qua truc tiep: phep so "H3 rho 0.1667 vs G015 0.1675" tung duoc dung de dong nhanh H3 chi
chenh **0.04 sd** => khong co suc phan biet. Nhieu verdict cu co the dang nam trong nhieu.

### 10.2 Sua: THEM chan doan bat buoc, KHONG doi luat quyet dinh

- Truoc khi bao cao ket qua chon, phai tinh **CI block-bootstrap cho CAGR cua diem neo tren
  DEV-A**, block >= 3 ngay (72h), tren chuoi loi nhuan ngay lay tu `sim.out` mark-to-market.
- Bao cao (a)/(b)/(c) o §4 buoc 7 **phai in CI nay canh khoang cach 3pp**.
- Neu 3pp nam TRONG CI cua neo: ket qua (a) van duoc tuyen bo **dung theo luat** (cam doi luat sau
  khi thay so), NHUNG bat buoc ghi kem cau: "khoang cach nay khong phan biet duoc voi nhieu o muc
  CI da do", va buoc tiep theo KHONG duoc re-baseline ngay — phai xac nhan them.
- **Nguong 0.6 / -20% / 3pp / k=10 / N=256 GIU NGUYEN.** Sua doi nay chi them thong tin cho nguoi
  doc, khong doi dieu kien chon hay dieu kien CONFIRMED.

### 10.3 Ghi no: phai do lai CI cho cac verdict cu

Ngoai pham vi wave nay, nhung phai lam truoc khi freeze bat cu thu gi: do lai CI block-72h cho
S1 rank-IC (+0.150) vs G015 (+0.055), va soat lai cac verdict THUA (H1, K, BR, RG, RND, N1-N4,
regime, H3) xem cai nao thuc su thua va cai nao chi nam trong nhieu.

## 11. SUA DOI 3 — 2026-09-03, TRUOC khi co ket qua: nguong 3pp VO HIEU

**Trang thai luc sua:** `/home/ubuntu/gs/out/` con rong, kernel con RUNNING.
Nguon: `docs/CI_REAUDIT.md` (commit `a396797`), phuong phap chot truoc o `docs/PREREG_CI.md`
(commit `2493eca`).

### 11.1 Do duoc: nhieu lon hon nguong

sd cua HIEU CAGR tren DEV (911 ngay, block-bootstrap 21 ngay, 2000 rep):

| loai thay doi | sd(hieu CAGR) | can bao nhieu nam de thay 3pp o 80% power |
|---|---|---|
| chi doi tham so exit | 2.57pp | 14.3 nam |
| doi selector | 4.45pp | 43.1 nam |
| noi gate | 6.34pp | 87.4 nam |

Voi N phep thu thuan nhieu, ky vong cua GIA TRI LON NHAT la `sd * sqrt(2 ln N)`.
N=256 => `sqrt(2 ln 256) = 2.35` => **E[max] = +6.0pp (sd 2.57) den +14.9pp (sd 6.34)**,
diem giua **+10.5pp** cho thay doi kieu selector.

=> Nguong "neo + 3pp" o §4 buoc 7 **nho hon muc nhieu ky vong**. Neu giu nguyen, ket qua (a) gan
nhu CHAC CHAN se duoc tuyen bo NGAY CA KHI toan bo 256 diem chi la nhieu. Nguong do vo hieu.

### 11.2 Sua

- **§4 buoc 1-6 GIU NGUYEN HOAN TOAN.** Khong doi k=10, khong doi N=256, khong doi bo loc,
  khong doi luat argmax NS, khong doi luat finalist.
- **§4 buoc 7, dieu kien cua (a) doi:** thay `> neo + 3pp` bang
  `> neo + 2.35 * sd_boot`, voi `sd_boot` = do lech chuan block-bootstrap cua HIEU CAGR giua diem
  do va neo tren DEV-A, tinh theo `PREREG_CI.md` (block 21 ngay, 2000 rep, seed 20260903).
  He so 2.35 = `sqrt(2 ln 256)` = hieu chinh so sanh boi. Nguong moi CAO HON 3pp trong moi
  truong hop da do => day la SIET LAI, khong phai noi ra.
- **Them dieu kien BAT BUOC moi cho (a):** finalist phai thang neo o **tang TUNG LENH / TUNG TICK
  theo thong ke ghep cap (paired)**, CI cua hieu khong chua 0. Ly do: do la tang duy nhat co n
  hieu dung dung duoc — chinh o do da phat hien duoc rank-IC S1-G015 (+0.0973, CI
  [+0.0711,+0.1152], n_eff 39 khoi) va gate edge (+0.0182, CI [+0.0085,+0.0227], n_eff 52 khoi),
  trong khi tang equity DEV can 14-43 nam moi phan biet duoc 3pp.
- **(b) va (c) giu nguyen cach doc.** Neu khong finalist nao qua nguong moi thi ket luan chinh la
  **"khong the phan biet bang du lieu DEV hien co"**, KHONG phai "C2b la tot nhat".

### 11.3 Ghi thang

Sua doi nay lam **KHO HON** de tuyen bo thanh cong. No khong the duoc dung de bien ket qua xau
thanh tot. Do la ly do no duoc phep ghi vao luc nay.

Hau qua ke hoach: **du wave 1 ra gi, KHONG re-baseline dua tren hieu CAGR DEV.** Gia tri chinh cua
wave 1 tu gio la §6 (chieu nao that su lam doi ket qua) va viec tim vung phang — khong phai tim
diem tot nhat. Cung ly do do, moi de xuat chon N4_a8s175 (61148) hay H1a_mom006 (60953) vi "equity
cao hon 60390" deu la chon tren nhieu: hieu lan luot -0.62pp CI [-5.55,+4.32] va -0.46pp CI
[-12.98,+11.96].
