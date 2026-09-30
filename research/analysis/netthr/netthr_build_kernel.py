import base64, hashlib, json, logging, os, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build")
arm, thr, slug = sys.argv[1], sys.argv[2], sys.argv[3]
R = "/home/ubuntu/src/BinanceFuturesJava"
src = open(R + "/research/pipeline/g015_net_train.py", "rb").read()
md5 = hashlib.md5(src).hexdigest()
tpl = open("/home/ubuntu/claude_master/0930_netthr/netthr_kernel_template.py").read()
b64 = base64.b64encode(src).decode()
b64 = "\n".join(b64[i:i + 100] for i in range(0, len(b64), 100))
code = tpl.replace("__ARM__", arm).replace("__THR__", thr).replace("__MD5__", md5).replace("__B64__", b64)
d = "/home/ubuntu/claude_master/0930_netthr/k_" + arm
os.makedirs(d, exist_ok=True)
fn = slug + ".py"
open(d + "/" + fn, "w").write(code)
meta = {"id": "chuyendinh/" + slug, "title": slug, "code_file": fn, "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_tpu": False,
        "enable_internet": False, "keywords": ["gpu"],
        "dataset_sources": ["chuyendinh/funding-oi-percoin", "chuyendinh/funding-unf15-data",
                            "chuyendinh/sel1m-code"],
        "kernel_sources": [], "competition_sources": [], "model_sources": []}
json.dump(meta, open(d + "/kernel-metadata.json", "w"), indent=1)
log.info("built %s trainer md5=%s", d, md5)
