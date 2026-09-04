# LABELH_RESULT — doi CHAN TROI nhan (72h -> 4h) KHONG tao khac biet do duoc o tang selector

Tuan `docs/PREREG_LABELH.md` @ **e22cbc9**. Script `research/analysis/labelh2.py`,
log `/home/ubuntu/cov/LABELH2.out`. Oracle **CPU** (GPU cam — pre-reg §7). CHI DEV.

## 0. SUA DOI 1 — ghi truoc khi doc so bien the

Ban dau (`/home/ubuntu/labelh.py`) cong tai lap **TRUOT**: `spearman = -0.898`. Hai loi cua toi:
1. **Loi dau**: so `s = -p` voi `-score` ma `score` cung da la `-p` => ra am. Tri that +0.898.
2. **Loi thiet ke (loi thuc)**: toi `dropna` tren 9 feature, trong khi `s1_rank.py` merge LEFT va
   **de NaN cho XGBoost tu xu ly**. Rieng cai do lam pool tut **1,220,490 -> 750,252** (~39% dong
   thieu it nhat 1 trong 9 feature — chu yeu 2 feature OI chi co tu 2021-12). Pool khac => cay khac
   => khong the trung ban deploy. Tuc **cong tai lap cu mau thuan voi chinh thiet ke ghep cap**.

**Sua**: tach cong kiem lam **HAI PHA** — (A) kiem harness tren **pool goc khong cat**;
(B) so 3 bien the tren pool ghep cap, moc so la `L72_g1lite` train tren **chinh pool do**.
⚠️ Sua nay thuc hien **sau khi thay cong trUot**, **truoc khi doc bat ky so nao cua 3 bien the**
(job cu `sys.exit(2)` ngay tai cong, khong in so bien the nao). Khong doi tieu chi §3/§5.
Bo sung: bo `dropna` feature => pool ghep cap = **1,220,490 dong / 8,642 tick** = **dung pool goc**
(moi dong deu co `maxFav_4h`), nen phep so nay ghep cap **hoan toan sach**.

## 1. PHA A — HARNESS TRUNG THUC

`spearman(harness, score cua pred_s1a2)` = **1.000000** tren **774,270** dong. **PASS.**
=> Harness tai lap dung `s1_rank.py`; moi so o Pha B noi ve dung cong thuc dang chay.

## 2. PHA B — ba bien the, ba tieu chi

Moi bien the chi khac NHAN; 9 feature / `rank:ndcg` / 10 fold / purge 72h / seed 42 y nguyen.
Nhan qua cung bien doi `rel5` = ngu phan vi trong tick cua `X - median_tick(X)`.

| tieu chi | `L72_g1lite` | `L72_maxfav` | `L4_maxfav` | thien vi |
|---|---|---|---|---|
| (A) rank-IC vs `g1_replay`, n=4,595 tick | +0.04178 | **+0.04291** | +0.03074 | ho 72h |
| (B) rank-IC vs `pathq_72h`, n=4,595 tick | +0.07401 | **+0.07958** | +0.07255 | ho 72h |
| (C) rank-IC vs **ROI THAT**, n=**84** tick | **-0.01885** | +0.00716 | -0.02301 | tap do S1 chon |

Hieu vs `L72_g1lite`, CI da nhan `f=1.21`:

| tieu chi | bien the | d | CI (72h) | loai tru 0? | `\|d\|>k*f*sd`? |
|---|---|---|---|---|---|
| A | `L72_maxfav` | +0.00113 | [-0.00512, +0.00739] | khong | khong |
| A | `L4_maxfav` | **-0.01104** | [-0.02708, +0.00500] | khong | CO (72h,24h) / khong (168h) |
| B | `L72_maxfav` | +0.00557 | [-0.00230, +0.01345] | khong | CO (ca 3) |
| B | `L4_maxfav` | -0.00146 | [-0.01979, +0.01688] | khong | khong |
| C | `L72_maxfav` | +0.02601 | [-0.04476, +0.09677] | khong | khong |
| C | `L4_maxfav` | -0.00416 | [-0.12865, +0.12032] | khong | khong |

## 3. VERDICT theo §5 — KHONG PHAN BIET DUOC, ca hai bien the

§5 doi **CA HAI**: CI loai tru 0 o **ca 3** do dai khoi **VA** `|d| > k*f*sd`.
**Khong bien the nao dat** — CI chua 0 o **moi** tieu chi, **moi** do dai khoi.

=> Theo dung §5: *"`L4_maxfav` khong phan biet duoc => **chan troi khong phai truc dang theo duoi**
o tang selector, va do la ket qua co gia tri (null co thong tin), khong phai that bai."*

Hai cho ngUong va CI **khong dong thuan** (A/`L4_maxfav` va B/`L72_maxfav`): ngUong `k*f*sd` vuot
nhung CI van chua 0. §5 doi ca hai nen ket luan van la khong phan biet duoc. Ghi lai de lan sau
thiet ke tieu chi khong bi mau thuan noi tai nhu vay.

## 4. BA DIEU PHAI GHI KEM

1. **Huong nhat quan nhung khong du**: `L4_maxfav` co diem uoc luong **thap hon** o **ca 3** tieu chi
   (-0.01104 / -0.00146 / -0.00416). Nhat quan ve dau, khong dat nguong phan biet.
2. **Tieu chi (C) vo dung ve phan giai**: chi **84 tick** (khong phai ~115 nhu du kien), CI **+-0.12**.
   Va tren chinh tieu chi **thien vi `L72_g1lite` nhat**, `L72_g1lite` lai ra **AM** (-0.01885) va
   **thap nhat trong ba**. Dang ghi nhan, **khong dung duoc** de ket luan gi voi n=84.
3. 🔴 **JOB NAY KHONG KIEM GIA THUYET GOC.** Gia thuyet o `CEIL_RESULT §3` la: nhan **72h QUA NGAN**
   so voi time-stop that **168h**, nen bo mat phia lo o ngay thu 7. Job nay so 72h voi **4h** —
   tuc thu **NGAN HON**, khong phai dai hon. => No **bac** duoc "ngan hon thi tot hon", nhung
   **KHONG kiem** duoc "dai hon (168h) thi tot hon". Cau hoi goc **van nguyen**, va file nhan
   `.pb` chi co toi 72h nen phai sinh lai tu `CLOSES_1H.bin` voi `NH=168` moi kiem duoc.

## 5. Cai job nay KHONG lam
Khong sinh bins, khong chay java (§6 chi ap cho bien the THANG — khong co bien the nao thang).
Khong cham VALIDATION/HOLDOUT. Khong ghi de artifact nao. GPU khong dung.
