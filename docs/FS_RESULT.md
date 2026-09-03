# FS_RESULT — ket qua tim FEATURE MOI cho selector S1

Tien dang ky: `docs/PREREG_FS.md`, commit **992edd53a2a3cf39d2808a13ddd89564e2e6eb5b**
(2026-09-03 22:39:12 +0700) — **truoc** moi phep do. Ngay do: 2026-09-03/04.
Pham vi: **CHI DEV**. Khong cham VALIDATION, khong cham HOLDOUT 2026, khong chay java,
khong backtest, khong ghi de artifact nao.

Script: `/home/ubuntu/fs/{fs_dl,fs_build2,fs_pack,fs_env,fs_run_cpu,fs_boot2}.py`;
kernel Kaggle `fs-cand-gpu` (GPU, **bi loai** — xem muc 0.2) va `fs-cand-cpu` (CPU, ban sao doc
lap tren moi truong float khac; ket qua o **muc 8**).
So thô: `/home/ubuntu/fs/fs_boot_oracle_cpu.csv`, `fs_verdict_oracle_cpu.csv`,
`out/fs_results_cpu.jsonl`, `out/fs_ticks_cpu.parquet`, log `RUNCPU.out`, `BOOT_ORACLE.out`.

---

## TOM TAT MOT DONG

**KHONG co ung vien nao vuot nguong — truong hop (c) cua pre-reg.** 15 feature that + 1 feature
nhieu, xay tu kline 1h (dollar-volume, microstructure trong nen, taker-flow, VWAP) va funding
(carry), do bang `Delta rankIC` khi **THEM** vao bo 7 feature hien co: **khong mot ung vien nao**
vuot nguong hieu chinh so sanh boi tren `g1_replay`, va **khong mot ung vien nao** vuot tren
`g1lite`. Ba ung vien thi **lam hai do duoc**. Doi chung am va doi chung san-nhieu-seed deu
dung nhu du bao.

> **Khoang trong 80% toi tran oracle KHONG nam o feature suy tu du lieu gia / khoi luong /
> funding o thang gio.** Do la cau tra loi quan trong nhat cua job nay.

---

## 0. HAI CONG DUNG/DUNG DA CHAY TRUOC — theo dung thu tu pre-reg muc 7

### 0.1 Neo nhan qua (do, khong doan)

`CLOSES_1H.bin[t]` **bang** close cua kline co `open_time = t - 1h`:

| doi chieu | n | sai so tuong doi max | trung binh |
|---|---|---|---|
| BTCUSDT 2022-03, `open_time + 1h == t` | 743 | **4.14e-08** | 2.20e-08 |
| ETHUSDT 2023-08, `open_time + 1h == t` | 743 | **3.59e-08** | 1.67e-08 |
| gia thuyet nguoc `open_time == t` | 744 | 4.61e-02 / 5.79e-02 | — |

=> moi ung vien chi dung bar co `open_time <= t - 1h`. **Unit test cat chuoi**: 40 symbol x
5 moc x 6 feature = **1,200 phep so, mismatch = 0** (`BUILD2.out`, `PASS CAUSALITY`).
Kem 5 kiem mien gia tri (`pos_7d in [0,1]`, `taker_buy in [0,1]`, `dd_speed <= 0`,
`dd_term <= 0`, `close_vwap` huu han) — tat ca PASS.

Du lieu: `data.binance.vision monthly/klines/<SYM>/1h/`, **294 symbol** x 42 thang
(2021-01..2024-06), cache 133 MB, giai nen trong bo nho (khong bung CSV ra dia).
Bang feature `/home/ubuntu/fs/feat_fs.parquet`: 4,944,054 dong x 16 ung vien;
do phu tren pool ledger **98.4%–99.8%** (base `vol_7d` la 99.7%).

### 0.2 Tai lap S1 — va mot ket qua PHUONG PHAP quan trong

| moi truong | keep9 vs `ledger/pred_s1a2.parquet` | ket luan |
|---|---|---|
| **Oracle CPU** (`xgboost 3.2.0`, `n_jobs=4`, `tree_method=hist`) | **spearman = 1.000000** tren **774,270** dong; `edge5 g1lite = +6.8044%` (goc +6.80%) | **PASS** — day la moi truong do |
| **Kaggle GPU** (`device="cuda"`, cung tham so) | spearman = **0.985490** | **FAIL** nguong 0.999 |
| GPU vs CPU, cung kernel, per-tick rank-IC | corr = 0.990013, **sai lech tuyet doi trung binh = 0.01843** | GPU **khong dung duoc** |

