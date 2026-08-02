#!/usr/bin/env python3
"""
verify_stage.py — GATE BAT BUOC TRUOC MOI FANOUT.

Bai hoc 2026-08-01 (HANDOFF_20260801_dca_grid_exit.md, muc "Bay ha tang" #1):
jar stale HAI LAN LIEN TIEP lam mat tron ca vong do.
  - Lan 1: build + bump Kaggle nhung QUEN scp sang Oracle -> sweep chay jar cu ->
           ket qua byte-identical baseline (27,412 vs 27,413). Mat ca vong.
  - Lan 2: bump Kaggle TRUOC khi them DCA_GRID_SCALE -> nhanh dcagrid8 y het dcagrid1.
Ca hai lan deu KHONG co dau hieu bao loi — job chay xong, co so, so trong "hop ly".
Day la dang loi te nhat: im lang va tao ket qua GIA.

Cach chan: mo jar DA STAGE (khong phai jar local, khong phai target/) roi kiem
cac token BAT BUOC co that su nam trong bytecode. Token = ten env var (hang chuoi
trong constant pool) hoac ten field. Thieu 1 token -> FAIL -> KHONG duoc fanout.

Dung:
    python3 verify_stage.py <jar> [--profile dca_grid|exit|base] [--token X --token Y]
    python3 verify_stage.py /home/ubuntu/java/simulator/gatecount.jar --profile dca_grid

Exit: 0 = PASS, 1 = FAIL (thieu token), 2 = loi doc jar.
"""
import argparse
import sys
import zipfile

# Class can soi + token bat buoc theo tung profile.
# Token phai la chuoi XUAT HIEN TRONG BYTECODE: ten env var (String constant) hoac ten field.
CLASSES = {
    "configs": "com/binance/chuyennd/tradecore/Configs.class",
    "dcautils": "com/binance/chuyennd/tradecore/DcaUtils.class",
    "wfotask": "com/binance/chuyennd/ai_ml/wfo/framework/tasks/StrategyWfoTask.class",
    "tradeutils": "com/binance/chuyennd/tradecore/TradeUtils.class",
}

PROFILES = {
    # Toi thieu: jar co dung nhanh grid + tran bac (ban chot tam 2026-08-01)
    "base": [
        ("configs", "DCA_GRID_ENABLED"),
        ("configs", "DCA_GRID_LEVELS"),
        ("configs", "DCA_GRID_WEIGHTS"),
        ("configs", "DCA_GRID_SCALE"),
        ("configs", "DCA_TIER_MARGIN_ENABLED"),
        ("configs", "DCA_TIER_MARGIN_CAPS"),
    ],
    # Them dang scalar => dieu kien CAN de HPO cham duoc DCA.
    # Neu thieu nhung van fanout thi HPO se quay gene ma khong doi gi -> ket qua GIA.
    "dca_grid": [
        ("configs", "DCA_GRID_SCALAR"),
        ("configs", "DCA_GRID_L1"),
        ("configs", "DCA_GRID_STEP"),
        ("configs", "DCA_GRID_LEGS"),
        ("configs", "DCA_GRID_W_RATIO"),
        ("configs", "DCA_GRID_SCALE"),
        ("configs", "DCA_TIER_CAP_BASE"),
        ("configs", "DCA_TIER_CAP_STEP"),
        ("configs", "dcaGridLevel"),
        ("configs", "dcaGridWeight"),
        ("configs", "dcaGridLegs"),
        # DcaUtils PHAI goi accessor; con doc thang mang la gene chet.
        ("dcautils", "dcaGridLevel"),
        ("dcautils", "dcaGridWeight"),
        # genome swap phai co mat trong task
        ("wfotask", "DCA_GRID_L1"),
        ("wfotask", "DCA_TIER_CAP_BASE"),
    ],
    "exit": [
        ("configs", "TS_GIVEBACK_FLOOR"),
        ("configs", "TS_MIN_GAP"),
        ("configs", "TS_GIVEBACK_RATIO"),
        ("tradeutils", "TS_MIN_GAP"),
        ("wfotask", "TS_MIN_GAP"),
        ("wfotask", "WFO_TSMULT_LO"),
    ],
}


def read_class(zf, path):
    try:
        return zf.read(path)
    except KeyError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jar")
    ap.add_argument("--profile", action="append", default=[],
                    help="base | dca_grid | exit (lap lai duoc)")
    ap.add_argument("--token", action="append", default=[],
                    help="token them dang class_key:TOKEN, vd configs:MY_FLAG")
    args = ap.parse_args()

    profiles = args.profile or ["base"]
    checks = []
    for p in profiles:
        if p not in PROFILES:
            print("FAIL: profile khong biet: %s (co: %s)" % (p, ", ".join(PROFILES)))
            return 2
        checks.extend(PROFILES[p])
    for t in args.token:
        if ":" not in t:
            print("FAIL: --token phai dang class_key:TOKEN, nhan duoc %r" % t)
            return 2
        k, v = t.split(":", 1)
        checks.append((k, v))

    try:
        zf = zipfile.ZipFile(args.jar)
    except Exception as e:  # jar hong / khong ton tai
        print("FAIL: khong mo duoc jar %s: %s" % (args.jar, e))
        return 2

    cache = {}
    missing = []
    checked = 0
    with zf:
        for class_key, token in checks:
            path = CLASSES.get(class_key)
            if path is None:
                print("FAIL: class_key khong biet: %s" % class_key)
                return 2
            if class_key not in cache:
                cache[class_key] = read_class(zf, path)
            blob = cache[class_key]
            if blob is None:
                missing.append("%s (THIEU CA CLASS %s)" % (token, path))
                continue
            checked += 1
            if token.encode("utf-8") not in blob:
                missing.append("%s.%s" % (class_key, token))

    print("verify_stage: jar=%s profiles=%s checked=%d/%d"
          % (args.jar, ",".join(profiles), checked, len(checks)))
    if missing:
        print("FAIL: jar da stage THIEU %d token -> jar STALE hoac build sai." % len(missing))
        for m in missing:
            print("  - %s" % m)
        print("CAM FANOUT. Build lai + scp lai roi chay lai lenh nay.")
        return 1
    print("PASS: jar da stage chua du token, duoc phep fanout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
