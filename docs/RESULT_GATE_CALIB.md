# RESULT_GATE_CALIB — hieu chuan gate quanh T170 (1.30 / 2.10): **BLOCKED (du lieu chua len Kaggle)**

Pre-reg: `docs/PREREG_GATE_CALIB.md` (commit cung dot nay, `module`). Baseline T170 `efb793e2468ca3a7318da0f0ad23d4fc` (n=1089).
**Vong nay KHONG chay sim, KHONG push.**

## 0. Ket luan mot cau

**BLOCKED — parity (byte-identical `efb793e2`) KHONG chay duoc tren Kaggle vi bundle `sim-c2b-bundle`
dang chua dataset CU `wfo_ds_clean` (10-fold, 2022-01), KHONG phai `wfo_ds_x1_2021` (18-fold, 2021-07)
ma T170 dang tro vao.** Khong phai loi tool, khong phai quota, khong phai auth — thieu du lieu.

## 1. Phan tich code gate (buoc 1 — da lam, xac nhan)

`EntryGate.java` + `Configs` (key `SIM_GATE_DYN_SCALE`):
```
thr = MIN_MOMENTUM_15M(0.008) * max(DYN_MIN=0.26787, symbolPred/SCORE_BASE(0.15) * DYN_MULT(1.28760)) * GATE_DYN_SCALE
PASS <=> !(predReturn15M < thr)
```
- `SIM_GATE_DYN_SCALE=1.70` (T170) = nhan **1.70** vao `dyn_thr` da tinh. `>1` = **CHAT hon** (nguong cao => it lenh),
  `<1` = **LONG hon**. Log that T170: `[GATE] scale=1.7 base=0.008 n_cand=17925650 n_pass=841`.
- Tang scale => nguong cao hon => bot coin qua cong (loc gay hon); giam scale => nhieu coin qua hon.
  Chi ap o nhanh dyn (`symbolPred != null`); nhanh nguong co so (BIG_DOWN/DCA_LEVEL1) khong bi scale.
- => 2 bien the pre-reg: **1.30 (long hon)** va **2.10 (chat hon)**, doi xung quanh 1.70.

## 2. Blocker — chi tiet (da xac minh, khong doan)

| thu | T170 baseline (`X1_GS_T170_2021`) | Kaggle `sim-c2b-bundle` (staging `/home/ubuntu/simbundle`) |
|---|---|---|
| dataset | `wfo_ds_x1_2021` (funding.bin **4.4GB**) | `wfo_ds_clean` (funding.bin **1.8GB**) |
| `leakFreeFrom` | **2021-07-01** | 2022-01-01 |
| `TIME_RUN` | **20210701** | 20220101 |
| `foldCount` | **18** | 10 |
| `fundingPredDir` | `predwf_map_s1a2_x1_2021` (18 bins, 20210701..20251001) | `predwf_map_s1a2` (10 bins, 20220101..20240401) |
| `md5_funding` | `8e57d900d5c54c744bfcaf5c9b27fc93` | `7b9ba20f7a5b49ec3d5aaafed60d45be` |

- Kaggle bundle manifest (da tai ve de kiem): `leakFreeFrom=2022-01-01, foldCount=10, fundingPredDir=predwf_map_s1a2,
  md5_funding=7b9ba20f...` => la data CU, KHONG phai data T170.
- Profile `x1_gs_t170` **khong co trong bundle** (bundle chi co `c2b/c2b_min/c3/e1_*/f2_*`...).
- `wfo_ds_clean` KHONG con ton tai o dia (chi con `wfo_ds_x1_2021`) => bundle la snapshot cu chua duoc restage cho T170.
- Doc `KAGGLE_SIM.md` §3/§4 (bundle layout) chi dung cho `wfo_ds_clean` + `predwf_map_s1a2`; muc §6
  ("exit/gate/sizing chay Kaggle binh thuong") dung voi CUNG bundle cu do, KHONG dung voi dataset T170 moi.

### De unblock can (khong tu che, can phe duyet)
Stage bundle MOI voi `wfo_ds_x1_2021` (funding.bin 4.4GB + market.bin 51MB + pred.bin 40MB + manifest) +
bins `predwf_map_s1a2_x1*` + jar hien hanh + `prof_x1_gs_t170/t130/t210` + config/exchange_info, roi
`dataset_create_version` (~**5.4GB upload**). Day la cong viec moi, chua duoc giao trong task.

## 3. Da kiem / khong phai blocker
- `tools/kaggle_sim.py` CON (API `submit/wait/fetch` OK).
- Auth Kaggle OK (lie ke duoc toan bo dataset `chuyendinh/*`).
- Aerospike Oracle `161.118.212.3:3222` **REACHABLE** (Symbol Mapper 863 symbols se load duoc).
- Jar `target/binance-java-sdk-1.2.4.jar` (build 2026-09-17): moi commit java tu 09-14 deu "default OFF
  byte-identical" + nhieu moc xac nhan `parity T170 efb793e2 KHOP` => jar **du kien** tai lap duoc baseline.

## 4. Chi phi / thoi gian
- Kaggle: **0** (khong push kernel nao — chan truoc khi can Kaggle).
- Phan tich code + xac minh blocker: chi doc file + API lie ke dataset (khong job JVM).

## 5. Khong lam
Khong push, khong cham 2026/HOLDOUT, khong dung/kill tien trinh song, khong tu che bundle moi (can phe duyet),
khong chay sim tren Oracle (JVM slot bi chiem).