**Day la mot phat hien can ghi vao runbook:** `device="cuda"` cua XGBRanker **khong** tai lap
duoc model dang chay, va nhieu cua no (**0.018 per-tick rank-IC**) **lon hon** moi hieu ung ma
job nay di tim (0.001–0.008) va lon hon ca hai khoi tin hieu that ma feataudit do duoc
(+0.0122 / +0.0183). Cu the: tren pipeline GPU, **hai** ung vien (`fs_dvol_7d`,
`fs_close_vwap_7d`) **vuot nguong** o SELECT; tren pipeline CPU (tai lap dung production)
**ca hai deu khong vuot**. Tuc GPU **san xuat ra hai ket qua duong gia**. Vi luat
"neu GPU khong khop CPU thi do bang CPU" da duoc chot **truoc** trong pre-reg muc 5,
hai ket qua duong gia do **khong** duoc bao cao la ket qua.

**=> Moi ket qua duoi day la CPU tren Oracle.** So GPU luu o `/home/ubuntu/fs/fs_boot_gpu_disq.csv`
va **chi** dung lam vi du ve nhieu backend.

---

## 1. BO NEN VA DIEM UOC LUONG

`BASE7 = [vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d]`
(= 9 feature `KEEP` tru 2 feature OI = model `no_oi` cua feataudit C.6).

| | rank-IC `g1_replay` SELECT | rank-IC `g1lite` SELECT | edge5 `g1_replay` |
|---|---|---|---|
| BASE7 (seed 42) | **0.04281** | **0.17210** | 1.43% |
| BASE7 seed 1 | 0.04290 | 0.17295 | 1.47% |
| BASE7 seed 7 | 0.04304 | 0.17204 | 1.42% |

Doi chieu feataudit C.6 (`no_oi`, 7 feature): rank-IC `g1lite` 0.1731, `g1_replay` 0.0407,
edge5 `g1_replay` **1.43%** — **khop**. `n_eff` = **194 khoi 72h** (SELECT), **51** (CONFIRM),
**248** (ALL).

---

## 2. DOI CHUNG — cong phai qua truoc khi doc bang ung vien

### 2.1 Doi chung am `fs_noise` (bat buoc)

| cua so | `Delta rankIC g1_replay` | CI95 khoi 72h | nguong `2.3548*sd` | vuot? | loai 0 ca 3 block? |
|---|---|---|---|---|---|
| SELECT | **-0.00071** | [-0.00432, +0.00273] | 0.00430 | **KHONG** | KHONG |
| ALL | -0.00154 | — | 0.00432 | KHONG | KHONG |

`g1lite` SELECT: `-0.00137`, CI [-0.00555, +0.00313], khong vuot.
=> **PIPELINE OK.** Truong hop (e) khong duoc kich hoat.

### 2.2 Doi chung san nhieu huan luyen (train lai BASE7 doi seed, them ZERO thong tin)

| doi chung | `Delta` `g1_replay` SELECT | sd72 | nguong | vuot? |
|---|---|---|---|---|
| `ctrl_seed1` (seed 1) | **+0.00008** | 0.00259 | 0.00610 | KHONG |
| `ctrl_seed7` (seed 7) | **+0.00022** | 0.00176 | 0.00416 | KHONG |

=> O **SELECT**, san nhieu huan luyen la **~0.0002**, thap hon nguong ~25 lan. Truong hop (d)
**khong** duoc kich hoat: **tang SELECT do duoc**.

### 2.3 Nhung cua so CONFIRM thi KHONG do duoc — phai noi thang

O cua so **CONFIRM** (2024H1, chi **51 khoi 72h**), chinh hai doi chung nay lai vuot nguong:

| | `Delta` `g1_replay` CONFIRM | CI95 72h | nguong | vuot? | loai 0 ca 3 block? |
|---|---|---|---|---|---|
| `ctrl_seed7` (ZERO thong tin) | **-0.00280** | [-0.00532, -0.00077] | 0.00271 | **CO** | **CO** |
| `ctrl_seed1` (ZERO thong tin) | -0.00221 | [-0.00427, -0.00041] | 0.00233 | khong (sat) | **CO** |
| `fs_noise` (nhieu thuan) | **-0.00400** | [-0.00663, -0.00136] | 0.00319 | **CO** | **CO** |

Nghia la: **tren 2024H1, chi doi seed huan luyen cung tao ra mot "hieu ung am co y nghia"**.
Do la ly do **moi** ung vien deu co `Delta` CONFIRM **am** (16/16 tren `g1_replay`, tru
`fs_taker_buy_7d` +0.0007) — do khong phai tinh chat cua cac ung vien, do la tinh chat cua
cua so. Cach doc dung:

