# Index — router tri thuc `docs/`

> **VIET LAI 2026-09-03 (M6).** Ban cu tro tuong minh toi **37 duong dan KHONG TON TAI**, trong
> do 6 file no goi la bat buoc doc: `CORE.md` ("Luon doc CORE"), `FINDINGS.md` ("NGUON SU THAT"),
> `SESSION_START.md` ("DOC DAU TIEN moi session"), `DATA_STATE.md`, `architecture.md`,
> `PIPELINE.md`. Ca 6 da bi don sang `archive/_cleanup_20260829` o commit `c446f0a`. Mot agent
> moi doc router cu se di tim 6 file khong co roi bo qua `ROADMAP_NOLEAK.md` va `RUNS_DEV.md` —
> hai file that su song.
>
> **KHONG tao file rong cho du danh sach.** Router chi tro vao file CO THAT. Cai da archive thi
> ghi ro la archive.
>
> Luat giu router nay dung: moi lan xoa/di chuyen file trong `docs/`, chay lai kiem link truoc
> khi commit. Router hong = agent doc sai su that.

## 1. DOC DAU TIEN (theo thu tu)

1. [AUDIT_APPLIED](AUDIT_APPLIED.md) — **trang thai THAT hom nay**: 57 muc da danh gia, muc nao
   da apply / chua / VOID, doi chieu truc tiep voi `profiles/` va `src/main`. Kem 13 mau thuan
   docs-vs-code (M1..M13). Docs noi da apply ma code khong co thi **code thang**.
2. [C2B_SPEC](C2B_SPEC.md) — dac ta cau hinh dang la ung vien freeze (C2b, DEV equity **60390**):
   gate 2 tang, selector, exit, sizing, param TRO, cach tai lap.
3. [RUNS_DEV](RUNS_DEV.md) — bang moi run DEV da chay + so do duoc. **Nguon su that ve "da do gi".**
4. [ROADMAP_NOLEAK](ROADMAP_NOLEAK.md) — hang doi con lai + gi da dong.

## 2. CAU HINH (he `TRADING_PROFILE`, chot 2026-09-03)

- [TRADING_CONFIG_REDESIGN](TRADING_CONFIG_REDESIGN.md) — thiet ke cong cau hinh B1..B5, cai da
  xong / con lai, va cac dinh chinh ghi chep (muc 5 = M1, muc 8 = cong thuc gate).
- [CONFIG_FIELD_MAP](CONFIG_FIELD_MAP.md) — ban do field sinh tu ma nguon (**khong go tay**,
  chay lai `tools/gen_config_field_map.py`).
- [CONFIG_INVENTORY](CONFIG_INVENTORY.md) — kiem ke key sinh tu ma nguon (**khong go tay**,
  chay lai `tools/gen_config_inventory.sh`).
- `profiles/c2b.properties` (23 key) va `profiles/c2b_min.properties` (16 key, da chung minh
  byte-identical) — **nguon su that duy nhat cho tham so giao dich**, ke ca bins selector.
- Guard: `tools/check_cfg_gateway.sh` (tham so giao dich cam doc `System.getenv` truc tiep).

## 3. PIPELINE DU LIEU + MO HINH

- [**research/pipeline/README**](../research/pipeline/README.md) — **pipeline sinh bins selector
  S1** (nguon edge duy nhat da chung minh): thu tu chay raw -> `feat_v2.parquet` ->
  `cand_dev.parquet` -> `pred_s1a2.parquet` -> `predwf_map_s1a2` -> dataset WFO -> sim, kem
  lenh cu the, thoi gian, moi truong va hyperparameter that cua `s1_rank.py`.
- [**research/pipeline/BINS_MANIFEST**](../research/pipeline/BINS_MANIFEST.md) — sha256 tung file
  bins + ban sao luu Kaggle PRIVATE. **Doc truoc khi tin bat ky so C2b nao.**
- [WFO_DATAFLOW](WFO_DATAFLOW.md) — luong du lieu WFO + env cua `ExportWfoDataset`.
- [insights/WFO_ROADMAP](insights/WFO_ROADMAP.md) — hub WFO.
- [DATA_GOVERNANCE_PROTOCOL](DATA_GOVERNANCE_PROTOCOL.md) · [DATA_CHUNKING_STANDARD](DATA_CHUNKING_STANDARD.md)
- `tools/run_c2b_dev.sh` — ban chuan chay lai C2b tren DEV + cong byte-identity tu dong.

## 4. LUAT (nap dung cai dang cham)

- [rules/backtest](rules/backtest.md) — toan ven va tai lap backtest/sim/golden + cam bay doc ket qua.
- [rules/code](rules/code.md) — quy uoc code Java/HPO.
- [rules/security](rules/security.md) — secret/key lo thi rotate, khong echo.
- [rules/build-env](rules/build-env.md) — Maven + protobuf.
- [rules/run-226](rules/run-226.md) — chay job java tren 226 (**LICH SU**: topology da chuyen sang
  Oracle hub; giu de truy vet).
