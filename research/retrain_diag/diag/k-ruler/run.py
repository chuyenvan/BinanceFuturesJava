"""rt-diag-ruler - PREREG_RETRAIN_DIAG 436977c1 muc 2.2 (D-ruler + D-src b). HOLDOUT_UNSEAL_2026_1121 (U4a). Launcher rt_diag_kernel.py (ds rt-diag-code)."""
import glob, subprocess, sys
p = [x for x in glob.glob("/kaggle/input/**/rt_diag_kernel.py", recursive=True) if "/rt-diag-code/" in x]
assert len(p) == 1, p
sys.exit(subprocess.call([sys.executable, "-u", p[0]]))