> **Buoc CONFIRM cua thiet ke nay khong co suc phan biet** o `n_eff = 51`. Ket luan cua job
> **chi dua vao SELECT**, va o SELECT thi doi chung sach va **khong ung vien nao vuot nguong**.
> Neu mot ung vien co vuot o SELECT thi ta **cung khong** the xac nhan no o 2024H1 — day la
> gioi han da bi lo ra bang phep do, khong phai bang phong doan. Luat pre-reg muc 2b duoc viet
> cho nguong o **muc 3** (dinh nghia tren SELECT) nen truong hop (d) khong kich hoat; nhung
> pham vi ap dung cua CONFIRM **phai** bi ha xuong "khong ket luan".

---

## 3. BANG UNG VIEN — `Delta rankIC` khi THEM vao BASE7

Nguong = `sqrt(2 ln 16) * sd_boot(72h) = 2.354820 * sd`. Cot "3 block" = CI95 loai 0 o **ca ba**
do dai 72h/24h/168h. Sap theo `Delta` tren `g1_replay` SELECT (thuoc do CHINH).

### 3.1 Thuoc do chinh — `g1_replay` (mo phong dung luat exit G1), cua so SELECT (2022-2023)

| ung vien | nhom | `Delta` | CI95 khoi 72h | sd72 | nguong | vuot? | 3 block? | **PASS** | can metrics? |
|---|---|---|---|---|---|---|---|---|---|
| `fs_wick_up_7d` | microstructure | **+0.00433** | [-0.00346, +0.01220] | 0.00403 | 0.00950 | khong | khong | **khong** | khong |
| `fs_dd_speed` | drawdown | +0.00282 | [-0.00358, +0.00940] | 0.00332 | 0.00782 | khong | khong | khong | khong |
| `fs_dvol_7d` | thanh khoan | +0.00261 | [-0.00229, +0.00784] | 0.00261 | 0.00614 | khong | khong | khong | khong |
| `fs_dvol_ratio` | thanh khoan | +0.00235 | [-0.00237, +0.00724] | 0.00237 | 0.00559 | khong | khong | khong | khong |
| `fs_close_vwap_7d` | microstructure | +0.00150 | [-0.00314, +0.00636] | 0.00244 | 0.00576 | khong | khong | khong | khong |
| `fs_trdsize_7d` | thanh khoan | +0.00101 | [-0.00425, +0.00717] | 0.00284 | 0.00668 | khong | khong | khong | khong |
| `fs_fund_slope` | carry | +0.00098 | [-0.00616, +0.00771] | 0.00357 | 0.00841 | khong | khong | khong | khong |
| *`ctrl_seed7` (san nhieu)* | *doi chung* | *+0.00022* | *[-0.00337, +0.00360]* | *0.00176* | *0.00416* | *khong* | *khong* | — | — |
| *`ctrl_seed1` (san nhieu)* | *doi chung* | *+0.00008* | *[-0.00521, +0.00498]* | *0.00259* | *0.00610* | *khong* | *khong* | — | — |
| `fs_dd_term` | drawdown | -0.00055 | [-0.00609, +0.00501] | 0.00282 | 0.00664 | khong | khong | khong | khong |
| `fs_pos_7d` | drawdown | -0.00061 | [-0.00465, +0.00383] | 0.00211 | 0.00497 | khong | khong | khong | khong |
| *`fs_noise` (doi chung am)* | *doi chung* | *-0.00071* | *[-0.00432, +0.00273]* | *0.00183* | *0.00430* | *khong* | *khong* | — | — |
| `fs_amihud_7d` | thanh khoan | -0.00090 | [-0.00513, +0.00412] | 0.00236 | 0.00557 | khong | khong | khong | khong |
| `fs_up_streak` | microstructure | -0.00223 | [-0.00551, +0.00110] | 0.00170 | 0.00400 | khong | khong | khong | khong |
| `fs_fund_sum_7d` | carry | -0.00333 | [-0.00816, +0.00161] | 0.00251 | 0.00590 | khong | khong | khong | khong |
| `fs_fund_persist` | carry | -0.00513 | [-0.00964, -0.00056] | 0.00231 | 0.00544 | khong | khong | khong | khong |
| **`fs_body_ratio_7d`** | microstructure | **-0.00580** | **[-0.00973, -0.00105]** | 0.00224 | 0.00527 | **CO** | **CO** | **khong (dau AM)** | khong |
| `fs_taker_buy_7d` | microstructure | **-0.00731** | [-0.01369, -0.00011] | 0.00344 | 0.00809 | khong | khong | khong | khong |

