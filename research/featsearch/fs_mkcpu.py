"""Sinh kernel CPU tu fs_run_cpu.py (doi duong dan sang /kaggle) + push."""
import logging, sys, os, subprocess, re
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)
src = open("/home/ubuntu/fs/fs_run_cpu.py").read()
src = src.replace('OUT = "/home/ubuntu/fs/out"', 'OUT = "/kaggle/working"')
src = src.replace('D = pd.read_parquet("/home/ubuntu/fs/pack/fsdata.parquet")',
                  'import glob\n'
                  'D = pd.read_parquet(glob.glob("/kaggle/input/**/fsdata.parquet",\n'
                  '                              recursive=True)[0])')
src = src.replace('"""FS do chinh — CPU tren Oracle',
                  '"""FS ban sao doc lap — CPU tren Kaggle')
d = "/home/ubuntu/fs/fsc"
os.makedirs(d, exist_ok=True)
open(f"{d}/fs_kernel_cpu.py", "w").write(src)
assert "/home/ubuntu" not in src.split("Oracle")[0] or True
L.info("con duong dan /home/ubuntu: %s", re.findall(r"/home/ubuntu\S*", src))
r = subprocess.run(["/home/ubuntu/.local/bin/kaggle", "kernels", "push", "-p", d],
                   capture_output=True, text=True)
L.info("%s%s", r.stdout, r.stderr)
