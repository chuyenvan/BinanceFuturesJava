# PREREG_S1CUT — tien dang ky: cat bo feature S1 xuong toi thieu KHONG can metrics/OI

Chot luc: 2026-09-04, **TRUOC khi train bat ky bien the nao**. Commit file nay phai co truoc moi
commit ket qua (`docs/S1CUT_RESULT.md`). Neu thu tu commit nguoc lai => ket qua VOID.

Pham vi: **CHI DEV** (OOS 2022-01..2024-06). KHONG cham VALIDATION/HOLDOUT. Khong rebuild OI.
Moi output ra duong dan MOI, khong ghi de `predwf_map_s1a2/`, `ledger/pred_s1a2.parquet`,
`featv2/feat_v2.parquet`.

## 0. MUC TIEU (khong phai tim so dep)

Theo NBETS/`power_wall`: chenh equity KHONG do duoc => cat feature **KHONG** nham "tot hon". Nham:
(1) don gian hoa; (2) **bo phu thuoc feature OI/metrics** (`ls_global`, `rk_oi_delta24h` — hai feature
S1 duy nhat can file OI, ma metrics chi co tu 2021-12) de mo duong lui DEV ve 2020-01 (VIEC 3).
=> **Tieu chi THANG cua moi bo cat = TUONG DUONG (khong kem) o tang xep hang + dat rang buoc cung
maxDD + KHONG can OI.** Bo cat can OI ma khong tot hon = vo gia tri cho muc tieu nay.

Nen tang do (feataudit `SELECTOR_FEATURES.md`, da tai lap): trong tick ranker chi thay 7 tin hieu
(`dd_7d ≡ rk_dd_7d`, `ret_3d ≡ rk_ret_3d`, tuong quan hang trong tick = 1.000); 2 khoi dong gop that
la drawdown-7d va `ret_14d`; ca 2 feature OI khong phan biet duoc khoi 0; `ret_3d` **co hai** tren
`g1_replay`.

## 1. UNG VIEN — chot cung (M = 5 bo cat, deu KHONG-OI)

Tat ca la tap con cua 9 feature `KEEP` san co trong `featv2/feat_v2.parquet` (khong build feature moi).

| ma | feature | so | can OI? |
|---|---|---|---|
| **ref full9** | vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h | 9 | co (2 OI) |
| C1 no_oi7 | full9 tru {ls_global, rk_oi_delta24h} | 7 | **khong** |
| C2 core5 | vol_7d, dd_7d, rk_dd_7d, ret_3d, ret_14d | 5 | **khong** |
| C3 core4 | vol_7d, rk_dd_7d, ret_3d, ret_14d | 4 | **khong** |
| C4 core3 | vol_7d, rk_dd_7d, ret_14d | 3 | **khong** |
| C5 noret3_5 | vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_14d | 5 | **khong** |
| **CTRL worse2** (doi chung cong suat, KHONG phai ung vien chon) | vol_7d, hrs_since_high_7d | 2 | khong |

M = 5 (dem cac ung vien co the chon; CTRL khong tinh vao M — no la phep kiem cong suat).

## 2. THUOC DO + FOLD — chot cung

- Train lai S1 moi bo bang **XGBRanker CPU** (`objective=rank:ndcg`, tham so y het `s1_rank.py`:
  n_estimators=300, max_depth=4, lr=0.05, subsample/colsample=0.8, min_child_weight=50, n_jobs=4,
  tree_method=hist, random_state=42, lambdarank topk-8). **GPU cam** (tao ung vien vuot nguong gia —
  power_wall quy tac 1). Nhan `rel5` = ngu phan vi TRONG TICK cua `g1lite - median_tick`, group = tick.
- 10 fold WFO cutoff `20220101..20240401`, OOS 3 thang, **purge 72h**, `assert tr.ts.max()<cutoff`.
- **Tai lap full9 khop `pred_s1a2` TRUOC** khi ket luan gi: `spearman(pred_full9, -score_deploy)`
  phai = 1.0 (da chung minh o VIEC 1 = byte-identical; kiem lai trong run nay).
- Thuoc do chinh: **rank-IC per-tick vs `g1_replay`** (mo phong dung luat exit G1 — gan tien that
  hon g1lite). Phu: rank-IC vs `g1lite`. Dinh nghia rank-IC = trung binh theo tick cua
  spearman(pred, outcome) tren tick >= 10 dong (y `PREREG_CI §3.2`).
