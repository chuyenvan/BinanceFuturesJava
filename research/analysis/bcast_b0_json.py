import json, logging, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_json")
v = json.load(open("/home/ubuntu/claude_master/1012/bcast/b0_vision.json"))
g = json.load(open("/home/ubuntu/claude_master/1003/ho1/gate/manifest_gate.json"))
gate = {s: dict(train_ts_min=r["train"]["train_ts_min"], train_ts_max=r["train"]["train_ts_max"],
                label_years=r["train"]["label_years"], model_sha256=r["train"]["model_sha256"]) for s, r in g["seeds"].items()}
out = dict(
    status="STOP_LEAK_WAIT_MASTER",
    leak=dict(gate_8seed=gate,
              net015_f15=dict(onnx_sha256="7921ceaf2405049ddf2c23187264c34d6c95a38125f33c9ef3506f02f4e6dd8b",
                              tool1_first_file="features_20210101_to_20210401.t1c", train_from="2021-01 (expanding; first OOS fold 2022-01)",
                              evidence="docs/experiment/G3_X26_RECOVERY.md 3.4; G015X26_PROVENANCE.md"),
              s1=dict(sha256="af706dc654c96f075caddc5f4153c768eec0732a28340cf9adbd6a6f791d8bf1", ledger_T0="2021-04-01",
                      evidence="research/pipeline/x1/x1_ledger.py:19; RESULT_S1REFRESH.md"),
              clean_span_utc=["2020-01-01", "2020-12-31"], leaked_span=["2021-01-01", "2021-06-30"]),
    proposal_P1=dict(build_utc=["2020-01-01", "2021-01-03"], score_plus07=["2020-05-01 00:00", "2020-12-31 23:59"],
                     strict_variant_end="2020-11-30", tech_sim=dict(TIME_RUN="20200101", SIM_END_DATE="20210101")),
    mapper=dict(not_in_mapper=["LENDUSDT", "BTCSTUSDT"], rule="drop+list (HO4)", optional_local_ids=[752, 753]),
    funding_missing_months=dict(QTUMUSDT=["2020-02"], LENDUSDT=["2020-11"], ICPUSDT=["2021-05", "2021-06"]),
    vision=dict(n_dirs=v["n_dirs"], n_uni=v["n_uni"], metrics_first_min=v["metrics_first_min"], metrics_none=v["metrics_none"],
                per_month={k: {kk: vv for kk, vv in r.items()} for k, r in v["per_month"].items()},
                early_syms=v["early_syms"]),
    kaggle_kernels=0, sims=0)
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True)
log.info("ghi %s", sys.argv[1])
