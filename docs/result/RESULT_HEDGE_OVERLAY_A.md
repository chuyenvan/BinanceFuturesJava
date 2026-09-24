# RESULT_HEDGE_OVERLAY_A — Phuong an A (overlay hedge BTC counterfactual): **NULL**

Ngay: 2026-09-20. Branch `module`. Pre-reg: `docs/prereg/PREREG_HEDGE_OVERLAY_A.md` (commit `03c037e`,
chot **truoc** khi tinh so). Code: `research/analysis/hedge_overlay_a.py`.
Ket qua thoi: `/home/ubuntu/hedge_a/hedge_overlay_a.json` (+ `_clip3.json`).

**KHONG sua file `.java` nao. KHONG chay sim Java.** Sach long T170 giu nguyen byte-identical
(khong co gi duoc chay lai; cong `md5 efb793e2` thoa hien nhien).

---

## 0. TL;DR

| | T170 GOC | T170 + HEDGE OVERLAY | |
|---|---|---|---|
| **ICC** (cohort = ngay vao lenh) | **+0.0516** | **+0.2208** | 🔴 **XAU DI 4.3 lan** |
| tran so cuoc doc lap `1/ICC` | **19.4** | **4.5** | 🔴 |
| `n_eff(k_bar=3.55)` | **3.13** | **2.27** | 🔴 −27% |
| beta ngay | +0.04866 | **−0.01340** | 🟢 beta BI TRIET (|b_h| = 0.28·|b_0|) |
| `%beta` tong loi nhuan log | 3.9% | −1.0% | 🟢 |
| `r2` hoi quy beta ngay | 0.0312 | 0.0015 | 🟢 |
| `|t(alpha)|` | 4.372 | 3.124 | — |
| equity cuoi | 111,070 | 117,741 | |
| CAGR | 29.27% | 30.96% | |
| maxDD | **−11.84%** | **−17.32%** | 🔴 |
| UW (ngay duoi nuoc lien tiep) | **92** | **266** | 🔴 |
| rang buoc cung theo nam (5 nam) | **PASS 5/5** | **PASS 3/5** (2022, 2025 FAIL) | 🔴 |

**PHAN QUYET theo nguong da KHOA o pre-reg muc 9: `NULL`.**
Nhanh NULL duoc kich hoat boi dieu kien ICC: `ICC_h = 0.2208 > 0.85 x ICC_0 = 0.0439`.
(Dieu kien NULL thu hai — `maxDD_h < 1.50 x maxDD_0 = −17.76` — o **sat bien** va KHONG kich
hoat: −17.32 > −17.76. Khong can den no.)

**KHUYEN NGHI: KHONG dau tu vao Phuong an B. Dong huong hedge-beta o day.**

---

## 1. Gia thuyet bi BAC BO voi co che DA HOAT DONG

Day la dang NULL manh nhat co the co: **hedge lam DUNG viec no phai lam** — beta ngay cua so
tu +0.04866 ve −0.01340, `%beta` tu 3.9% ve −1.0%, `r2` tu 0.0312 ve 0.0015 (tuc BTC gan nhu
khong con giai thich duoc bien dong ngay cua so) — **nhung ICC KHONG giam, ma TANG 4.3 lan.**

=> **H1 sai**: tuong quan chep-lenh trong ngay cua T170 **khong** den tu market beta BTC.
Con lai la cac co che chung khac (cung gate, cung sizing/throttle, cung regime thanh khoan,
cung dang pump-lottery) ma overlay beta khong dong toi.

Vi sao ICC con TANG? Vi PnL hedge duoc phan bo pro-rata cho moi lenh dang mo cung khoang
(cong thuc da KHOA o pre-reg muc 7) => no la mot **cu soc CHUNG moi** cong vao moi lenh cung
cohort. Beta rolling causal uoc luong rat nhieu (med 0.935, p05 −1.97, p95 +2.95) nen cu soc
chung nay LON so voi phuong sai rieng cua tung lenh. Noi ngan: overlay **khong bo bot** mot
nhan to chung, no **them vao** mot nhan to chung.

---

## 2. 🔴 Phat hien quan trong hon ca phan quyet: **ICC = 0.247 la cua C2b, KHONG phai cua T170**

Pre-reg muc 8b da canh bao truoc va do lai. Ket qua do truc tiep tren sach T170 bang **dung**
`icc_anova()` cua `research/analysis/nbets_step3_crosssec.py`:

| | `ICC` | `J` (cohort) | `N` | `k_bar` | `n_eff(k_bar)` | tran `1/ICC` |
|---|---|---|---|---|---|---|
| C2b (lich su, `NBETS_RESULT.md` 4.2) | +0.2468 | 101 | 952 | 4.88 | 2.49 | **4.05** |
| **T170 (do trong vong nay)** | **+0.0516** | 105 | 1084 | 3.55 | **3.13** | **19.38** |

Kiem do ben theo cohort khac (mo ta): T170 goc `72h` = +0.0512, `tuan` = +0.0482 — rat on dinh.

**He qua cho `docs/notes/power_wall.md`:** phat bieu "ICC = 0.247 => tran ~4 cuoc doc lap/ngay" la
**dac tinh cua C2b**, khong phai cua incumbent hien tai. Voi T170 tran la **~19 cuoc**, va
`n_eff` thuc (3.13) bi chan boi **`k_bar` = 3.55 vi the giu dong thoi**, KHONG phai boi ICC.
=> Neu muon tang so cuoc doc lap cua T170, don bay dung la **so vi the giu dong thoi / tan suat
vao lenh** (T170 chi vao lenh o **105 ngay** trong 1,644 ngay, 76.9% so gio khong giu gi),
**khong phai** giam tuong quan. TASK 2 nham vao nut that cua he thong CU.

---

## 3. So lieu chi tiet

### 3.1 Cau hinh thuc thi (dung pre-reg)
- Cua so 2021-07-01..2025-12-31; 1,089 lenh; luoi rebalance **1h**, 39,480 moc.
- `Nopen` trung binh 1,541 USDT; max 49,434; **77.7% so gio khong co vi the nao**.
- `beta_roll` N=**60** ngay lich, toi thieu 20 quan sat, CAUSAL (chi dung `d <= D-1`):
  hoat dong **1,544/1,644 ngay**; mean 0.133, med 0.935, p05 −1.973, p95 +2.947.
- Funding BTCUSDT tu Aerospike local (ns `test`, set `funding_data`, bin `f_data`):
  **6,042 settlement**, dung 8h/lan, 2021-01-01..2026-07-07, **85.55% rate duong**,
  tong rate trong cua so = +0.3633.

### 3.2 Phan ra PnL cua chan hedge (USDT)
| thanh phan | uncapped | sens. clip ±3 |
|---|---|---|
| PnL gia (short BTC) | +10,549.2 | +11,460.7 |
| PnL funding (**short NHAN khi rate>0** — dau Binance THAT) | **+76.2** | +122.1 |
| chi phi giao dich (0.0006 x turnover) | −3,955.0 | −2,703.9 |
| **TONG hedge PnL** | **+6,670.5** | **+8,878.9** |
| turnover notional | 6,591,652 | 4,506,481 |
| hedge notional trung binh / |max| | 1,003.7 / **676,811** | 1,175.9 / 148,301 |

Kiem tra bat buoc cua pre-reg muc 7: `sum_i hedge_pnl_i` = `sum_t hedge_pnl(t)`, sai so
**5.5e-12** (uncapped) va **0.0** (clip3); `unallocated = 0`. ✅

⚠️ `|hedge notional| max = 676,811` = **6.1 lan equity** — do duoi cua uoc luong beta (0.45% so
ngay co |beta|>10). Day la mot dau hieu ro rang rang beta rolling causal tren du lieu nay
**khong du on dinh de hedge that**.

### 3.3 Rang buoc cung theo nam (`x1_rates.py::hard_by_year`: maxDD<=15, UW<=120, nam>=0, quy>=−5)
| nam | GOC maxDD/UW/PASS | HEDGED maxDD/UW/PASS |
|---|---|---|
| 2021 | −2.46 / 37 / PASS | −4.84 / 37 / PASS |
| 2022 | −11.84 / 72 / PASS | −16.65 / 100 / **FAIL** |
| 2023 | −2.73 / 63 / PASS | −2.30 / 78 / PASS |
| 2024 | −6.60 / 92 / PASS | −4.99 / 74 / PASS |
| 2025 | −4.23 / 52 / PASS | −8.36 / **168** / **FAIL** |

