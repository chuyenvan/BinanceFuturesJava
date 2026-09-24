# AUDIT_READJUDICATE_CI_RESCORE — cham lai vong chon T170 bang he so CI dung

2026-09-15. **KHONG chay sim moi, KHONG sua `c3_rates.py`, KHONG refit gi.** Chi doc lai
`printDone.csv` da co, chay lai DUNG may bootstrap block-72h cua `x1_rates.ci_pair_df`
(BLOCK_H=72, NREP=2000, SEED=20260905) va **chi doi he so noi rong CI o buoc cuoi**.
Script: `research/analysis/readjud_rescore.py`. Vong goc: `docs/result/RESULT_DEV2021_READJUDICATE.md`
(commit d94f64f), pre-reg `docs/prereg/PREREG_DEV2021_READJUDICATE.md` (commit e57fd3d).

## 0. Vi sao audit nay ton tai
Trong PHU LUC A cua `RESULT_DCA_MORELEGS_V4.md` (commit 8251e84) da xac dinh: `CI_INFLATE = 1.21` la
**hang so CUNG** trong `c3_rates.py`, khong co phep tinh `sqrt(2 ln k)` nao trong code, va
`1.21 = sqrt(2 ln k)` khi `k = 2.079`. Cau hoi tiep theo, hoan toan chinh dang: **vong chon T170 lam
incumbent co con dung khi dung he so dung khong?**

## 1. Cong tai lap — PASS (bat buoc truoc khi tin bat ky con so nao duoi day)
Ba run cu con nguyen, md5 khop TUYET DOI voi doc goc muc 7:
| tag | vai tro | n dong | md5 (8) | doc goc ghi |
|---|---|---|---|---|
| `X1_C3_FULL_2021` | baseline (= T100, scale 1.00) | 2560 | `dc16e4da` | `dc16e4da` OK |
| `X1_GS_T170_2021` | variant T170 (1.70) | 1090 | `efb793e2` | `efb793e2` OK |
| `X1_GS_T130_2021` | variant T130 (1.30) | 1581 | `68510567` | `68510567` OK |

Chay lai bootstrap va in CI o he so **1.21** => **trung khop doc goc den 3 chu so thap phan** tren ca
4 rate: `win +3.916 [-0.059,+8.074]`, `tsloss -5.624 [-9.622,-1.429]`, `mp|SL +2.197 [-2.181,+6.715]`,
`meanP +2.071 [+0.067,+3.983]`. => may cham diem duoc tai lap chinh xac; phan re-score tin cay duoc.

## 2. k DUNG cua vong goc = **2** (da khai bao TRUOC khi chay, khong phai suy dien sau)
`PREREG_DEV2021_READJUDICATE.md` (commit e57fd3d, chot TRUOC khi chay sim):
- dong 27: *"=> Chay **2 variant: T170, T130**. Multiplicity **k = so variant chay = 2**."*
- dong 59-60: *"Multiplicity k=2. Ghi ca hai cach doc: (a) x1_rates.py CI x1.21 (block-72h),
  (b) ghi chu nguong nghiem hon sqrt(2 ln 2)=1.177."*

**Xac nhan k=2 la dung, va tai sao KHONG phai 3 hay 4:**
- **T100 KHONG phai ung vien** — no la **baseline/control**. Moi CI deu la hieu `(variant - baseline)`;
  khong he co mot phep kiem dinh nao "cho T100". T100 la moc null, khong phai gia thuyet duoc kiem.
- **GD92 KHONG co so lieu** — BLOCKED, khong bao gio chay (co che rolling da bi xoa o commit f1c43a3).
  Multiplicity dem cac phep KIEM DINH DA THUC HIEN; mot phep kiem chua bao gio chay khong lam phong
  family-wise error rate cua nhung phep da chay. Dem no vao la **over-correction**.
=> **k = 2** (T170, T130). Con so nay do vong goc TU KHAI BAO truoc khi thay ket qua — dung ky luat.

## 3. KET QUA RE-SCORE — T170 vs baseline (T100). Hieu = T170 - baseline
Rate CHAT LUONG theo luat du an = {win%, TSloss%, meanP}. Huong TOT cho T170: win% duong,
TSloss% am, meanP duong.

| he so noi rong CI | so rate TOT ngoai CI | ket luan | chi tiet |
|---|---|---|---|
| 1.000 (khong multiplicity) | **3** | THANG | win +3.916[+0.647,+7.368]; tsloss -5.624[-8.911,-2.140]; meanP +2.071[+0.407,+3.643] |
| **1.177 = sqrt(2 ln 2), k=2 — HE SO DUNG** | **3** | **THANG** | win +3.916[**+0.051**,+7.965]; tsloss -5.624[-9.512,-1.540]; meanP +2.071[+0.119,+3.930] |
| 1.210 = hang so da dung (~k=2.08) | **2** | THANG | tsloss -5.624[-9.622,-1.429]; meanP +2.071[+0.067,+3.983] |
| 1.482 = sqrt(2 ln 3), k=3 | 1 | duoi nguong | tsloss -5.624[-10.544,-0.507] |
| 1.665 = sqrt(2 ln 4), k=4 | 0 | duoi nguong | — |
| 2.039 = sqrt(2 ln 8), k=8 | 0 | duoi nguong | — |