- [rules/task-workflow](rules/task-workflow.md) · [rules/ce-buttons](rules/ce-buttons.md)
- [KAGGLE_RULES](KAGGLE_RULES.md) — bat buoc truoc moi Kaggle job (slot=5, 12h-kill, System.exit).

## 5. PRE-REGISTRATION (khong sua noi dung da chot — chi them phu luc dinh chinh)

- [preregistration_frame_v1_2026-08-23](preregistration_frame_v1_2026-08-23.md) — khung chung.
- [PREREG_GS](PREREG_GS.md) — grid-search wave 1 (**dang chay, KHONG SUA**).
- [PREREG_H3](PREREG_H3.md) FAIL 4/5 · [PREREG_K](PREREG_K.md) VO HIEU ·
  [PREREG_BR](PREREG_BR.md) khong cai thien · [PREREG_RND](PREREG_RND.md) PASS chua bam nut.
- [PHASE1_DECISION_SURFACE](PHASE1_DECISION_SURFACE.md) — **7 quyet dinh Pha 1 cot "QUYET" con
  TRONG HOAN TOAN**; 2 muc con nguy hiem (A2c label SL 0.03 placeholder, A2e grid 15m overlap
  horizon 4h = nghi leak L1) nam ngay tren duong gate cua C2b. Xem AUDIT M13.
- [PHASE1_RECIPE_FROZEN_v1](PHASE1_RECIPE_FROZEN_v1.md) · [PHASE1_RECIPE_DRAFT](PHASE1_RECIPE_DRAFT.md) ·
  [PHASE1_GENE_REFERENCE](PHASE1_GENE_REFERENCE.md)
- [GS_BASELINE_NOTE](GS_BASELINE_NOTE.md) — hai diem neo **60390** (aerospike) va **60395** (file):
  lech 1 lenh / 970 = 0.008%. Moi so sanh Oracle<->Kaggle chi tin toi ~0.01%.

## 6. QUYET DINH (ADR)

- [decisions/](decisions/) — `0000`..`0012`. `0003` (genome 13) **da thay boi `0012`** (genome 18).
  `0007-survivorship-backfill` hien hanh, `0007-survivorship-material` SUPERSEDED.
  `0008-circuit-breaker` — **doc kem M2: co che nay da bi xoa khoi SIM 2026-09-03**.

## 7. RUNBOOK VAN HANH

- [runbooks/runbook_live_242_2026-08-19](runbooks/runbook_live_242_2026-08-19.md) — live 242
  (muc 12: bang venh live<->sim, live chay `K=5` con sim `K=8` — venh CHUA dong, xem AUDIT M10).
- [runbooks/runbook_shadow_off_trade_2026-08-23](runbooks/runbook_shadow_off_trade_2026-08-23.md)
  — **kill-switch `SHADOW_NO_PUSH`. KHONG duoc xoa/sua.**
- [runbooks/wfo_ops_runbook_2026-08-13](runbooks/wfo_ops_runbook_2026-08-13.md) ·
  [runbooks/RUNBOOK_CPCV_VALIDATION](runbooks/RUNBOOK_CPCV_VALIDATION.md) (nhanh CPCV da FAIL DSR, dong)

## 8. KHAC

- [AGENTS](AGENTS.md) — ban do agent dang lam gi (⚠️ co the lech, doi chieu `RUNS_DEV.md`).
- [HANDOFF-24-8-2026-B](HANDOFF-24-8-2026-B.md) — ban giao 2026-08-24.
- [architecture/README](architecture/README.md) — so do kien truc (co 2 file HTML kem theo).
- [../orchestrator/cognitive-execution-framework-v3.md](../orchestrator/cognitive-execution-framework-v3.md) — CE V3.
- [../tasks/](../tasks/) — task theo thu tu logic.

## 9. DA ARCHIVE — KHONG con o `docs/` (dung tro toi nhu file song)

`CORE.md`, `FINDINGS.md`, `SESSION_START.md`, `DATA_STATE.md`, `architecture.md`, `PIPELINE.md`,
`PIPELINE_PROVENANCE.md`, `WFO_DATA_PIPELINE_MASTER.md`, `DATA_VALIDATION_FRAMEWORK.md`,
`REDESIGN_INFRA_20260804.md`, `REBUILD_ROADMAP.md`, `AGENT_WORKFLOW.md`, `DEFERRED.md`,
`LIB_BINANCE_OLD.md`, `SOLUTION_FRAMEWORK_20260711.md`, `STRATEGY_ROADMAP_3PART.md`,
`STRATEGY_CONSOLIDATED.md`, `db/index.md`, `reference/*`, `insights/*` (tru `WFO_ROADMAP.md`),
`runbooks/BACKFILL_SURVIVORSHIP.md`.

Tim chung o [archive/](archive/) (chu yeu `archive/_cleanup_20260829/`, commit `c446f0a`).
Chung la **SNAPSHOT lich su**: so lieu trong do co the da bi thoi (nhat la moi thu truoc ban fix
funding `49fde3b` va truoc `5f40a90`). Muon dung lai mot file thi phai doi chieu lai voi
`src/main` roi moi keo ra khoi archive.