**Khong mot dong nao co `PASS = CO`.** Truong hop tot nhat (`fs_wick_up_7d`, `+0.00433`) chi bang
**46%** nguong cua no va CI chua 0 o ca ba do dai block.

### 3.2 Thuoc do phu — `g1lite` (nhan S1 duoc train), cua so SELECT

| ung vien | `Delta` | CI95 khoi 72h | nguong | vuot? | 3 block? | PASS `g1lite`? |
|---|---|---|---|---|---|---|
| `fs_wick_up_7d` | +0.00287 | [-0.00604, +0.01230] | 0.01138 | khong | khong | khong |
| `fs_dvol_ratio` | +0.00250 | [-0.00492, +0.00933] | 0.00846 | khong | khong | khong |
| `fs_close_vwap_7d` | +0.00094 | [-0.00426, +0.00618] | 0.00625 | khong | khong | khong |
| `fs_dd_speed` | +0.00048 | [-0.00684, +0.00742] | 0.00873 | khong | khong | khong |
| `fs_amihud_7d` | +0.00044 | [-0.00448, +0.00658] | 0.00661 | khong | khong | khong |
| `fs_pos_7d` | -0.00064 | [-0.00574, +0.00509] | 0.00658 | khong | khong | khong |
| `fs_fund_slope` | -0.00286 | [-0.00940, +0.00319] | 0.00765 | khong | khong | khong |
| `fs_up_streak` | -0.00354 | [-0.00710, +0.00019] | 0.00441 | khong | khong | khong |
| `fs_dd_term` | -0.00475 | [-0.01290, +0.00249] | 0.00937 | khong | khong | khong |
| `fs_fund_sum_7d` | -0.00558 | [-0.01249, +0.00068] | 0.00790 | khong | khong | khong |
| `fs_trdsize_7d` | -0.00636 | [-0.01415, +0.00222] | 0.00963 | khong | khong | khong |
| `fs_dvol_7d` | -0.00644 | [-0.01472, +0.00191] | 0.01000 | khong | khong | khong |
| **`fs_fund_persist`** | **-0.00973** | **[-0.01687, -0.00242]** | 0.00878 | **CO** | **CO** | khong (AM) |
| **`fs_body_ratio_7d`** | **-0.01127** | **[-0.01719, -0.00498]** | 0.00727 | **CO** | **CO** | khong (AM) |
| **`fs_taker_buy_7d`** | **-0.01635** | **[-0.02562, -0.00539]** | 0.01222 | **CO** | **CO** | khong (AM) |

**Khong mot ung vien nao duong va vuot nguong tren `g1lite`.** => **truong hop (b) cung khong
xay ra**: khong co ung vien nao "thang tren nhan bi vol-confound roi that bai tren thuoc sat
tien thuc". Ket qua la **(c) thuan**.

### 3.3 Ba ung vien LAM HAI do duoc — ket qua duong (khong phai null)

Ba feature sau **lam xau di** chat luong xep hang. Muc do chac chan khac nhau theo thuoc do,
phai noi chinh xac: tren **`g1lite`** ca ba deu thoa `T2 + T3` voi **dau am** (tuc hai la ket
qua *do duoc*, khong phai null); tren **`g1_replay`** thi **chi `fs_body_ratio_7d`** vuot duoc
nguong hieu chinh, hai feature con lai co CI72 loai 0 nhung `abs(Delta)` chua dat nguong
(`fs_taker_buy_7d` 0.00731 vs 0.00809; `fs_fund_persist` 0.00513 vs 0.00544) nen theo luat
pre-reg phai doc la **chua phan biet duoc** tren thuoc do chinh.

| feature | `g1_replay` SELECT | `g1lite` SELECT | doc |
|---|---|---|---|
| `fs_taker_buy_7d` (ti le taker buy 7d tu kline) | -0.00731, CI [-0.01369, -0.00011] | **-0.01635, CI [-0.02562, -0.00539]**, vuot nguong, 3 block | hai manh nhat. Gia thuyet "mat can bang dong lenh la thong tin moi" **bi bac bo co huong**: them no vao lam ranker te di |
| `fs_body_ratio_7d` (ti le than nen 7d) | **-0.00580, CI [-0.00973, -0.00105]**, vuot nguong, 3 block | **-0.01127**, vuot nguong, 3 block | hai tren **ca hai** thuoc do |
| `fs_fund_persist` (do ben dau funding) | -0.00513, CI [-0.00964, -0.00056] | **-0.00973**, vuot nguong, 3 block | dung nhu rui ro da khai bao truoc trong pre-reg (proxy thoi gian/tuoi) |

