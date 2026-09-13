# RESULT_K_DENSITY — gian top-K (SELECTOR_RANK_TOPK 8->12->16) tren gate T170 / DEV 2021

Pre-reg: `docs/PREREG_K_DENSITY.md` (commit 1579f5a, chot TRUOC khi chay sim).
Nen: DEV mo rong 18 fold (2021Q3..2025Q4), dataset `wfo_ds_x1_2021`, bins `predwf_map_s1a2_x1_2021`,
baseline `X1_GS_T170_2021` (K=8, md5 efb793e2, n=1089). Jar HEAD 422b23e (KHONG rebuild). SIM_END_DATE=20251231,
holdout 2026 nguyen ven. KHONG cham 242, KHONG tune, KHONG push, KHONG doi code Java. Chi doi SELECTOR_RANK_TOPK.

## 0. Phan quyet (so truoc)
- **REPRODUCTION K=8: PASS** — re-run baseline -> printDone md5 **efb793e2** trung byte-for-byte (n=1089, eq 111070).
- **DENSITY (khoi luong): TANG ro va don dieu.** n 1089 -> 1409 (+29.4%) -> 1730 (+58.9%); lenh/ngay 0.66 -> 0.86 -> 1.05;
  gap trung binh giua 2 lenh 1.46 -> 1.13 -> 0.92 ngay; p95 gap 7.44 -> 3.80 -> 1.69 ngay. Gian K lam DAY hon TRONG cac dot.
- **DENSITY (do DEU): KHONG cai thien.** CV lenh/tuan ~2.61 CA BA (2.614/2.600/2.616); coverage tuan co lenh **33.8% Y HET**
  ca ba; khoang trong DAI NHAT **129.24 ngay Y HET** ca ba. => burstiness la thuoc tinh cua GATE T170, KHONG phai cua K.
  Gian K chi them lenh trong tuan gate DA MO, KHONG lap duoc tuan gate DONG. Muc tieu "entry DEU hon" => gian K KHONG dat.
- **CHAT LUONG: xau nhe don dieu.** TSloss% 9.73 -> 11.21 -> 11.79; meanP 5.244 -> 4.890 -> 4.824. K12: 2 rate chat luong
  ngoai CI (TSloss% +1.48, meanP -0.35) DEU HUONG XAU => KHONG phai win (luat can >=2 rate ngoai CI huong TOT). K16: 1 rate
  ngoai CI (TSloss% +2.06 xau).
- **RUI RO: xau don dieu.** UW 92 -> 119 -> 164; maxDD -11.84 -> -13.05 -> -13.15. **K16 FAIL rang buoc cung (UW=164 > 120)** —
  pha dung tieu chi rui ro ma T170 duoc chon vi giu. **K12 PASS ca 5 nam** (UW 119 SAT tran 120, maxDD -13.05).
- Multiplicity k=2 variant: sqrt(2 ln 2)=1.177 < 1.21 (CI_INFLATE built-in c3_rates) => 1.21 da bao mult, khong noi rong them.

## 1. Cong REPRODUCTION (PASS)
- Re-run K=8 profile `x1_gs_t170.properties` tren `wfo_ds_x1_2021` (jar 422b23e) -> devrun X1_GS_T170_KREPRO:
  printDone md5 **efb793e2468ca3a7318da0f0ad23d4fc** = baseline goc byte-for-byte, n=1089, b:111070, PROFILE_HASH 0d0fa22158b1d8c0.
- Cong CHI-DOI-K (b): diff clone vs goc = DUNG 1 dong. x1_gs_t170_k12 PROFILE_HASH 97a0c944a470825f (SELECTOR_RANK_TOPK=12);
  x1_gs_t170_k16 PROFILE_HASH e979ffa728d58b28 (=16). 20 key moi profile. Gate T170 + S1 9-feat + net015 + DCA/exit/sizing GIU NGUYEN.

