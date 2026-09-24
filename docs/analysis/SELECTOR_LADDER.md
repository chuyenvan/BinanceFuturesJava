# SELECTOR_LADDER — bang sim THAT tu dia: doi selector thi equity doi bao nhieu

Liet ke tu **125 run** trong `/home/ubuntu/java/devrun/*/logs/sim.out` (doc truc tiep dong
`done:` -> `b:<equity>`), khong lay tu docs. DEV 2022-01..2024-06, von goc 35,000.
Sinh boi `research/analysis/dump_sim_runs.sh`.

## 0. VI SAO CO FILE NAY

`docs/result/LABELH_RESULT.md` so 3 nhan **chi o tang rank-IC**, khong chay sim => **khong so duoc**
voi chuoi baseline lich su, vi luong that tao baseline la
**train selector -> pred -> bins -> sim Java -> equity**. File nay bu dung cho do trong: lay
**ket qua sim** cua moi doi selector da tung chay, va xep thang.

## 1. THANG SELECTOR o exit "G1" (arm 5%, scale 1.0) — chi khac BINS

| bins / selector | equity | lenh | run |
|---|---|---|---|
| **V2** — 40 feature, XGBClassifier, nhan `maxFav_72h>=6%` | **32,956** | 2,315 | `v2_g1` |
| **V3** — 9 feature, XGBClassifier, nhan vol-norm | **38,471** | 875 | `v3_g1` |
| **`vol_7d` tho** (doi chung tam thuong, khong model) | **41,876** | 922 | `map_vol7d_g1` |
| `b30` veto bucket | 41,769 | 2,604 | `b30_g1` |
| `b40` veto bucket | 42,432 | 2,504 | `b40_g1` |
| nhan `fav72` | 44,788 | 2,841 | `fav72_g1` |
| nhan `cs72` | 46,645 | 1,312 | `cs72_g1` |
| **G015** — 45 feature (40 Tool1 + 5 OI), classifier, nhan 4h | **48,352** | 1,736 | `G1_giveback5` |
| **S1a** — 9 feature, XGBRanker | **49,581** | 1,228 | `map_s1a_g1` |
| **S1a2** — 9 feature, XGBRanker (**BAN DANG DUNG**) | **50,891** | 1,117 | `map_s1a2_g1` |

**S1a2 − G015 = +2,539 (+5.3%)** o **cung thang exit**, chi khac bins.
Va **S1a2 − `vol_7d` tho = +9,015 (+21.5%)** — day la cho doi chung tam thuong THUA nang o sim,
nguoc voi ket qua o tang rank-IC (`vol_7d` thang S1 tren `g1lite`/`maxFav`).

## 2. THANG SELECTOR o exit "C2" (arm 7%, scale 1.5, TIER_FLAT, SELECTOR_ONLY_ENTRY)

| selector | equity | lenh | run |
|---|---|---|---|
| **G015x26** | **51,903** | 1,583 | `C2_g015` |
| **G015_v2** (ban tai lap 2026-09-04) | **45,439** | 2,544 | `C3` |
| S1 pool day (`s1a4`) | 55,357 | 950 | `C2_s1a4` |
| S1 + `p_g015` lam feature 10 (`s1b4`) | 56,588 | 974 | `C2_s1b4` |
| S1 nhan graded (`s1b2`) | 56,704 | 1,049 | `C2_s1b2` |
| **S1a2** | **59,471** | 1,025 | `C2a` |
| **S1a2 + 3 key exit** (= **C2b, UNG VIEN HIEN TAI**) | **60,390** | **970** | `C2b` |

**S1a2 − G015x26 = +7,568 (+14.6%)** o cung thang exit.

## 3. ⚠️ CI DA GIET PHAN LON BANG NAY — doc kem `ci_reality`

`CI_REAUDIT` do lai bang block-bootstrap ghep cap: `sd(hieu CAGR)` giua hai selector = **4.45pp**.
- `C2b` vs `C2_g015`: `d = +7.33pp`, **CI [-1.72, +15.61]** => **KHONG PHAN BIET DUOC**
- `map_s1a2_g1` vs `G1_giveback5` ("16.21 vs 13.85"): `d = +2.36pp`, **CI [-3.33, +7.71]** =>
  **KHONG PHAN BIET DUOC**

=> **Ca hai phep so selector o muc 1 va 2 deu KHONG dat nguong phan biet.** Thang o day la
**thang diem uoc luong**, khong phai thang co y nghia thong ke.

**Nhung co mot thu bang nay noi ma CI khong xoa duoc:** thang **don dieu va nhat quan qua HAI thang
exit khac nhau** (G1 va C2), va **thu tu giong nhau** (V2 < V3 < vol_7d < ... < G015 < S1a < S1a2).
Do la bang chung **co huong**, khong phai bang chung **do duoc**. Ghi ro nhu vay, khong nang cap.

## 4. HAI RUN TRA LOI TRUC TIEP CAU HOI DA HOI TRUOC DAY

| run | equity | lenh | y nghia |
|---|---|---|---|
| **`A4_hardsl`** | **17,598** | 3,112 | **BAT stop-loss cung** => equity tu 35,000 xuong **17,598 (mat 50%)**. Day la ly do co hoc vi sao C2b **khong co SL truoc arm** — khong phai bo sot, ma da thu va no pha he |
| **`v3_g1_nomom`** | **10,305** | **13,960** | **TAT gate** (`SIM_MIN_MOMENTUM_15M=0`) => 13,960 lenh, equity **10,305**. Gate la thu **chiu luc**, khong phai tham so trang tri |

## 5. NHUNG RUN GAN 35,000 — khong phai loi

`R1_base` 35,255 · `R2_trail` 35,222 · `S3_ts168` 35,169 · `S1_sl30` 35,101 · `S2_sl60` 35,139 ·
`S4_ts720` 35,154 · `R3_rollgate` 35,332 — nhom tham do dau (2026-09-02 06:00-10:30), gan nhu
khong giao dich duoc gi. Chung la moc "0" cua ca chuoi, khong phai baseline.

## 6. Cai file nay KHONG lam

Khong chay run moi. Khong ket luan selector nao "tot hon" — muc 3 da noi ro CI khong cho phep.
Chi tap hop **ket qua sim da co** de doi chieu truc tiep, dung cho trong ma `LABELH_RESULT` de lai.