Co che kha di (khong do duoc trong job nay, ghi la **gia thuyet**): ba feature nay co phan bo
rat hep va **troi theo che do** (`fs_taker_buy_7d` 1%-99% chi 0.4496–0.5111;
`fs_body_ratio_7d` 0.3690–0.4965; `fs_fund_persist` bi chan o +-21 va co trung vi 19), nen cay
dung chung nhu **bien chi bao che do/thoi gian** thay vi tin hieu cross-sectional — dung loai
rui ro ma `docs/DATA_EXTENT_SURVEY.md` muc 2(c) va feataudit D.3.3 (`f23 fundingPersistence`)
da canh bao. Neu ai muon thu lai ba feature nay thi phai **chuan hoa trong tick** truoc, va do
la mot pre-reg khac.

---

## 4. DOC KET QUA THEO PRE-REG MUC 6

| Truong hop | Kich hoat? | Bang chung |
|---|---|---|
| (e) pipeline SAI (`fs_noise` vuot nguong) | **KHONG** | `fs_noise` `Delta` = -0.00071, CI [-0.00432, +0.00273], nguong 0.00430 |
| (d) khong do duoc (doi chung seed vuot nguong) | **KHONG o SELECT** | seed1 +0.00008 / seed7 +0.00022 vs nguong 0.0061 / 0.0042. (**NHUNG** o CONFIRM thi kich hoat — xem 2.3, va he qua la buoc CONFIRM bi ha xuong "khong ket luan") |
| (a) CO thong tin moi | **KHONG** | 0/16 ung vien PASS tren `g1_replay` |
| (b) chi thang tren `g1lite` | **KHONG** | 0/16 ung vien duong va vuot nguong tren `g1lite` |
| **(c) KHONG AI THANG** | **CO — day la ket qua** | xem muc 3 |

### Ket luan bat buoc phai viet theo pre-reg cho truong hop (c)

> Khoang trong 80%+ toi tran oracle (S1 bat 17.8%) **khong** nam o feature suy tu du lieu
> **gia / khoi luong / funding** o thang **gio**. 15 gia thuyet kinh te doc lap, phu 5 nhom
> chua tung co trong S1 (thanh khoan/dollar-volume, carry funding, microstructure trong nen,
> order-flow taker, cau truc drawdown), **khong** nhom nao mang thong tin do duoc ngoai 7
> feature hien co. Bottleneck phai nam o:
> 1. **Lop du lieu khac** — order book (do sau, mat can bang bid/ask), trade-by-trade
>    (kich thuoc lenh that, khong phai trung binh gio), cross-exchange (co so, dan dat gia),
>    on-chain/flow san. Day cung la ket luan cua B6 (`AUDIT_APPLIED:81`) va cua feataudit E6.
> 2. **Cach dat bai toan** — khong phai "chon coin nao trong tick" ma "vao luc nao" /
>    "thoat the nao". Ung ho manh cho huong nay: feataudit C.4 do duoc **khong model nao**
>    xep hang duoc `retEnd_72h` (S1 = -0.0177, CI chua 0), tuc toan bo edge cua tang selector
>    nam o **hinh dang duong gia**, khong o loi suat cuoi ky.
> 3. **Tran oracle 38.34% ban chat khong dat toi duoc** vi phan lon no la nhieu khong du bao
>    duoc tu du lieu qua khu cua chinh coin do.

### He qua ve viec lui du lieu ve 2020-01 (cau hoi thiet ke chinh cua job)

Toan bo 15 ung vien that **chi can kline 1h + funding**, **khong can metrics** — dung uu tien
thiet ke da chot. Nhung vi **khong** ung vien nao thang, **khong co ung vien nao mo duong lui
DEV ve 2020-01**. Ba dieu con lai van dung va van co gia tri:

1. **Ha tang de lui da san.** Da xac nhan **do duoc**: Vision co kline 1h day du tu 2020-01
   cho toan universe, 294 symbol x 42 thang tai trong **191 giay**, cache **133 MB**, va neo
   nhan qua da duoc **do** (khong doan). Bat ky ai muon lui DEV chi con phai xu ly nhan
   (`label_15m`) va gate, khong phai feature gia.
