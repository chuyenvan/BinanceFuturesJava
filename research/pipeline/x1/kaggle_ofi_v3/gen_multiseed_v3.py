"""Sinh 4 kernel Kaggle multi-seed cho OFI V3 (docs/prereg/PREREG_S1_FREE_OFI_V3_MULTISEED.md).

Moi thay the la CO HOC (assert dung 1 lan) tren `ofi_train_eval_v3.py` da commit.
KHAC BIET DUY NHAT so voi vong goc: `random_state` cua model = seed cua kernel, ten file output,
va 1 file output PHU (`ms_diffs_s<seed>.parquet`, chuoi diff theo tick) de tinh pooled CI.
Khong doi feature/harness/fold/CI/noise-RNG/bootstrap-SEED.

Dung: OFI_V3_OUT=<dir> python gen_multiseed_v3.py [seed ...]   (mac dinh 42 43 44 45)
"""
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("genms")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OFI_V3_OUT") or "/home/ubuntu/ofi_v3/kernels_ms"
USER = "chuyendinh"
SEEDS = [int(x) for x in sys.argv[1:]] or [42, 43, 44, 45]
SRC = open(os.path.join(HERE, "ofi_train_eval_v3.py"), encoding="utf-8").read()

BASE_META = json.load(open("/home/ubuntu/ofi_v3/kernels/ofi-v3-train-eval/kernel-metadata.json"))


def patch(seed):
    s = SRC
    n0 = s.count("\n")

    s = s.replace(
        "# OFI V3 UNIVERSE -- train/eval CONFIRM cho OFI build tren TOAN BO universe",
        "# OFI V3 MULTI-SEED (seed %d) -- docs/prereg/PREREG_S1_FREE_OFI_V3_MULTISEED.md.\n"
        "# Sinh CO HOC tu ofi_train_eval_v3.py: CHI doi random_state->%d, ten output, +1 output phu "
        "(ms_diffs).\n# OFI V3 UNIVERSE -- train/eval CONFIRM cho OFI build tren TOAN BO universe" % (seed, seed), 1)

    a = "SEED = 20260919\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "MS_SEED = %d  # PREREG multi-seed: CHI doi seed model; bootstrap SEED + noise RNG giu NGUYEN\n" % seed, 1)
    s = s.replace(a, a + "MS_DIFFS = {}\n", 1)

    b = "def make_model(random_state=42):"
    assert s.count(b) == 1
    s = s.replace(b, "def make_model(random_state=MS_SEED):", 1)
    c = "        m = make_model(random_state=42)"
    assert s.count(c) == 1
    s = s.replace(c, "        m = make_model(random_state=MS_SEED)", 1)

    d = "    d_ic = cand_ic - base_ic_ref\n"
    assert s.count(d) == 1
    s = s.replace(d, d + '    MS_DIFFS[name + "__edge5"] = d_e\n'
                        '    MS_DIFFS[name + "__rankic"] = d_ic\n', 1)

    e = 'with open(f"{WORK}/ofi_result_v3.json", "w") as f:'
    assert s.count(e) == 1
    s = s.replace(e, 'MS_DIFFS["fold"] = P_cand.drop_duplicates("ts").set_index("ts")["fold"]\n'
                     'pd.DataFrame(MS_DIFFS).to_parquet(f"{WORK}/ms_diffs_s%d.parquet")\n'
                     '_p("dumped ms_diffs_s%d.parquet", MS_DIFFS["fold"].shape, flush=True)\n\n'
                     'with open(f"{WORK}/ofi_result_v3_ms_s%d.json", "w") as f:' % (seed, seed, seed), 1)

    log.info("seed %d: %d -> %d dong", seed, n0, s.count("\n"))
    return s


for sd in SEEDS:
    slug = "ofi-v3-ms-s%d" % sd
    d = os.path.join(OUT, slug)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "ofi_train_eval_v3_ms.py"), "w", encoding="utf-8", newline="\n").write(patch(sd))
    meta = dict(BASE_META)
    meta["id"] = "%s/%s" % (USER, slug)
    meta["title"] = slug
    meta["code_file"] = "ofi_train_eval_v3_ms.py"
    json.dump(meta, open(os.path.join(d, "kernel-metadata.json"), "w"), indent=2)
    log.info("kernel %s: sources=%d", meta["id"], len(meta["kernel_sources"]))
