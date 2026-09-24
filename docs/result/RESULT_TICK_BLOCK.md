# RESULT_TICK_BLOCK — chan ca LUOT (tick) khi luot YEU: **NULL / NO-GO** (giu T170)

Ngay: 2026-09-23. Pre-reg: **`docs/prereg/PREREG_TICK_BLOCK.md` (commit `b98c9ff`)** — chot TRUOC khi chay.
Script: `research/analysis/tickblk_run.py` (day 4 chan/chay-tiep len Kaggle), `research/analysis/tickblk_score.py`
(cham diem). **Toan bo sim chay tren Kaggle CPU kernel** — **khong** chay Java sim tren Oracle (job `shadow-c3`
van `active`), **khong** `claude-run`/Claude Code, **khong push**, **khong cham 2026** (du lieu <= 2025-12-31).
Trung gian: `/tmp/tickblk_*`.

---

## 0. KET LUAN (mot dong)

> **NULL / NO-GO cho ca 3 bien the.** Chan ca LUOT **KHONG** giam exposure nhu ky vong va **KHONG** cai thien
> chat luong: `DEPTH` chan 23,28% so luot nhung net chi mat **3 lenh** (gross 92 — 96,7% duoc vao lai o luot
> khac); `DROP15M` chan 23,80% so luot ma net mat **0 lenh** (gross 1); chi `BREADTH` chan 97,90% so luot moi
> that su giam duoc 261 lenh (24%). **0/5 rate chat luong ngoai CI o ca 3 bien the** (moi CI deu chua 0).
> Co che "chan COIN vo hieu" (D3) **tai xuat nguyen ven o tang LUOT**: he chuyen lenh sang **luot ke tiep**
> trong cung pool/score, nen exposure duoc quyet dinh boi *kha nang vao lenh tren ca cua so*, khong boi mot luot.

---

## 1. CONG BUOC 0 — parity T170 tren nen jar MOI: **PASS**

| hang muc | gia tri |
|---|---|
| Bundle / ticker | `chuyendinh/sim-x1-2021-bundle` + 7 dataset `wfo-ticker-2021..2025h2` (1.826 ngay, khong thieu) |
| Profile / cua so | `x1_gs_t170`, `SIM_END_DATE=20251231`, `TICKER_SOURCE=file`, 2021-07-01..2025-12-30 |
| `tickblk2-par` (jar MOI, co OFF) | equity **111070**, n=**1089**, mapper 863, JVM **1182,8s**, `JAR_SHA256=715043edab1f96a04ed97e3169b8634c14667dae4a31f13188a3217192b2a048` |
| md5 `printDone.csv` | **`efb793e2468ca3a7318da0f0ad23d4fc`** = ban Oracle `X1_GS_T170_2021` |
| `diff` voi ban parity cua vong SELCUT (`selcut-par0`) | **0 dong** ⇒ byte-identical |

⇒ Nen dung, jar dung; **chi khi cong nay PASS moi doc so 3 bien the** (dung `docs/prereg/PREREG_TICK_BLOCK.md` §3.1).

### 1.1 🔴 BAN CHAY 1 (tag `tickblk-*`) BI LOI va DA BO — ghi nguyen van