2. **Bo BASE7 khong can metrics** (feataudit C.6 da do: `no_oi` khong phan biet duoc voi bo 9),
   nen **lua chon (b) cua `DATA_EXTENT_SURVEY`** (lui ve 2020-01, bo OI) **khong ton mot bit
   tin hieu nao o tang S1** — job nay tai xac nhan diem uoc luong do tren mot lan train khac
   (`base7` rank-IC `g1_replay` SELECT 0.04281 vs feataudit 0.0407 tren ALL).
3. Ly do de lui du lieu vi vay la **cong suat thong ke** (`MDE80` selector 12.46pp -> 9.28pp),
   **khong** phai "de feature moi hoat dong".

---

## 5. NHUNG CHO SU THAT NEN TRONG DE BAI CAN DINH CHINH / BO SUNG

1. **`vol_7d` khong con "khong phan biet duoc" o day, no AM tren `g1lite` khi doi base.**
   De bai (theo feataudit C.5) noi `vol_7d` co tac dung `+0.0244` tren `g1lite`. Dung — do la
   phep **bo** feature khoi bo 9. Job nay khong do lai dieu do va **khong** phan bien no.
   Nhung mot quan sat lien quan: khi **them** `fs_dvol_7d` (dollar-volume, ho hang gan nhat voi
   `vol_7d` ma la turnover) vao BASE7, `g1lite` **giam** `-0.00644`. Tuc thong tin "khoi luong"
   khong thay the duoc thong tin "bien dong loi suat" — hai thu khac nhau, va cai thu hai moi
   la cai `g1lite` thuong.
2. **"Ranker thuc chat thay 7" — xac nhan gian tiep, va BASE7 duoc dinh nghia lai cho ro.**
   De bai noi `dd_7d == rk_dd_7d` va `ret_3d == rk_ret_3d` trong tick nen ranker "thay 7".
   Trong job nay `BASE7` **khong** phai "7 tin hieu doc lap" do, ma la **9 feature `KEEP` tru
   2 feature OI** (= model `no_oi` cua feataudit C.6, cung goi la 7 feature). Hai cach dem deu
   ra so 7 nhung **khac tap hop**; pre-reg muc 1 da chot cach thu hai va ghi ro ly do
   (base khong chua du lieu ro ri; toan bo thi nghiem khong can metrics). Doc so trong bao cao
   nay theo dinh nghia do.
3. **De bai khuyen "GPU cho vong train nhieu bien the". Do la mot bay do luong o day.**
   `device="cuda"` cua `XGBRanker` khong tai lap duoc `pred_s1a2` (spearman 0.9855 < 0.999) va
   nhieu per-tick rank-IC cua no (**0.0184**) lon hon moi hieu ung can tim. Tren pipeline GPU,
   hai ung vien **vuot nguong gia**. Khuyen nghi: **moi phep do `Delta rankIC` cua du an nay
   phai chay CPU**; GPU chi dung cho viec khong doi hoi tai lap (vd quet tho).
4. **Kaggle CPU cung khong bit-identical voi Oracle CPU.** Cung `xgboost 3.2.0`, cung tham so:
   `keep9` rank-IC `g1lite` = **0.17040** (Kaggle) vs **0.1723** (Oracle/feataudit) — lech
   nam trong bien do seed (0.1720–0.1730) nhung **khong** bang nhau. Do la ly do moi so sanh
   ghep cap trong bao cao nay **chi so trong cung mot moi truong**. Bo sung nay dong bo voi
   `KAGGLE_RULES` muc 3e (hai duong doc ticker khong bit-exact).
5. **Buoc "xac nhan tach roi" tren 2024H1 khong co suc phan biet — do duoc, khong phong doan.**
   Doi chung seed (ZERO thong tin) cho `Delta = -0.0028`, vuot nguong va loai 0 o ca ba do dai
   block tren CONFIRM. Bat ky thiet ke tuong lai nao dung `n_eff ~ 51 khoi 72h` lam tap xac
   nhan cho mot phep so sanh **retrain** deu se cho ket qua rac. Muon co buoc xac nhan that thi
   phai (i) dai hon, hoac (ii) **trung binh nhieu seed** o ca hai nhanh de triet san nhieu
   huan luyen truoc khi bootstrap.
6. `PROCESS_LOG.md` (noi chua 4 quy tac cat feature R1-R4) — tai xac nhan **khong ton tai**
   tren dia va chua tung vao git; job nay khong phuc hoi duoc no.

---

## 6. NHUNG GI JOB NAY KHONG TRA LOI