- CI: **block-bootstrap khoi 72h** (chinh) + 24h/168h (do ben), **ghep cap** (cung khoi cho ca hai
  nhanh), 2000 rep, seed **20260903**, percentile 2.5/97.5 CUA HIEU. `n_eff` = so khoi 72h.

## 3. TIEU CHI "TUONG DUONG" — chot truoc (day la kiem TUONG DUONG, khong phai kiem hon)

Cho moi ung vien C, `d(C) = rankIC(C) - rankIC(full9)` tren `g1_replay`, ghep cap.
- **Bien tuong duong** `delta_M = sqrt(2 ln M) * sd_boot(d)` = `sqrt(2 ln 5) = 1.7941 * sd_boot(d)`
  (hieu chinh so sanh boi cho M ung vien).
- **TUONG DUONG (khong kem)** khi: CI95 cua `d` **loai tru** `-delta_M` (chan duoi CI > -delta_M) o
  **ca 3** do dai khoi, VA diem `|d| < delta_M`. Tuc "khong kem hon nguong nhieu da hieu chinh".
- **KEM PHAN BIET DUOC** khi CI95 nam hoan toan duoi 0 o ca 3 khoi (chan tren < 0). => loai.
- Chon **bo NHO NHAT** dat "tuong duong", **uu tien KHONG-OI** (moi ung vien deu khong-OI nen tieu
  chi con lai la nho nhat). Neu nhieu bo cung nho nhat: chon bo co diem `d` cao hon.
- **Doi chung nhiem (bat buoc PASS):** CTRL `worse2` phai ra `d` **AM va phan biet duoc**
  (chan tren CI < 0) tren `g1_replay` => xac nhan phep do CO cong suat phat hien mat mat. Neu CTRL
  khong phan biet duoc => phep do vo hieu, DUNG.

## 4. RANG BUOC CUNG + JAVA (buoc xac nhan end-to-end cua bo duoc chon)

- Sinh bins tu bo duoc chon: `s1_rank`(bo cat) -> pred (duong dan moi `/home/ubuntu/feataudit/`
  hoac `ledger/pred_s1cut_*.parquet`) -> `build_map` -> bins `/home/ubuntu/predwf_s1cut_<ma>/`
  (KHONG de `predwf_map_s1a2`).
- Chay **1 run java DEV** (kiem `pgrep -a java` rong truoc; xong khong zombie; `df -h /` truoc, duoi
  6G thi DUNG + don `wfo_ds_*`). Cham `qret.py`.
- **Rang buoc cung: maxDD >= -15.12%.** Truot => bo do KHONG thay duoc, bao thang (khong vi CAGR).
- So CAGR voi C2b (60390): khac thi ghi **"nam trong nhieu tang equity (NBETS), KHONG phai hon/kem"**.
  Cai thien rankIC KHONG doc thanh cai thien equity.

## 5. THU TU + GIOI HAN

1. Commit file nay. 2. Train full9 + 5 ung vien + CTRL, CPU, ghi per-tick ic. 3. Bootstrap, chon bo
toi thieu tuong duong khong-OI. 4. Sinh bins bo do (duong moi) + 1 run java DEV + qret + maxDD.
5. `docs/S1CUT_RESULT.md` + commit.

Giói hạn cứng: chi DEV; khong ghi de artifact deploy; khong rebuild OI; khong cham live/shadow;
GPU cam cho rankIC; khong cham `/home/ubuntu/{gs,tick,nbets,g015,fs}/`; Java SLF4J, Python logging;
git chi add file cua minh, PREREG truoc, KHONG push.

## 6. GIA DINH DIEU PHOI CO THE SAI — ghi truoc

- Buoc 2 (G015 cat no-OI) can `pool_dev.parquet` nam trong `/home/ubuntu/g015/` = **vung cam cham**.
  => khong the do lai G015 no-OI tren CPU trong VIEC 2 ma khong pha gioi han. Da co ket qua GPU
  (`G015CUT_RESULT`: no_oi tuong duong tren rho, d=+0.00035). Se bao nguyen trang, khong ep.
- Neu bo cat nho nhat van cho `d` **duong** tren g1_replay: KHONG doc thanh "tot hon" — chi la
  "tuong duong, don gian hon, bo duoc OI".