Trong luc kiem tra doc lap, phat hien **`new float[(WIN+1)*1440]` cua Java khoi tao = `0.0f`, KHONG phai `NaN`**
⇒ moi slot **CHUA GHI** bi tinh la "mau hop le" ⇒ (a) so mau luon >= `MIN_SAMPLES` ⇒ **warm-up 14 ngay bi VO
HIEU** (nguong = 0.0 ngay tu ngay 1), va (b) chan luon moi phut co `rateDownAvg >= 0` ⇒ **chan them 9.656 phut
trong 2021-07-01..2021-09-17**, trai voi thiet ke da pre-reg (`PREREG_TICK_BLOCK` §1.2: *"chua du 20.160 mau
hop le thi KHONG chan"*).

Do bang **ban tai lap Python doc lap** (doc truc tiep `market.bin`, cung cong thuc quantile):

| mode | so phut bi chan | khop voi Java |
|---|---:|---|
| 0-init (dung ban chay 1) | 560.539 | **560.538/560.538** (lech 1 phut do bien cua so) |
| NaN-init (= thiet ke pre-reg) | **550.883** | — |
| `A \ B` (0-init chan them) | **+9.656 phut**, tat ca trong 2021-07-01..2021-09-17 | `B \ A` = **0** |
| 0-init cho `DROP15M` | 559.398 vs Java 559.637, `thrLast` khop tung chu so (`-0,008701`) | 99,94% |

⇒ Da **sua** (fill `NaN` truoc khi dung, commit `4d8d9c5`, jar `715043ed…`) va **CHAY LAI TOAN BO** duoi tag
`tickblk2-*`. **Moi so trong bao cao nay la cua ban DA SUA.** Ban chay 1 van duoc giu lam bang chung
(so lenh **y het**: depth 1086 / breadth 828 / drop15 1089 — chi so phut bi chan doi 23,68%→23,28% o DEPTH).
Khong doi mot dong nao cua thiet ke (chi so / muc cat 25% / cua so 30 ngay / pham vi chan).

---

## 2. Commit

| commit | noi dung |
|---|---|
| `b98c9ff` | **PREREG_TICK_BLOCK** (chot TRUOC khi chay) |
| `079a897` | Code: class `TickWeakBlock` + 5 key `SIM_TICK_BLOCK_*` (default OFF) + 3 guard tai `Simulator` + 2 script runner/scorer. jar sha `d14129bf…` |
| `4d8d9c5` | **FIX warm-up** (NaN init) + `tickblk_run.py` chuyen sang tag `tickblk2-*`. jar sha `715043ed…` |

## 3. Chan chay + tai nguyen Kaggle (chi phi **0** — CPU kernel khong tinh quota)

| chan | tag | JVM | so lenh | equity cuoi |
|---|---|---:|---:|---:|
| cong parity jar1 | `chuyendinh/sim-tickblk-par` | 1214,3s | 1089 | 111070 |
| V1/V2/V3 (ban 1, **BO**) | `tickblk-depth/breadth/drop15` | 1248,3 / 1129,6 / 1116,2s | 1086 / 828 / 1089 | 109941 / 68933 / 111170 |
| cong parity jar2 | `chuyendinh/sim-tickblk2-par` | 1182,8s | 1089 | 111070 |
| **V1 `DEPTH`** | `chuyendinh/sim-tickblk2-depth` | **1203,3s** | **1086** | **109941** |
| **V2 `BREADTH`** | `chuyendinh/sim-tickblk2-breadth` | **1142,2s** | **828** | **68933** |
| **V3 `DROP15M`** | `chuyendinh/sim-tickblk2-drop15` | **1102,8s** | **1089** | **111170** |

**8 chan** (4 bo + 4 dung), 4 dot (parity → 3 bien the, moi dot song song), wall **~2h20'**; tong JVM ~2,6 gio;
tran 5 slot khong bi cham (toi da 3 kernel cung luc). Dataset moi: `chuyendinh/sim-jar-tickblk` (95MB, chi
chua `sim.jar`) — v1 = `d14129bf…` (bo), **v2 = `715043ed…`** (dung); kernel in `JAR_SHA256=` va ghi vao
`result.json` nen **khong the** dung nham jar.

---

## 4. EXPOSURE — % luot bi chan va SO LENH MAT (cau hoi chinh)

`minutes=2.367.360` (= 1644 ngay x 1440, bang nhau o ca 3 bien the). "gross" = so lenh parity co `start`
roi vao **phut bi chan** (doi chieu `storage/tickblk_blocked_min.csv` do sim ghi); "net" = `n(parity) - n(bien the)`.

| bien the | % luot bi chan | gross (lenh parity roi vao luot chan) | net mat | vao lai duoc o luot khac |
|---|---:|---:|---:|---:|
| `DEPTH` | **23,28%** (551.006) | **92** = 8,45% so lenh | **-3** | 89/92 = **96,7%** |
| `DROP15M` | **23,80%** (563.497) | **1** = 0,09% so lenh | **0** | 1/1 = 100% |
| `BREADTH` (degenerate, xem §7) | **97,90%** (2.317.691) | **447** = 41,05% so lenh | **-261** (24%) | 186/447 = 41,6% |

- **Tu-kiem do exposure**: `gross_van_con_trong_bien_the = 0` o ca 3 ⇒ khong lenh nao "tuong vao roi ma van con"
  (phep do khong bi ao giac); moi lenh o phut bi chan **that su** bi chan.
- **Doc dung**: "% luot bi chan" **KHONG** phai "% quyet dinh bi anh huong". Ca 2.367.360 luot chi co **433 phut
  co lenh mo** o parity. Vi vay `DROP15M` chan 23,8% so luot ma gross = **1 lenh**, con `DEPTH` (cung ~24%)
  gross = 92 lenh — hai tap luot chan **khac han nhau ve muc do "trung" voi phut vao lenh**.
- ⇒ **Nut that khong phai "luot" ma la "kha nang vao lenh tren CA CUA SO"**: khi 1 luot bi chan, symbol do
  **khong** bi khoa, va selector duoc xet lai **moi phut** voi cung bo score 15M (forward-fill) ⇒ lenh
  **chuyen sang luot ke tiep** (96,7% o DEPTH). Day dung la co che da lam `D3` vo hieu (loc 4.942 candidate
  nhung net chi -109 lenh) — chi khac la bay gio no xay ra **giua cac luot** thay vi **trong 1 luot**.
- Chi khi chan ~**98%** so luot (V2) thi moi that su cat duoc 24% so lenh ⇒ quan he "%luot chan → %lenh mat"
  **cuc ky phi tuyen** (24% → 0-8%; 98% → 24%).

## 5. PRIMARY — 5 rate chat luong (toan bo leg) vs parity

CI block-72h paired, 2000 rep, seed `20260905`, neo co dinh `2021-07-01`; bao **CA HAI** do rong: `x1.21`
(brief yeu cau) va `inflate(3)=1,4823` (chuan hoa cho k=3). "Ngoai CI" chi tinh khi ngoai o **CA HAI**.

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---:|---:|---:|---:|---:|---:|
| PARITY | 1089 | 88,25 | 9,73 | 7,642 | -16,992 | 5,244 |
| `DEPTH` | 1086 | 88,40 | 9,67 | 7,638 | -16,998 | 5,256 |
| `BREADTH` | 828 | 87,20 | 10,51 | 7,367 | -19,263 | 4,569 |
| `DROP15M` | 1089 | 88,25 | 9,73 | 7,642 | -16,974 | 5,246 |

Hieu (bien the − parity) + CI:

| bien the | win% | TSloss% | mP\|SM | mP\|SL | meanP | rate ngoai CI |
|---|---|---|---|---|---|---|
| `DEPTH` | +0,152 [-0,203,+0,664] | -0,065 [-0,312,+0,153] | -0,004 [-0,219,+0,180] | -0,006 [-0,227,+0,168] | +0,012 [-0,190,+0,195] | **0/5** |
| `BREADTH` | -1,048 [-2,492,+0,564] | +0,774 [-0,832,+2,612] | -0,275 [-1,654,+0,611] | -2,272 [-6,537,+1,067] | -0,675 [-2,034,+0,329] | **0/5** |
| `DROP15M` | 0,000 | 0,000 | 0,000 | +0,018 [-0,006,+0,064] | +0,002 [-0,001,+0,006] | **0/5** |

(CI in o do rong `x1.21`; o `inflate(3)` rong hon ⇒ cung khong co rate nao ngoai — json day du:
`/home/ubuntu/kaggle_sim/out/tickblk2_score_all.json`.)

- `DEPTH`/`DROP15M`: khong rate nao doi theo huong co nghia (moi |hieu| < 0,1 don vi rate).
- `BREADTH` (ban chan 98% luot): 5/5 hieu di theo huong **XAU** nhung **deu chua ngoai CI** — chat luong
  KHONG giu duoc khi phai vao lenh o 2,1% luot con lai (win% -1,05; mP|SL -2,27; meanP -0,68).
- **Ket luan PRIMARY: 0 bien the dat cong `>=2 rate ngoai CI cung huong tot` ⇒ NULL** (khong bien the nao
  co rate XAU ngoai CI ⇒ khong co "bang chung nguoc", chi la **khong co bang chung**).

## 6. Theo LEVEL + PnL/equity RIENG (khong dung de chon)

| tag | level | n | SumPnL | meanP | win% | TSloss% |
|---|---|---:|---:|---:|---:|---:|
| PARITY | PREDICT_SYMBOL_TRADE / BIG_DOWN / DCA_LEVEL1 | 821 / 248 / 20 | 47114 / 16254 / 12701 | 4,221 / 4,786 / 52,888 | 88,31 / 88,71 / 80,00 | 10,11 / 8,47 / 10,00 |
| `DEPTH` | — | 819 / 248 / 19 | 46657 / 15967 / 12317 | 4,218 / 4,709 / 57,123 | 88,52 / 88,31 / 84,21 | 9,89 / 8,87 / 10,53 |
| `BREADTH` | — | 564 / 248 / 16 | 15510 / 12075 / 6348 | 3,138 / 4,597 / 54,554 | 87,06 / 87,90 / 81,25 | 10,82 / 9,27 / 18,75 |
| `DROP15M` | — | 821 / 248 / 20 | 47189 / 16270 / 12712 | 4,224 / 4,786 / 52,888 | 88,31 / 88,71 / 80,00 | 10,11 / 8,47 / 10,00 |

- Lenh bi chan gan nhu **100% thuoc leg SELECTOR** (`PREDICT_SYMBOL_TRADE`): 92/92, 446/447, 1/1.
  **`BIG_DOWN` khong he bi chan o DEPTH/DROP15M** (248 -> 248) — dung nhu thiet ke: no chi kich hoat khi
  `rateDownAvg < -0,03157` (duoi rat nong), khong bao gio nam trong nhom "nguoi" bi chan.
- **PnL/equity rieng**: equity cuoi 111070 -> **109941** (`DEPTH`, -1,0%) / **111170** (`DROP15M`, +0,09%) /
  **68933** (`BREADTH`, -37,9%); SumPnL 76070 -> 74941 / 76170 / 33934. Khong dung de chon (chi bao cao).

## 7. Rang buoc CUNG (`docs/runbooks/RISK_APPETITE.md`) + tap trung

| tag | maxDD/nam | UW | quy xau nhat | nam am | conc 1 coin | PASS? |
|---|---:|---:|---:|---:|---:|---|
| PARITY | -11,84% (2022) | 92 | -0,92% | khong | 9,77% | PASS |
| `DEPTH` | **-7,99%** (2022) | 119 | -0,98% | khong | **7,26%** | **PASS** |
| `DROP15M` | -11,85% (2022) | 92 | -0,92% | khong | 9,77% | **PASS** |
| `BREADTH` | -7,94% (2022) | **205 > 200** | -1,93% | khong | 7,26% | **FAIL** |

`DEPTH` **cai thien rui ro** (maxDD -11,84% -> -7,99%; tap trung 9,77% -> 7,26%) nhung **khong** cai thien
chat luong ⇒ no la "bot exposure mot chut", khong phai mot cai thien.

### 7.1 ⚠️ GHI CHU BAT BUOC ve V2 `BREADTH` (bien the degenerate)

Luat pre-reg ("chan khi `x <= Q0.25` cua cua so cuon") duoc **thuc thi dung**, nhung **phan bo cua chi so
`breadth` co diem khoi luong lon tai 0** (return 1M <= -3% la bien co rat hiem) ⇒ `Q0.25 = 0,0` dung bang
⇒ "nhom te nhat" theo luat = **moi luot co `breadth == 0`** = **97,90% so luot** ⇒ V2 tren thuc te la bien the
"**chan gan het luot**", KHONG phai "cat 25%". Vi vay:
- V2 **khong** duoc doc nhu mot phep kiem "cat 25%" (no la phep kiem co che, o cuong do cuc dai);
- V2 **FAIL rang buoc cung** (UW 205) ⇒ du no co rate ngoai CI thi cung khong dung duoc;
- **KHONG** duoc sua thiet ke (doi nguong, doi chi so) sau khi thay so — neu muon mot V2 dung nghia "cat
  25%", phai pre-reg mot chi so breadth khac (vd ti le coin duoi MA n phut) cho **vong sau**.

## 8. Vi sao NULL — co che (ket luan co tinh chuyen huong)

> **Don vi "luot" khong phai la don vi khan hiem.** Thu he thuc su khan la **kha nang vao lenh** (pool score
> 15M + gate + budget + tier). Chan mot luot chi **hoan** quyet dinh sang luot ke tiep (cung symbol, cung
> score), nen "%luot bi chan" va "%lenh mat" gan nhu **doc lap** (DROP15M: 23,8% luot -> 0 lenh net). Muon
> giam exposure that su phai doi **cai gi do gan voi symbol/kha nang vao lenh** (gate, sizing, so luot cho
> phep/ngay, budget) — chu **khong** phai "cat luot" hay "cat coin".
> Ket qua nay **cung co** ket luan cua `RESULT_D3D4_FILTER_SIM` (§2) va `RESULT_SELECTOR_LEG_CUT` (phan bo
> von/co che khoa khong phai nut that), va **khong** phu nhan phat hien TIMING cua `RESULT_HARNESS_CONTROL`
> (§3) — no bat che do TIMING **khong the** khai thac bang cach chan luot.

## 9. Nhung gi vong nay KHONG ket luan duoc (trung thuc)

1. **Khong** ket luan ve gia thuyet H1 ("luot nguoi = luot yeu") theo huong *dung*: ca `DEPTH`/`DROP15M`
   deu chan nhom **nguoi**, ket qua chat luong **di ngang** ⇒ tren book T170, "luot nguoi" **khong** te hon
   "luot nong" (khac voi doc lap suy tu MOM15 vi MOM15 la tin hieu khac, fire o nhom cuc nong).
   Gia thuyet doi lap H0' ("luot nong moi yeu") **chua duoc kiem** — phai pre-reg rieng.
2. **Khong** ket luan ve muc cat khac (20/33/40%): pre-reg chot **mot** muc 25%, **khong quet** — va do
   V1/V3 deu 0/5 rate, mot muc khac cung kho doi ket luan.
3. **Khong** ket luan ve `BIG_DOWN`/`DCA_LEVEL1` khi bi chan (chung 248/20 lenh, khong bao gio roi vao nhom
   bi chan) ⇒ phep thu "chan ca luot gom BIG_DOWN" **chua duoc kich hoat** boi 2/3 chi so.
4. **Khong** ket luan ve 2026 (seal) hay VALIDATION.

## 10. Tu-kiem cong cu + ve sinh

- Cong parity 2 lan (jar `d14129bf` va `715043ed`) deu ra md5 `efb793e2468ca3a7318da0f0ad23d4fc` ⇒ nhanh
  OFF **byte-identical** (co `SIM_TICK_BLOCK_IND` khong khai ⇒ `tickBlocked` luon false).
- Ban tai lap Python doc lap (`research/analysis/tickblk_verify.py`, doc truc tiep `market.bin`; 1 lenh: `python3 research/analysis/tickblk_verify.py DEPTH --ab`)
  khop Java **99,94-100%** so phut bi chan va khop `thrLast` tung chu so o ca 2 chi so ⇒ cong thuc cuon/quantile
  duoc kiem doc lap, khong chi tu tin vao code. Tren ban DA SUA: DEPTH replica 550.883 / Java **551.006**
  (giao 550.879, "chi Java" 127 — deu la phut bien cua so 2021-06-30 va phut hiem dau run);
  DROP15M replica 563.192 / Java **563.497** ("chi replica" = 0).
- `blocked_van_con_trong_bien_the = 0` (phep do do exposure khong bi ao giac).
- **Ve sinh temp**: xoa `storage/tickblk_blocked_min.csv` cua **3 chan ban 1** (da bo: 8,4 + 35,1 + 8,4 = ~52MB);
  giu `printDone.csv` + `sim.out` + `result.json` + `full.log` cua ca 8 chan (bang chung so, ~60MB)
  + `/home/ubuntu/kaggle_sim/out/tickblk2_score_all.json` (raw cua script cham). Xoa script tam o `/tmp/tickblk_*.py`.
- Thu muc stage jar: `/home/ubuntu/tickblk_jar/` (ban copy `sim.jar` sha `715043ed…`).
- **Side effect phai ghi ro**: buid maven ghi de in-place `/home/ubuntu/selcut_jar/sim.jar` (hardlink cung
  inode voi `target/original-*.jar` cua vong SELCUT) ⇒ thu muc stage **local** cua vong SELCUT mat noi dung
  jar cu; **dataset Kaggle `sim-jar-selcut` KHONG bi anh huong** (da la snapshot `99698846` byte) va khong
  chan nao cua vong nay doc tu do.
- Flog `SELECTOR_LEG_CUT` va `SIM_TICK_BLOCK_*` deu **default OFF**; **khong** bat o bat ky profile nao;
  `shadow-c3` khong bi dung toi (khong stop/kill/systemctl) — chi doc file.