- **OI / metrics**: loai tru co chu dich (pre-reg muc 2c.2) vi 6 cot metrics dang ro ri 5 phut
  voi `ts >= 2024-03-04` va **dang duoc sua**. Cau "OI co thong tin moi khong" **con mo**, phai
  do lai sau khi sua xong.
- **Feature o thang phut** hoac cua so ngan (< 24h). Moi ung vien o day dung cua so 24h/168h/720h
  tren luoi **gio**, dong bo voi 7 feature hien co. Mot lop feature ngan han (vi du 15m-4h) chua
  duoc thu; nhung luu y feature S1 von co the cu tơi 45 phut so voi thoi diem quyet dinh
  (`s1_rank.py:26,28`), nen loi ich cua feature rat ngan han bi cat bot ngay tu thiet ke join.
- **Feature cross-sectional**: loai bang ly le (pre-reg 2c.1) — bien doi don dieu trong tick la
  dong nhat hang, ranker khong thay.
- **Ap dung**: khong de xuat ap dung gi. Khong train G015. Khong chay sim/backtest.

## 7. PHU LUC — file

| File | Noi dung |
|---|---|
| `/home/ubuntu/fs/fs_dl.py` + `DL.out` | tai 294 symbol x 42 thang kline 1h -> cache npz |
| `fs_build2.py` + `BUILD2.out` | build 16 ung vien + guard mau so + 1,200 phep kiem nhan qua |
| `fs_pack.py` | dong goi bang train (1,220,490 dong x 32 cot) |
| `fs_env.py` + `ENV.out` | tai lap S1 tren Oracle CPU: spearman 1.000000 |
| `fs_run_cpu.py` + `RUNCPU.out` | 19 nhanh CPU (base7 + 2 doi chung seed + 16 ung vien) |
| `fs_boot2.py` + `BOOT_ORACLE.out` | block-bootstrap 72h/24h/168h, 2000 rep, seed 20260903 |
| `fs_boot_oracle_cpu.csv` / `fs_verdict_oracle_cpu.csv` | so tho + bang verdict |
| `out/fs_ticks_cpu.parquet` | rank-IC theo tung tick cho ca 19 nhanh (cho phep do lai khong can train) |
| `out/fs_results_cpu.jsonl` | 1 dong/nhanh, `fsync` ngay (luat 12h Kaggle) |
| `fs_boot_gpu_disq.csv` + `BOOT_GPU.out` | pipeline GPU **da bi loai** — chi luu lam vi du nhieu backend |
| `feat_fs.parquet` + `feat_fs.meta.json` | bang 16 ung vien, 4,944,054 dong |

---

## 8. BAN SAO DOC LAP TREN MOI TRUONG THU HAI (Kaggle CPU) — bo sung sau commit `c14107a`

Chay lai **toan bo 19 nhanh** bang script y het (`fs-cand-cpu`, `xgboost 3.2.0`, 4 vCPU,
`device` mac dinh = CPU). Day **khong** phai moi truong bit-identical voi Oracle (xem muc 5.4),
nen no la mot **phep kiem do ben doi voi nhieu backend** — dung loai nhieu da lam GPU bi loai.
So tho: `/home/ubuntu/fs/fs_boot_kaggle_cpu.csv`, `fs_verdict_kaggle_cpu.csv`,
`outk/fs_results_cpu.jsonl`, log `BOOT_KAGGLE.out`.

### 8.1 Hai cong doi chung — dat o ca hai moi truong

| doi chung | `Delta` `g1_replay` SELECT (Oracle) | (Kaggle) | vuot nguong? |
|---|---|---|---|
| `fs_noise` (nhieu thuan) | -0.00071 | -0.00328 | **khong** o ca hai |
| `ctrl_seed1` (ZERO thong tin) | +0.00008 | +0.00038 | khong |
| `ctrl_seed7` (ZERO thong tin) | +0.00022 | +0.00192 | khong |

### 8.2 Ket luan chinh — **giong nhau**: 0 ung vien CONFIRMED

**Khong ung vien nao `CONFIRMED` o moi truong nao.** Mot khac biet o **buoc man loc SELECT**:

| | Oracle CPU (**chinh thuc**, tai lap `pred_s1a2` spearman 1.000000) | Kaggle CPU |
|---|---|---|
| `fs_wick_up_7d` | `Delta` +0.00433, sd72 0.00403, **nguong 0.00950** => **khong vuot** | `Delta` +0.00567, sd72 0.00232, **nguong 0.00546** => **VUOT** (T1+T2+T3) |
| `fs_wick_up_7d` o CONFIRM | -0.00272 (dau doi) | -0.00036 (dau doi) | 
| => `CONFIRMED` | **khong** | **khong** (that bai o CONFIRM) |

