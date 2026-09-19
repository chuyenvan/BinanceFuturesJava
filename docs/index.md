# Index — router tri thuc `docs/`

## ⚠️ TRẠNG THÁI THẬT (cập nhật 2026-09-19)

- **C2b SUPERSEDED** bởi C3 — xem [`C3_BASELINE.md`](C3_BASELINE.md).
- **VALIDATION đã nhập vào DEV mở rộng** theo quyết định user (không còn VAL sạch; validate
  cuối cùng = forward test) — xem [`PREREG_X1.md`](PREREG_X1.md) dòng 7.
- Chỉ **HOLDOUT 2026 còn sạch** (chưa đụng, chưa có pre-reg).
- **Incumbent nghiên cứu = T170** — [`../profiles/x1_gs_t170.properties`](../profiles/x1_gs_t170.properties),
  devrun `X1_GS_T170_2021`, md5 printDone `efb793e2`. Xem
  [`RESULT_DEV2021_READJUDICATE.md`](RESULT_DEV2021_READJUDICATE.md) +
  [`AUDIT_READJUDICATE_CI_RESCORE.md`](AUDIT_READJUDICATE_CI_RESCORE.md).
- **Luật CI mới**: [`AUDIT_CI_INFLATE_STANDARDIZATION.md`](AUDIT_CI_INFLATE_STANDARDIZATION.md)
  (hệ số đúng `inflate(k)=sqrt(2 ln k)`; hệ số cũ `x1.7936` dùng ở `DCA_ROUND_CAP`/
  `DCA_AGG_PERCOIN` bị nhân chồng, đã đính chính PRIMARY PASS→FAIL ở § B.2).
- **Khẩu vị rủi ro mới**: [`RISK_APPETITE.md`](RISK_APPETITE.md) (maxDD<=30%, UW<=200 ngày, quý
  xấu nhất>=-15%, tập trung 1 coin<=15% equity; ngưỡng bằng chứng CI giữ nguyên >=2 rate ngoài
  CI).
- **Shadow production 242 = FLATGRID KEEPLEG0** (paper, `SHADOW_NO_PUSH=true`) — xem
  [`DECISION_SHADOW_FLATGRID_KEEPLEG0.md`](DECISION_SHADOW_FLATGRID_KEEPLEG0.md).

Mục 1 "ĐỌC ĐẦU TIÊN" bên dưới mô tả trạng thái 09-03, giữ để truy vết;
[`RUNS_DEV.md`](RUNS_DEV.md) / [`ROADMAP_NOLEAK.md`](ROADMAP_NOLEAK.md) /
[`QUEUE.md`](QUEUE.md) đứng yên từ 09-03 / 09-02 / 09-12.

**12 RESULT gần nhất theo mtime (trích dòng phán quyết đầu file, không diễn giải):**

1. [`RESULT_SHADOW_T170_FIX.md`](RESULT_SHADOW_T170_FIX.md) (09-18): "Trước khi sửa, shadow
   không sinh entry nào" — process chết ~12 ngày không auto-restart + cấu hình lệch T170; đã
   sửa bằng systemd watchdog (`Restart=always`), kill-test PASS (~20s tự bật lại).
2. [`RESULT_D3D4_FILTER_SIM.md`](RESULT_D3D4_FILTER_SIM.md): "Verdict: NULL — cả 3 biến thể
   KHÔNG cải thiện chất lượng; giữ nguyên T170 (parity)."
3. [`RESULT_PUMPDUMP_OHLCV.md`](RESULT_PUMPDUMP_OHLCV.md): "Cả 4 detector đều NULL. Không
   detector nào đạt cả 3 tiêu chí chốt trước."
4. [`RESULT_PUMPDUMP_DETECT.md`](RESULT_PUMPDUMP_DETECT.md): "Cả 6 feature / 4 detector đều
   NULL. Không detector nào đạt cả 3 tiêu chí chốt trước."
5. [`RESULT_POSTPUMP_MEASURE.md`](RESULT_POSTPUMP_MEASURE.md): "MÔ TẢ (descriptive) — KHÔNG
   chạy sim, KHÔNG sửa `.java`, KHÔNG push" (đo tín hiệu post-pump trên n=1089 lệnh).
6. [`RESULT_S1_CORRECT_MEASURE.md`](RESULT_S1_CORRECT_MEASURE.md): "DESCRIPTIVE MEASUREMENT —
   sửa 2 lệch cấu trúc của `RESULT_S1_RANK_QUALITY.md`... KHÔNG phải bằng chứng alpha."
7. [`RESULT_S1_RANK_QUALITY.md`](RESULT_S1_RANK_QUALITY.md): "DESCRIPTIVE MEASUREMENT — lần
   ĐẦU đo trực tiếp chất lượng xếp hạng của S1... KHÔNG phải bằng chứng alpha."
8. [`RESULT_TREND_RANK_IC.md`](RESULT_TREND_RANK_IC.md): "DESCRIPTIVE SCREENING (không phải
   bằng chứng alpha). Chạy MỘT lần, không tune."
9. [`RESULT_BD_THRESHOLD_FRAGILITY.md`](RESULT_BD_THRESHOLD_FRAGILITY.md): "Edge BIG_DOWN mong
   manh theo ngưỡng. PnL BIG_DOWN dao 2x (8,323 → 16,254 USD) trong 4 biến thể ngưỡng lân cận."
10. [`RESULT_DCA_AGG_PERCOIN.md`](RESULT_DCA_AGG_PERCOIN.md): "Per-coin 15% là công cụ ĐÚNG —
    chặn được tập trung (17.15% → 12.51%)..." — **⚠️ PRIMARY nay đã đính chính PASS→FAIL**, xem
    banner đầu file.
11. [`RESULT_DCA_ROUND_CAP.md`](RESULT_DCA_ROUND_CAP.md): "NULL — giữ T170. Trần 10%/lượt
    (CAP10) KHÔNG binding..." — **⚠️ PRIMARY nay đã đính chính PASS→FAIL**, xem banner đầu file.
12. [`RESULT_SEL_BIGDOWN.md`](RESULT_SEL_BIGDOWN.md): "Verdict: NULL — giữ nguyên T170
    (parity)."

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
5. **GATE ENTRY** — [LEAN_GATE_AUDIT](LEAN_GATE_AUDIT.md) (do 48 thang: floor CO bind 1 lan =>
   **cam** rut gon gate ve `K*symbolPred`) roi [L7_LEAN_GATE](L7_LEAN_GATE.md) (cong entry ve MOT
   class `tradecore/EntryGate`, 1 knob, sim+live dung chung, `printDone.csv` byte-identical).
   Tien than: [AUDIT_GATE_DYN_PARITY](AUDIT_GATE_DYN_PARITY.md), [L6_GATE_DYN_FIX](L6_GATE_DYN_FIX.md),
   [RESULT_FLATGATE](RESULT_FLATGATE.md). Viec con lai: [L8_SIZING_PARITY_BACKLOG](L8_SIZING_PARITY_BACKLOG.md).

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
- [KAGGLE_SIM](KAGGLE_SIM.md) — chay sim SONG SONG tren Kaggle CPU (5 slot), neo **60395**,
  API `tools/kaggle_sim.py` (`submit`/`wait`/`fetch`).
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

- [L4_LIVE_BUILDMAP](L4_LIVE_BUILDMAP.md) — `build_map` chay LIVE: shadow = C3 o tang entry (quy uoc `symbolPred = 1 - P(win)`, cong REPLAY 3 ngay DEV).