### 3.3b [TASK C 2026-09-20] Rang buoc cung theo nam — khau vi HIEN HANH (maxDD<=30%,
UW<=200, nam khong am, quy>=−15%; tap trung 1 coin<=15% KHONG do o day, xem
`docs/result/RESULT_VOL_TARGET.md` muc 3). Cham lai tu CUNG so tho o bang tren, doi chieu bang cong cu
`x1_rates.py --appetite current` (bang cu o tren KHONG bi xoa).

| nam | GOC maxDD/UW/PASS | HEDGED maxDD/UW/PASS |
|---|---|---|
| 2021 | −2.46 / 37 / PASS | −4.84 / 37 / PASS |
| 2022 | −11.84 / 72 / PASS | −16.65 / 100 / PASS |
| 2023 | −2.73 / 63 / PASS | −2.30 / 78 / PASS |
| 2024 | −6.60 / 92 / PASS | −4.99 / 74 / PASS |
| 2025 | −4.23 / 52 / PASS | −8.36 / 168 / PASS |

**Ca GOC va HEDGED PASS 5/5 nam theo khau vi hien hanh** (khac khau vi CU: HEDGED FAIL 2022 va
2025 o do). Nhung **toan ky** (bang muc 0): GOC PASS moi rang buoc (maxDD −11.84%>=−30%,
UW 92<=200); **HEDGED FAIL rieng UW toan ky = 266 > 200** — moi nam rieng le deu <=200 nhung
mot chuoi duoi-nuoc thuc te bac qua ranh gioi nam dai hon bat ky nam rieng le nao. Day la diem
DUY NHAT HEDGED khong PASS o khau vi hien hanh, khop voi review cua MASTER
(`round_2026-09-20_beta_decomp_and_data_survey.md` muc REVIEW.4). **T170 GOC PASS ca hai khau vi
(cu va hien hanh), moi nam va toan ky.**

### 3.4 Kiem do ben mo ta: kep beta ve [−3, +3] (KHONG nam trong phan quyet)
Them **sau** khi da co ket qua chinh, ghi ro de minh bach. Muc dich: kiem xem NULL co phai chi
do duoi |beta| lon hay khong.

| | GOC | HEDGED uncapped | HEDGED clip ±3 |
|---|---|---|---|
| ICC (ngay) | +0.0516 | +0.2208 | **+0.1067** |
| ICC (72h / tuan) | +0.0512 / +0.0482 | +0.2224 / +0.2196 | +0.1097 / +0.1062 |
| beta ngay | +0.04866 | −0.01340 | −0.00341 |
| CAGR | 29.27% | 30.96% | 31.50% |
| maxDD | −11.84% | −17.32% | −15.55% |
| UW | 92 | 266 | 266 |
| hard-year PASS | 5/5 | 3/5 | 3/5 |

=> Kep beta lam nhe bot nhung **KHONG lat nguoc**: ICC van **tang gap doi**, UW van 266,
maxDD van thung nguong 15%. Ket luan NULL **ben**.

---

## 4. Doi chieu voi 4 tieu chi da KHOA o pre-reg muc 9

| tieu chi | yeu cau | do duoc | dat? |
|---|---|---|---|
| c1 ICC | `ICC_h <= 0.70 x 0.0516 = 0.0361` **VA** `< 0.15` | 0.2208 | ❌ |
| c2 beta | `|beta_h| <= 0.30 x 0.04866 = 0.01460` | 0.01340 | ✅ |
| c3 rui ro | `maxDD_h >= −14.80%` **VA** `CAGR_h > 0` | −17.32%, +30.96% | ❌ |
| c4 `n_eff` | tang >= 20% (>= 3.76) | 2.27 (−27%) | ❌ |

1/4 dat => **KHONG phai tin hieu duong**. Nhanh NULL kich hoat (muc 0) => **NULL**, khong phai
"khong ket luan duoc".

---

## 5. 🔴 MINH BACH — moi thay doi thiet ke trong luc thuc thi

Pre-reg muc 2 (Buoc 2 cua de bai) cho phep sua loi thiet ke phat hien khi code, **voi dieu kien
ghi ro da sua TRUOC hay SAU khi thay ket qua cuoi**. Co **ba** thay doi:

### (A) Vet float trong `Sum notional` → 0 — **TRUOC moi ket qua co nghia**
`cumsum` cua chuoi su kien (+notional khi mo, −notional khi dong) de lai can du **~8e-13** sau
khi moi vi the da dong => 64.5% so gio bi dem nham la "co vi the" (dung phai la 22.3%). Vi
`y = dPnL/Nopen` chia cho so ~1e-13 nen lan chay day du dau tien cho ra rac hoan toan
(hedge notional ~1e19, equity cuoi −6.2e17). **Khong co metric gia thuyet nao doc duoc tu lan do.**
Vi notional nho nhat cua mot lenh THAT la 266.38 USDT, nguong `1e-6` la khong nhap nhang.

### (B) Doi dang uoc luong beta rolling — **TRUOC moi ket qua gia thuyet cua thiet ke cuoi**
Dang pre-reg muc 3 la OLS cua `y = dPnL/Nopen` tren `x = r_b`. Dang do **ILL-POSED**: ngay chi
co 1 lenh mo 1 gio => `Nopen ~ notional/24 ~ 11 USDT`, trong khi `dPnL` cua ngay do co the la
hang tram USDT (lenh khac vua dong) => diem don bay gia tao.
**Luat quyet dinh da chot TRUOC khi chay chan doan** (`/home/ubuntu/hedge_a/diag2.py`, header
cua file ghi nguyen van): *neu `|beta_roll| > 10` tren hon 1% so ngay co hedge thi uoc luong la
ill-posed va chuyen sang dang WLS tuong duong.* Do duoc: **1.42% > 1%** => kich hoat.
Dang thay the: `dPnL(d) = a + b x (Nopen(d) x r_b(d)) + e`. `b` van **dung** la "beta tren mot
don vi notional long" ma cong thuc `hedge_notional = b x Nopen` can; chi khac o trong so
(tuong duong WLS trong so `Nopen^2`) va **khong con phep chia cho so nho**. Sau khi doi:
`|beta|>10` con **0.45%** (< 1%). **Chan doan nay chi nhin vao SUC KHOE SO HOC cua uoc luong,
khong tinh ICC/CAGR/maxDD.**

### (C) Sua lech 7 gio khi gom PnL hedge theo ngay — **SAU khi da thay mot bo ket qua day du**
🔴 Day la thay doi duy nhat xay ra **sau** khi da nhin thay metric gia thuyet. Ghi lai day du:

- **Loi:** ban dau gom PnL hedge theo **ngay lich GMT+7** (`floor(t_utc + 7h)`). Nhung kiem tra
  `sim.out` cho thay moi ngay **chi co DUNG 1 ban ghi** `Update YYYYMMDD 07:00` (gio JVM GMT+7)
  = **00:00 UTC** cung ngay. Vay `equity(D)` la anh chup tai 00:00 UTC ngay D va `r_s(D)` phu
  `UTC [D−1 00:00, D 00:00)` — **khop chinh xac** voi `r_b(D)` cua `beta_decomp_t170.py`
  (dung nhu TASK1 da kiem: `delta_h = 0.0`). Gom hedge theo ngay GMT+7 lam chuoi hedge **lech
  7 gio** so voi chuoi equity. Da sua thanh `eq_day(t) = floor_ngay(t_utc) + 1 ngay`.
- **Ket qua cua lan chay BI LECH (cong bo day du de khong giau so):** ICC 0.0516 → **0.0494**;
  beta ngay 0.04866 → **+0.04976** (hedge **khong** triet duoc beta — dung nhu ky vong khi chuoi
  bi lech); CAGR 31.24%; maxDD −14.01%; UW 201. **Phan quyet cua lan do cung la `NULL`**
  (c1 False, c2 False, c3 True, c4 False).
- **Vi sao viec sua nay khong phai dredging:** (i) no lam cho mot tieu chi **CHUYEN TU FAIL SANG
  PASS** (c2 beta) nhung **khong** cuu duoc phan quyet — NULL truoc va sau; (ii) can cu la mot
  su that kiem duoc trong `sim.out` (1 ban ghi/ngay tai 07:00 GMT+7), khong phai lua chon theo
  ket qua; (iii) khong sua thi chan hedge **khong** trung hoa duoc beta, tuc lan chay bi lech
  danh gia hedge **de dai hon** cho H1 chu khong khat khe hon.

### (D) Kiem do ben kep beta ±3 (muc 3.4) — **SAU** khi co ket qua chinh, **mo ta**, khong tham
gia phan quyet. Them vao vi `|hedge notional| max = 6.1 lan equity` la bat thuong va can chung
minh NULL khong phai artefact cua duoi.