Doc dung: hai moi truong **dong y ve diem uoc luong** (+0.0043 vs +0.0057, cung dau, cung do lon)
nhung **khong dong y ve viec no co vuot nguong hay khong**, vi `sd_boot` khac nhau **1.7 lan**
(0.00403 vs 0.00232). Theo pre-reg, moi truong quyet dinh la **Oracle** (moi truong duy nhat
tai lap duoc model dang chay), va o do no **khong vuot**. Va o **ca hai** moi truong no
**khong xac nhan duoc** tren 2024H1. => ket luan **(c)** khong doi.

### 8.3 Bang do ben cua DAU giua hai moi truong (`Delta` `g1_replay` SELECT)

Day la thong tin ma mot moi truong khong the cho, va no noi ro dau la "hieu ung nho nhung on
dinh" va dau la "nhieu thuan":

| ung vien | Oracle | Kaggle | dau on dinh? |
|---|---|---|---|
| `fs_wick_up_7d` | +0.00433 | +0.00567 | **duong, on dinh** — manh nhat, **van khong dat nguong o Oracle** |
| `fs_dvol_7d` | +0.00261 | +0.00631 | **duong, on dinh** |
| `fs_dvol_ratio` | +0.00235 | +0.00185 | duong, on dinh |
| `fs_trdsize_7d` | +0.00101 | +0.00408 | duong, on dinh |
| `fs_fund_slope` | +0.00098 | +0.00383 | duong, on dinh |
| `fs_dd_speed` | +0.00282 | -0.00289 | **DOI DAU** => nhieu |
| `fs_close_vwap_7d` | +0.00150 | -0.00295 | **DOI DAU** => nhieu |
| `fs_dd_term` | -0.00055 | +0.00154 | **DOI DAU** => nhieu |
| `fs_amihud_7d` | -0.00090 | -0.00295 | am, on dinh |
| `fs_pos_7d` | -0.00061 | -0.00370 | am, on dinh |
| `fs_up_streak` | -0.00223 | -0.00309 | am, on dinh |
| `fs_fund_sum_7d` | -0.00333 | -0.00616 | am, on dinh |
| `fs_fund_persist` | -0.00513 | -0.00579 | am, on dinh |
| `fs_body_ratio_7d` | -0.00580 | -0.00179 | am, on dinh |
| `fs_taker_buy_7d` | **-0.00731** | **-0.01017** | **am, on dinh, LON NHAT** |
| *`fs_noise`* | *-0.00071* | *-0.00328* | *am (nhieu)* |

### 8.4 Hai khang dinh duoc CUNG CO them

1. **`fs_taker_buy_7d` lam hai — tai lap tren ca hai moi truong.** `g1_replay` SELECT
   -0.0073 / -0.0102 (Kaggle: vuot nguong + loai 0 ca 3 block); `g1lite` SELECT
   -0.0164 / -0.0195 (vuot nguong o ca hai). Day la ket qua **duong**, khong phai null: ti le
   taker-buy 7 ngay tu kline **khong** chi la vo dung ma **lam xau** kha nang xep hang cua S1.
2. **Ung vien co trien vong nhat la `fs_wick_up_7d` (ti le rau tren), va no CHUA du.**
   Diem uoc luong duong on dinh o ca hai moi truong (+0.0043 / +0.0057) — cung huong voi gia
   thuyet "nguon cung hap thu cac cu bat". Nhung: khong dat nguong hieu chinh o moi truong
   chinh, va **doi dau o 2024H1 o ca hai moi truong**. Neu ai muon theo dam nay thi phai la mot
   **pre-reg moi voi N = 1** (nguong `1.96*sd` thay vi `2.3548*sd`) va mot **tap xac nhan co
   suc phan biet that** (khong phai 51 khoi 72h — xem muc 2.3), cong voi **trung binh nhieu
   seed** o ca hai nhanh de triet san nhieu huan luyen. Chi phi do la that; **job nay khong
   duoc phep tu lam dieu do** vi se la leak L2 (chon dam sau khi xem so).

### 8.5 Ghi chu ve file so tho

`.gitignore:7` cua repo bo qua `*.csv`, nen `fs_boot_*.csv` / `fs_verdict_*.csv` **khong** vao
git (giong `feataudit/*.csv`). Chung nam o `/home/ubuntu/fs/`; moi con so trong bao cao nay da
duoc dan nguyen van tu chung.