**T130 vs baseline** (de day du): 1.000 -> 2 rate TOT; **1.177 (k=2) -> 1 rate**; 1.21 -> 1 rate;
1.482 tro len -> 0. => T130 **NULL o he so dung** y het ket luan goc (va T130 con FAIL rang buoc cung).

## 4. PHAN QUYET CUA AUDIT — **T170 DUNG VUNG, va con vung HON truoc**
**He so DUNG cho vong do (k=2) la 1.177, tuc HEP HON 1.21 da dung.** Nghia la vong goc da tu cham diem
**NGHIEM HON muc can thiet**, chu khong phai long hon. Cham lai o 1.177:
- T170 co **3** rate chat luong ngoai CI (win%, TSloss%, meanP), **tang** so voi 2 rate da bao cao.
- Nguong thang la >=2 => **T170 THANG, con thuyet phuc hon ban goc.**
- T130 van NULL. Khong ket luan nao cua vong goc bi dao nguoc.

**=> Loi `CI_INFLATE` phat hien o V4 KHONG lam lung lay viec chon T170.** No chi anh huong theo huong
"qua chat" o vong k=2 nay, va theo huong "qua long" o cac vong k>=3 (V1-V4) — nhung o V1-V4 moi config
deu da NULL voi bien do rong, nen cung khong doi verdict nao (da kiem o PHU LUC A muc A3.3/A3.4).

## 5. HAI CAVEAT PHAI GHI RO (khong tu ket luan, de master/user quyet)
1. **Neu ai do lap luan k=3 hoac k=4** (dem ca T100 nhu mot ung vien, hoac dem ca GD92 du khong co so),
   T170 tut xuong **1 rate** (k=3) hoac **0 rate** (k=4) => duoi nguong thang. Toi cho rang k=2 moi dung
   (ly do o muc 2) va do la con so DA PRE-REG, nhung ghi ro day de master thay do nhay cua ket luan.
   **Luu y quan trong o kich ban do**: viec T170 khong dat nguong KHONG tu dong dua T100 tro lai, vi
   **T100 (baseline) TU VI PHAM rang buoc cung o 2/5 nam** (2024 UW=121, 2025 UW=227 — doc goc muc 5).
   Quay ve T100 se la cai dat mot cau hinh pha tran rui ro cua chinh du an. Day la su that so hoc,
   khong phai khuyen nghi — quyet dinh thuoc ve master/user.
2. **Multiplicity o tang CHUONG TRINH, khong phai tang VONG.** `sqrt(2 ln k)` voi k=2 chi hieu chinh cho
   2 phep kiem TRONG vong do. Toan bo du an da chay rat nhieu vong (GATESCALE, GATEDYN, REGIME, #52,
   V1-V4...), nen "garden of forking paths" tong the lon hon k=2 rat nhieu. Do la mot han che THAT cua
   toan bo chuong trinh, khong phai thu ma `sqrt(2 ln k)` trong mot vong giai quyet duoc. Ghi lai de
   khong ai doc muc 4 thanh "T170 da duoc chung minh chac chan".
3. Nhac lai: T170 thang KHONG chi nho CI. Yeu to phan biet manh nhat o doc goc muc 5 la **rang buoc cung
   theo nam**: T170 PASS ca 5 nam trong khi baseline FAIL 2024+2025 va T130 FAIL 2024+2025.

## 6. KY LUAT
- KHONG chay backtest moi. KHONG sua `c3_rates.py` (viec tham so hoa `CI_INFLATE` theo `sqrt(2 ln k)`
  van la de xuat can **pre-reg RIENG**, chua lam).
- KHONG doi incumbent, KHONG doi quyet dinh nao — audit nay chi tra lai con so.
- KHONG 242, KHONG `git push`, holdout 2026 nguyen ven.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT

---
## PHU LUC B (2026-09-15) — GD92 da co AUDIT DOC LAP rieng; quyet dinh k=2 duoc CUNG CO
> Doc-doi-chieu, **KHONG chay gi, KHONG khoi phuc code GD92 vao repo**.

Muc 2 o tren loai GD92 khoi multiplicity voi ly do: *"GD92 BLOCKED, khong bao gio chay (co che rolling
bi xoa o `f1c43a3`); multiplicity dem cac phep kiem DA THUC HIEN"*. Ly do do van dung, nhung **chua day
du**. Sau khi doc hai tai lieu duoi day, co mot ly do thu hai **manh hon**:

**Nguon:**
- `/home/ubuntu/gate_feat_study/GD92_CODE_AND_RESULTS.md` (644 dong; code `GateRollingThreshold.java`
  da xoa + profile + ket qua goc; tao 2026-09-15, NGOAI repo).
- **`docs/audit/AUDIT_GATEDYN_GD92.md`** (trong CHINH repo nay, 20,294 byte, 2026-09-11) — audit doc lap cua
  agent AUDIT+REPLICATE ro soat claim "GD92 THANG" cua OpenClaw (commit `272d8f1`/`1c1ecca`/`41d5d76`).

**Phan quyet cua audit do: "KHONG PHAN BIET DUOC (nhieu)" + "VI PHAM PHUONG PHAP" (rieng dot GATEDYN2).**
Bon tru cot:
1. **Hieu qua khong phan biet duoc**: `d = CAGR(GD92) − CAGR(PARITY_R) = +4.98pp` voi
   `CI95 [−4.47, +16.09]` **chua 0**, va **thap hon 2.2 lan** nguong da hieu chinh cho k=9 bien the
   (`2.0963 × sd_boot = 10.90pp`).
2. **Bang chung quyet dinh bi dung sai**: thu duy nhat tach GD92 khoi cac bien the khac la **UW=116** so
   voi tran 120 — **du 4 ngay**, trong khi `PREREG_CI` muc 2.5 ghi ro UW **KHONG duoc bootstrap** (chi la
   quan sat mot lan), va hai lang gieng cung co che lai o **153 va 183**.
3. **Leak L2 (grid quanh winner)**: dot GATEDYN2 mo 6 bien the quanh diem thang bang cach doi phan vi /
   noi cua so — dung thu ma `docs/result/B4_RESULT.md` dong 179-180 **cam dich danh**. "6/6 FAIL" khong phai
   bang chung on dinh ma la dau hieu **be mat tham so gap ghenh**: ba metric dat dinh o **ba diem KHAC
   NHAU** (CV thap nhat o G90W60 = 0.469; equity cao nhat o G92W60 = 130,175; UW thap nhat o diem thu ba).
4. **Dao dau theo nam** => khong phai giam rui ro that: `d` doi chieu giua cac nam (2022 am, 2023 duong,
   2024 ~0, 2025 duong), va nam **DUY NHAT** co CI khong chua 0 la **2022 ve phia XAU**
   (**−10.06pp** [−20.971, −1.100]). Rang buoc cung 2022: GD92_R thua PARITY_R tren **ca ba truc**
   (maxDD −13.21 vs −12.46; ret nam +7.24 vs +17.30; quy min −3.81 vs +0.63). Audit ket luan nguyen van:
   no **"doi rui ro tu 2025 sang 2022"**, chu khong giam rui ro.

**Dieu audit do CONG NHAN** (phai ghi cho can): muc tieu PRIMARY ma user dat ra — phan bo lenh deu hon
theo quy — **dat that** (CV quy **0.712 → 0.518**), so lieu **tai lap byte-identical**, khong cham holdout,
khong bia so. Audit **khong** chung minh GD92 *xau hon* gate cung; no chung minh DEV 48 thang **khong du
suc phan biet** hai cau hinh o tang hieu qua. Phan bi bac bo la **buoc nhay tu "dat do deu" sang
"thang ve hieu qua"**.

**He qua cho muc 2 (k=2) cua audit nay:** loai GD92 khoi multiplicity budget **khong phai bo sot**.
Ngoai ly do "khong co so lieu de so", con mot ly do doc lap: **chinh so lieu GD92 (khi con) da bi mot
audit rieng ket luan la san pham cua quy trinh leak/nhieu**. Dem mot phep kiem nhu vay vao `k` se lam
**phinh** nguong multiplicity bang mot "phep kiem" von da bi loai vi vi pham phuong phap — tuc phat oan
T170/T130. => **k = 2 duoc CUNG CO, khong phai duoc nhan nhuong.**

*(Doi chieu: tom tat cua user khop voi noi dung file that o tat ca cac diem chinh — verdict nhieu /
CI chua 0 / UW 116 vs 120 khong CI / lang gieng 153-183 / grid-leak bi B4_RESULT cam / 6-6 fail voi ba
dinh khac nhau / dao dau theo nam voi 2022 −10.06pp / PRIMARY CV 0.712→0.518 duoc cong nhan. **Khong
phat hien sai lech dang ke.** Chi tiet bo sung co trong file that ma tom tat khong neu: he so k=9 va
nguong 10.90pp; audit noi ro no KHONG chung minh GD92 xau hon; GD92 chua he kiem tren validation/holdout.)*

**KHONG khoi phuc code GD92 vao repo. KHONG chay lai bat cu thu gi lien quan GD92.** Muc nay chi la
ghi chu lien ket tai lieu.