### (E) 🔴 PHAT HIEN KHI MASTER REVIEW, SAU KHI RESULT DA COMMIT — thay doi (B) lam guard
`MIN_OBS=20` VO HIEU

Thay doi (B) o tren doi dang uoc luong beta sang `dPnL(d) = a + b*(Nopen(d)*r_b(d))`. Guard
`valid = np.isfinite(y) & np.isfinite(x)` (voi `y=dpnl`, `x=z=nopen*r_b`) trong `rolling_beta()`
**coi moi ngay co `Nopen=0` la mot quan sat hop le**, vi `z = 0*r_b = 0` la mot so huu han (qua
duoc `isfinite`). Nhung ngay khong co vi the nao mo thi `z` LUON bang 0 bat ke `r_b` la gi —
day la mot quan sat KHONG mang thong tin gi ve beta (khong co don bay long nao de uoc luong he
so tren). Hau qua: cua so lich 60 ngay chi can >=20 ngay BAT KY (ke ca ngay khong vi the) la du
`MIN_OBS=20` va tinh duoc beta, trong khi y dinh ban dau cua guard nay la doi it nhat 20 ngay
**CO vi the mo** (co thong tin thuc su). Do luong: T170 chi co vi the mo **431/1644 ngay (26.2%)**
trong ca cua so — rat nhieu cua so 60-ngay co duoi 20 ngay CO vi the that nhung van "du 20 obs"
nho dem ca ngay `Nopen=0` (z=0). Day la loi giai thich hop ly nhat cho `beta_roll` nhieu bat
thuong da ghi trong RESULT (med 0.935, p05 −1.97, p95 +2.95, |beta|>10 tren 0.45% ngay) va
hedge notional max **6.1 lan equity**.

**He qua cho phan quyet**: `ICC x4.3` (0.0516→0.2208), `maxDD` −11.84%→−17.32%, `UW` 92→266 la
**ARTEFACT cua loi nay** (beta duoc uoc luong tu it quan sat "that" hon nhieu so voi tuong dinh).
**Verdict NULL KHONG doi**: ly do that cua NULL khong phai chat luong uoc luong beta ma la
**r²=0.031** (TASK1/muc 2 o tren) — hedge BTC don gian KHONG CO gi de lay di, du beta co uoc
luong hoan hao den dau (xem bien the (F) duoi day do truc tiep dieu nay). Sua guard (doi `valid`
thanh chi dem ngay `nopen>0`) se lam beta on dinh hon nhung se KHONG doi ket luan NULL vi tran
thong tin la r², khong phai nhieu uoc luong. **KHONG sua code de tinh lai so chinh thuc trong
RESULT nay** (da cong bo; sua se la thay doi thiet ke SAU khi thay ket qua ma khong co ly do gi
khac ngoai "cho dep so") — chi ghi nhan tai day theo dung luat minh bach muc 5, va do truc tiep
bang bien the mo ta (F).

### (F) 🔵 BIEN THE MO TA THEM SAU (TASK C 2026-09-20, KHONG tham gia phan quyet muc 9):
`HEDGE_BETA_CONST` — beta CO DINH = beta OLS TOAN KY in-sample ("can tren lac quan")

De tach rieng "NULL vi r² thap" khoi "NULL vi beta_roll nhieu do (E)", them bien moi truong
`HEDGE_BETA_CONST=1` vao `hedge_overlay_a.py`: thay vi beta rolling causal 60-ngay, dung MOT beta
CO DINH cho toan bo cua so = beta OLS tren TOAN KY (khong causal, nhin ca qua khu lan tuong lai,
dung dung dang well-posed `dPnL = a + b*(Nopen*r_b)`). Day la mot **can tren lac quan**: mot nha
giao dich khong the biet truoc beta nay tai thoi diem t (khong the dung live), no chi tra loi cau
hoi "neu co MOT beta hoan hao, on dinh, biet truoc CA CHUOI, thi hedge tot nhat co the co giam
duoc ICC hay khong?".

Ket qua (`HEDGE_BETA_CONST=1 python3 research/analysis/hedge_overlay_a.py` →
`/home/ubuntu/hedge_a/hedge_overlay_a_betaconst.json`):