## 2. Bang chinh (equity/CAGR KHONG phai tieu chi)
| tag | K | n | win% | TSloss% | meanP | mP\|SL | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X1_GS_T170_2021 (baseline) | 8 | 1089 | 88.25 | 9.73 | 5.244 | -16.99 | 1851 | -11.84 | 92 | 111070 | 29.27 |
| X1_GS_K12_2021 | 12 | 1409 | 87.37 | 11.21 | 4.890 | -16.23 | 1656 | -13.05 | 119 | 113340 | 29.85 |
| X1_GS_K16_2021 | 16 | 1730 | 87.05 | 11.79 | 4.824 | -16.63 | 1453 | -13.15 | 164 | 116824 | 30.73 |

Doc: equity/CAGR TANG don dieu (them lenh => tong loi nhuan gop tang) NHUNG meanP/lenh GIAM va TSloss% TANG
=> lenh bien them (coin rank 9-16) chat luong THAP hon, keo chat luong trung binh xuong; UW/maxDD xau di (nhieu vi the
dong thoi hon). Equity KHONG phai tieu chi (luat cung #3 AGENT_RUNBOOK).

## 3. CI khoi-72h x1.21 (variant - baseline). Rate chat luong = win%/TSloss%/meanP/mP|SL; n & mMargin = bien kiem soat
### K12 vs baseline (n_A=1409 n_B=1089) — 2 rate chat luong ngoai CI, DEU XAU
| rate | hieu | lo | hi | ngoaiCI |
|---|---|---|---|---|
| win% | -0.879 | -2.304 | +0.303 | - |
| TSloss% | +1.480 | +0.180 | +2.959 | **YES (xau)** |
| mP\|SL | +0.766 | -0.380 | +1.969 | - |
| meanP | -0.354 | -0.716 | -0.064 | **YES (xau)** |
| n (control) | +320 | +215 | +441 | YES |
| mMargin (control) | -195 | -239 | -151 | YES |
=> 0 rate chat luong ngoai CI theo huong TOT (can >=2 de THANG). 2 rate ngoai CI DEU XAU => chat luong xau nhe.

### K16 vs baseline (n_A=1730 n_B=1089) — 1 rate chat luong ngoai CI, XAU
| rate | hieu | lo | hi | ngoaiCI |
|---|---|---|---|---|
| win% | -1.194 | -2.774 | +0.209 | - |
| TSloss% | +2.058 | +0.391 | +3.972 | **YES (xau)** |
| mP\|SL | +0.367 | -1.846 | +2.615 | - |
| meanP | -0.420 | -1.032 | +0.131 | - (xau, trong CI) |
| n (control) | +641 | +427 | +897 | YES |
| mMargin (control) | -399 | -456 | -338 | YES |
=> 1 rate chat luong ngoai CI (TSloss%, xau). Khong win.

## 4. Rang buoc cung tung nam (maxDD<=15, UW<=120, nam>=0, quy>=-5) — x1_rates
| tag | nam>=0 het | qmin | maxDD% | UW | verdict |
|---|---|---|---|---|---|
| baseline K8 | PASS (2021..2025) | -0.9 | -11.84 | 92 | **PASS 5 nam** |
| K12 | PASS | -1.9 | -13.05 | 119 | **PASS 5 nam** (UW 119 SAT tran 120) |
| K16 | PASS | -2.7 | -13.15 | 164 | **FAIL** (UW=164 > 120) |
Relative so voi K8: K12 maxDD +1.21pp, UW +27 ngay; K16 maxDD +1.31pp, UW +72 ngay (vuot tran). Rui ro xau don dieu theo K.

## 5. MAT DO (do tu printDone.csv cot `start`; span DEV 2021-07-01..2025-12-31 = 1645 ngay / 234 tuan)
| tag | K | n | lenh/ngay | lenh/tuan tb | std/tuan | CV tuan | tuan-co-lenh% | gap max (ngay) | gap p95 | gap tb |
|---|---|---|---|---|---|---|---|---|---|---|
| K8 | 8 | 1089 | 0.662 | 4.65 | 12.16 | 2.614 | 33.8% | 129.24 | 7.44 | 1.460 |
| K12 | 12 | 1409 | 0.857 | 6.02 | 15.66 | 2.600 | 33.8% | 129.24 | 3.80 | 1.128 |
| K16 | 16 | 1730 | 1.052 | 7.39 | 19.34 | 2.616 | 33.8% | 129.24 | 1.69 | 0.919 |

Doc HAI mat cua "mat do":
- **Khoi luong / do day TRONG dot**: gian K cai thien manh — n +29%/+59%, lenh/ngay +29%/+59%, gap tb va gap p95 GIAM manh
  (p95 7.44 -> 3.80 -> 1.69). Neu user muon "nhieu lenh hon, it khoang trong ngan hon" => K12/K16 dat.
- **Do DEU theo thoi gian (rai deu, lap khoang trong DAI)**: gian K KHONG cai thien — CV ~2.61 KHONG doi, coverage tuan
  33.8% KHONG doi, gap DAI NHAT 129.24 ngay KHONG doi ca ba. Ly do: top-K chi them coin trong tick GATE DA MO; tuan nao
  gate T170 dong (khong dot momentum) thi K bao nhieu cung 0 lenh. Muc tieu "entry DEU hon / lap khoang trong dai" =>
  don bay dung la GATE (vd scale < 1.70) hoac co che entry khac, KHONG phai K. (Ngoai pham vi pre-reg nay.)

## 6. Phan quyet + trade-off density-vs-quality
- **Khong K nao la "WIN chat luong"** (khong K nao co >=2 rate chat luong ngoai CI huong TOT). Gian K danh doi
  chat luong/rui ro LAY khoi luong.
- **K16: LOAI.** Pha rang buoc cung (UW=164 > 120) — dung tieu chi rui ro T170 duoc chon vi giu. Density khoi luong cao nhat
  nhung KHONG dang, va van khong deu hon.
- **K12: kha thi CO DIEU KIEN neu user uu tien khoi luong.** +29% lenh, gap p95 giam ~1/2, VAN PASS ca 5 nam rang buoc cung
  (UW 119 sat tran). Gia phai tra: chat luong xau nhe co y nghia thong ke (TSloss% +1.48, meanP -0.35 deu ngoai CI), rui ro
  xau nhe (maxDD -13.05, UW 119 sat tran 120 => bien an toan mong, de vuot o cua so khac).
- **Neu muc tieu THAT su la "entry DEU hon" (rai deu, bot dot bursty): gian K KHONG giai quyet.** CV/coverage/gap-max deu
  KHONG doi. Van de o GATE, khong o K. Khuyen nghi: neu can DEU hon, thu don bay gate (ngoai pham vi), khong tang K.
- **Khuyen nghi cho master/user:** giu K=8 lam mac dinh (chat luong + rui ro tot nhat, la baseline THANG). Chi can nhac K=12
  neu user chap nhan danh doi chat luong nhe LAY +29% khoi luong VA hieu ro no khong lam entry deu hon. TUYET DOI khong K16.
  KHONG tune K khac (pre-reg chot 8/12/16).

## 7. Ghi chu van hanh + tai lap
- Artifact: devrun X1_GS_T170_KREPRO (repro efb793e2), X1_GS_K12_2021 (md5 9dbae8af), X1_GS_K16_2021 (md5 b905c758).
  Profile: profiles/x1_gs_t170_k12.properties, profiles/x1_gs_t170_k16.properties (moi file chi doi 1 dong SELECTOR_RANK_TOPK).
- Dataset dung CHUNG wfo_ds_x1_2021 (K ap o SIM-time, khong rebuild dataset).
- Cham chat luong: python3 research/analysis/x1_rates.py X1_GS_T170_2021 X1_GS_K12_2021 (va ..._K16_2021).
- Cham mat do: python3 /home/ubuntu/java/fsrun/k_density.py X1_GS_T170_2021 X1_GS_K12_2021 X1_GS_K16_2021.
- KHONG cham 242 / holdout 2026, KHONG deploy, KHONG git push, KHONG doi code Java / rebuild jar.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
