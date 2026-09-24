"""Sinh thu muc kernel Kaggle cho OFI V3: 10 kernel build (1 shard/kernel, tu ofi_v3_shards.json)
+ 1 kernel train/eval. Chay tren Windows (python311), output D:\\claudedata\\ofi_v3\\kernels\\.
Dung: python gen_kernels_v3.py [--remainder NAME SYM1,SYM2,...]  (chi dung khi shard bi cat, xem PREREG)."""
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("genk")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"D:\claudedata\ofi_v3\kernels"
SH = json.load(open(os.path.join(HERE, "ofi_v3_shards.json")))
TPL = open(os.path.join(HERE, "ofi_build_feat_v3.py"), encoding="utf-8").read()
USER = "chuyendinh"


def build_kernel(slug, shard_key, shard_map):
    d = os.path.join(OUT, slug)
    os.makedirs(d, exist_ok=True)
    src = TPL.replace("__SHARD_ID__", repr(shard_key) if isinstance(shard_key, str) else str(shard_key))
    src = src.replace("__SHARDS_JSON__", json.dumps(shard_map))
    open(os.path.join(d, "ofi_build_feat_v3.py"), "w", encoding="utf-8", newline="\n").write(src)
    meta = dict(id=f"{USER}/{slug}", title=slug, code_file="ofi_build_feat_v3.py", language="python",
                kernel_type="script", is_private=True, enable_gpu=False, enable_internet=True,
                dataset_sources=[], competition_sources=[], kernel_sources=[])
    json.dump(meta, open(os.path.join(d, "kernel-metadata.json"), "w"), indent=2)
    log.info("kernel %s: %d symbols", slug, len(shard_map[str(shard_key)]))


if len(sys.argv) > 1 and sys.argv[1] == "--remainder":
    name, syms = sys.argv[2], sys.argv[3].split(",")
    allmap = {s: i for sh in SH["shards"] for s, i in sh["syms"]}
    build_kernel(f"ofi-v3-build-{name}", 0, {"0": [[s, allmap[s]] for s in syms]})
    sys.exit(0)

shard_map = {str(sh["shard"]): sh["syms"] for sh in SH["shards"]}
builds = []
for sh in SH["shards"]:
    slug = f"ofi-v3-build-s{sh['shard']}"
    build_kernel(slug, sh["shard"], shard_map)
    builds.append(f"{USER}/{slug}")

d = os.path.join(OUT, "ofi-v3-train-eval")
os.makedirs(d, exist_ok=True)
open(os.path.join(d, "ofi_train_eval_v3.py"), "w", encoding="utf-8", newline="\n").write(
    open(os.path.join(HERE, "ofi_train_eval_v3.py"), encoding="utf-8").read())
extra = [x for x in os.environ.get("OFI_V3_EXTRA_BUILDS", "").split(",") if x]
meta = dict(id=f"{USER}/ofi-v3-train-eval", title="ofi-v3-train-eval", code_file="ofi_train_eval_v3.py",
            language="python", kernel_type="script", is_private=True, enable_gpu=False, enable_internet=False,
            dataset_sources=[f"{USER}/s1-featv2-x1-20260919"], competition_sources=[],
            kernel_sources=[f"{USER}/s1-baseline18-det-n1-20260919"] + builds + [f"{USER}/{x}" for x in extra])
json.dump(meta, open(os.path.join(d, "kernel-metadata.json"), "w"), indent=2)
log.info("train kernel sources: %s", meta["kernel_sources"])