| | GOC | HEDGED (beta_roll causal, muc 0) | HEDGED (beta CO DINH toan ky, can tren lac quan) |
|---|---|---|---|
| beta dung de hedge | — | rolling 60d, med 0.935, p05/p95 −1.97/+2.95 | **hang so +1.368 (n=1643)** |
| ICC (ngay) | +0.0516 | +0.2208 | **+0.0496** |
| beta ngay (sau hedge) | +0.04866 | −0.01340 | −0.02100 |
| r² (sau hedge) | 0.0312 | 0.0015 | 0.0112 |
| n_eff(k_bar=3.55) | 3.13 | 2.27 | **3.15** (+0.6%) |
| maxDD | −11.84% | −17.32% | **−4.58%** |
| UW | 92 | 266 | 128 |
| CAGR | 29.27% | 30.96% | 34.08% |
| c1 ICC<=0.70x0 & <0.15 | — | False | **False** (0.0496 > 0.0361) |
| c2 &#124;beta_h&#124;<=0.30x&#124;beta_0&#124; | — | True | **False** (0.021 > 0.0146) |
| c3 maxDD>=1.25xDD0 & CAGR>0 | — | False | True |
| c4 n_eff tang >=20% | — | False | **False** (+0.6%, can >=20%) |

**Doc ket qua**: voi mot beta "hoan hao" (khong the co that trong thuc te), ICC **KHONG con tang
manh** nhu ban causal (0.0496 vs 0.2208) — xac nhan phan lon muc tang ICC 4.3 lan trong ket qua
chinh la do nhieu uoc luong ((E) o tren), KHONG phai do ban than co che phan bo pro-rata. NHUNG
ICC van **KHONG giam** xuong duoi nguong c1 (0.0496 van > 0.0361 = 0.70x0.0516) va `n_eff` gan
nhu khong doi (+0.6%, xa duoi nguong +20% can cho tin hieu duong) — ngay ca can tren lac quan
nhat (beta biet truoc ca qua khu lan tuong lai) cung KHONG dat du tieu chi thang (chi dat rieng
c3 rui ro, khong dat c1/c2/c4). **Bang chung doc lap them cho ket luan o muc 2**: tran that su cua
ICC/n_eff T170 khong nam o chat luong uoc luong beta BTC (du toi uu den dau), ma o **r²=0.031**
— BTC don gian khong giai thich du bien dong ngay cua T170 de bat ky phep hedge beta nao (nhieu
hay khong nhieu) co the cai thien duoc tuong quan trong-cohort. maxDD/UW cai thien manh o cot nay
(−4.58%/128) la hieu ung phu cua don bay/foresight (beta co dinh lon +1.368 ap dung ca cho qua
khu), KHONG phai bang chung kha thi — khong the dung lam can cu quyet dinh vi khong causal.

**Ghi chu ky thuat**: day la so MO TA THEM sau khi RESULT da cong bo, dung env var moi
`HEDGE_BETA_CONST=1`, KHONG doi hanh vi mac dinh cua script — da kiem lai: chay khong bien moi
truong cho DUNG so byte-for-byte nhu RESULT da cong bo o muc 0 (ICC 0.0516→0.2208, maxDD
−11.84%→−17.32%, UW 92→266, verdict NULL). KHONG tham gia phan quyet muc 9.

---

## 6. Gioi han (pre-reg muc 10, nhac lai + bo sung)

1. **Day la COUNTERFACTUAL, KHONG phai he chay duoc live.** Hedge PnL khong vao
   `BudgetManagerSimple.equityNow()` nen khong doi sizing; hedge notional khong an
   `marginRunning` nen khong doi `throttle`/admission. Neu chay that (Phuong an B) **tap lenh
   long se KHAC** va hieu ung hedge khong con tach duoc khoi hieu ung doi sach long.
2. Chi mot proxy thi truong duy nhat (BTC). Beta "alt-beta"/thanh khoan khong duoc bat.
3. Khop tai dung gia close 1h, khong mo hinh gap/thanh khoan trong gio, khong mo hinh impact.
4. Chi phi 0.0006/quay vong la uoc tinh can tren; khong mo hinh margin/thanh ly cua chan hedge
   (gia dinh von vo han cho chan short — trong thuc te `|hedge notional| = 6.1 x equity`
   la KHONG the thuc hien).
5. `equity` ngay la anh chup 00:00 UTC => beta rolling la beta **tan suat ngay**, khong phai gio.
6. Uoc luong beta rolling causal rat nhieu (`r2` hoi quy ngay chi 3.1%; `beta_roll` p05..p95 =
   −1.97..+2.95). Mot phan lon ket luan "overlay them nhieu chung" den tu chinh su nhieu nay —
   day **khong** phai loi thuc thi ma la **gioi han thong tin cua du lieu**: 1,644 ngay nhung
   chi **431 ngay co vi the mo**, va chi **105 ngay co lenh vao**.
7. **Dau funding**: overlay dung dau Binance THAT (short NHAN khi rate>0), **nguoc** voi bug
   da biet o `OrderTargetInfoTest.computeFundingOnClose()` cho `side == SELL`. Trong vong nay
   thanh phan funding chi **+76.2 USDT / +6,670.5 tong** (1.1%) nen dao dau no cung **khong**
   doi phan quyet. Ghi nhan de neu sau nay co lam B thi van phai sua dau, nhung no **khong
   phai** ly do NULL o day.

---

## 7. KHUYEN NGHI

### 7.1 **KHONG lam Phuong an B.** Ly do, theo thu tu suc nang:

1. **Co che da chay dung ma gia thuyet van sai.** Overlay triet duoc beta (`r2` 0.0312 → 0.0015)
   nhung ICC tang 4.3 lan. Mot ban Java "that" hon se **khong** sua duoc dieu nay — no chi them
   phan hoi sizing/admission, tuc them confound, chu khong doi ban chat "tuong quan trong ngay
   cua T170 khong phai beta BTC".
2. **Tien de cua TASK 2 khong dung cho incumbent hien tai.** ICC cua T170 la **0.0516**, tran
   **19.4 cuoc**, chu khong phai 0.247 / 4 cuoc (do la C2b). Nut that thuc su cua T170 la
   **`k_bar` = 3.55 vi the dong thoi** va **chi 105 ngay co lenh vao / 1,644 ngay**.
3. **Rui ro xau di that su**: UW 92 → 266 (nguong cung 120), maxDD −11.84% → −17.32% (nguong
   cung 15%), FAIL 2/5 nam. Ngay ca ban kep beta ±3 van FAIL 2/5 nam.
4. **Gia phai tra cua B rat cao**: 647–890 dong Java, **bat buoc** cham `equityNow()` +
   `marginRunning` (goc sizing + admission cua MOI lenh long) va sua dau funding trong ham
   **dung chung** voi long => rui ro pha `md5 efb793e2` ngay ca khi `HEDGE_MODE=OFF`
   (`docs/design/DESIGN_HEDGED_BOOK.md` muc 4). Chi phi cao, xac suat thanh cong gan nhu 0 sau ket qua nay.

### 7.2 Viec nen lam thay the (KHONG thuoc pham vi vong nay, chi la de xuat)

- **Sua `docs/notes/power_wall.md`**: phat bieu "ICC = 0.247 => tran ~4 cuoc/ngay" phai duoc gan nhan
  **"dac tinh cua C2b"**. Voi T170 so do la 0.0516 / 19.4. Ket luan "duong power duy nhat con
  song la tang so cuoc doc lap" van dung, nhung **don bay dung la tang `k_bar` va so ngay co
  lenh vao**, khong phai giam tuong quan.
- Neu muon tang `n_eff` cua T170: huong nghien cuu la **tan suat vao lenh / so vi the giu dong
  thoi** (T170 trong 76.9% so gio), khong phai hedge. Can pre-reg rieng.

---

## 8. Tai lap

```
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/hedge_overlay_a.py                 # ban chinh (phan quyet)
HEDGE_BETA_CLIP=3 python3 research/analysis/hedge_overlay_a.py   # kiem do ben mo ta
```
Phu thuoc: `/home/ubuntu/hedge_a/funding_btcusdt.csv` (dump 1 lan tu Aerospike local bang
`/home/ubuntu/hedge_a/dump_funding_btc.py`; scratch, khong commit). Ket qua ghi ra
`/home/ubuntu/hedge_a/hedge_overlay_a*.json`.

**Cong hoi quy tu kiem tra trong chinh lan chay** (moi so duoi day tai lap CHINH XAC so da
cong bo truoc do, xac nhan pipeline doc dung du lieu T170):
`equity 35,000 → 111,070`, `CAGR 29.27%`, `maxDD −11.84%`, `UW 92`, `n = 1,089`,
`beta = +0.04866`, `t_alpha = +4.372`, `%beta = 3.9%` (khop `docs/analysis/ANALYSIS_BETA_DECOMP_T170.md`),
`PASS 5/5` nam.
