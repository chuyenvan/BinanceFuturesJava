#!/usr/bin/env python3
"""FAMILY2B driver Kaggle (LONG: SL / TP theo ti le R, KHONG DCA) tren nen r1-a3.
Prereg: docs/prereg/PREREG_FAMILY2B.md (commit 5f917679) muc 4 (luoi 24 + NEN), muc 8 (driver), muc 9 (smoke).
File MOI, import r1_a3_driver (KHONG sua ban cu). Chi doi CAU HINH: overrides profile + extra_env.

Usage (seed chi A1 | S7; cwd bat ky):
  list                         bang 25 cau hinh (overrides them / bo / extra_env)
  dry <cell> <seed>            in cfg day du + kernel-metadata (KHONG goi mang, KHONG ghi file)
  smoke <cell> <seed>          push 1 kernel smoke (tag f2b-smk-<cell>-<seed>), khong can PARITY_OK
  fetch <cell> <seed> [--smoke]  keo output (xoa-tuong-minh ban cu: chuyen sang out/_stale) + tom tat;
                               --smoke: kiem dau hieu muc 9 (+ A1 N1/N2), FAIL -> exit 6
  parity <seed> [--wait]       cell NEN (tag f2b-nen-<seed>). MOT buoc moi lan goi (mac dinh KHONG cho):
                               chua push -> push; dang chay -> bao; COMPLETE -> chuyen out cu sang _stale, fetch MOI,
                               so md5 printDone voi r1-a3-<seed> -> PARITY_OK_<seed>.json | lech exit 3; loi -> exit 7
  push <cell> <seed>           1 o luoi; can PARITY_OK hop le (bam lai md5 printDone tren dia); free_slots() truoc
  grid [--max-slots N]         MOT vong: fetch o COMPLETE, push o chua push (thu tu bang prereg; dung khi FREE=0 hoac
                               so kernel f2b dang chay >= N), in bang 48 o roi THOAT. Kernel loi: ghi nhan, KHONG push lai.
  status                       in bang 48 o + parity/smoke (khong push, khong fetch)
Moi push: tu choi neu f2b_driver.py / test_f2b_driver.py chua commit / da sua sau commit (git status --porcelain);
ghi git HEAD + sha256 f2b_driver.py vao pushed/<tag>.json.
Log bang logging (r1_a3_driver da basicConfig stdout); bang cung qua logging.
Exit code: 0 ok | 2 sai tham so / cau hinh | 3 parity lech | 4 het slot | 5 chan (chua parity / da push / chua commit)
           | 6 smoke FAIL | 7 kernel loi.
"""
import argparse
import collections
import csv
import contextlib
import gzip
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import r1_a3_driver as R  # noqa: E402

log = logging.getLogger("f2b")

PREREG = "docs/prereg/PREREG_FAMILY2B.md@5f917679"
SEEDS = ("A1", "S7")
# tien to md5 printDone run tham chieu r1-a3-<seed> (prereg muc 1) - CHI de doi chieu; md5 DAY DU doc tu result.json
REF_MD5_PREFIX = {"A1": "8986d332", "S7": "083e3de0"}
JAR_DS = "sim-jar-tsx"
JAR_SHA_PREFIX = "cc0f9d11"
SIM_END = "20251231"
SIM_END_MAX = 20251231
NEN = "NEN"
X14_KEYS = ("SIM_LOSER_TS_EXT_HOURS", "SIM_LOSER_TS_EXT_DAYS")
WL_ADD = frozenset({"SIM_PRE_ARM_SL", "SIM_TAKE_PROFIT_RATE", "SIM_TAKE_PROFIT_ONLY", "DCA_GRID_WEIGHTS", "SIM_F_BASE"})
WL_ENV = frozenset({"WFO_DISABLE_DCA"})
FORBIDDEN = ("DCA_GRID_ENABLED",)
STATE_DIR = os.environ.get("F2B_STATE_DIR", "/home/ubuntu/kaggle_sim/f2b_state")

# ---- BANG DUY NHAT (prereg muc 4) ----
SL_LEVELS = (("05", "-0.05"), ("10", "-0.10"), ("20", "-0.20"))      # SIM_PRE_ARM_SL
R_LEVELS = (("R05", "0.5"), ("R1", "1"), ("R2", "2"))                 # TP = R x |SL|
SIZING = (("S1", {}),                                                 # profile 1,1,1,1 ; SCALE 6 ; F_BASE 0.015
          ("S2", {"DCA_GRID_WEIGHTS": "1,0,0,0", "SIM_F_BASE": "0.0075"}))
ENV_NODCA = {"WFO_DISABLE_DCA": "1"}

Cell = collections.namedtuple("Cell", "add drop env")


def _fmt(d):
    """Decimal -> chuoi nhu bang prereg: 0.025, 0.05, 0.10, 0.20, 0.40, -0.05 ..."""
    s = format(d.quantize(Decimal("0.001")), "f")
    return s[:-1] if s.endswith("0") else s


def _mk_cells():
    rows = []
    for sn, sl in SL_LEVELS:
        for rn, rm in R_LEVELS:
            tp = _fmt(abs(Decimal(sl)) * Decimal(rm))
            rows.append(("A" + sn + rn, {"SIM_PRE_ARM_SL": sl, "SIM_TAKE_PROFIT_RATE": tp,
                                         "SIM_TAKE_PROFIT_ONLY": "true"}, X14_KEYS))
    for sn, sl in SL_LEVELS:
        rows.append(("B" + sn, {"SIM_PRE_ARM_SL": sl}, ()))
    cells = collections.OrderedDict()
    for name, add, drop in rows:
        for szn, szov in SIZING:
            a = dict(add)
            a.update(szov)
            cells["%s-%s" % (name, szn)] = Cell(a, tuple(drop), dict(ENV_NODCA))
    cells[NEN] = Cell({}, (), {})
    return cells


CELLS = _mk_cells()
assert len(CELLS) == 25, len(CELLS)
for _n, _c in CELLS.items():
    assert set(_c.add) <= WL_ADD and set(_c.env) <= WL_ENV, _n
    assert not any(k in _c.add for k in FORBIDDEN), _n


class F2BError(Exception):
    code = 2

    def __init__(self, msg, errs=None):
        super().__init__(msg)
        self.errs = list(errs or [])


class ParityMissing(F2BError):
    code = 5


class AlreadyPushed(F2BError):
    code = 5


class NoSlot(F2BError):
    code = 4


class ParityMismatch(F2BError):
    code = 3


def seed_ok(seed):
    if seed not in SEEDS:
        raise F2BError("seed %r khong hop le (chi %s)" % (seed, "/".join(SEEDS)))
    return seed


def cell_ok(cell):
    if cell not in CELLS:
        raise F2BError("cell %r khong co trong bang prereg muc 4" % (cell,))
    return cell


def tag_of(cell, seed, smoke=False):
    cell_ok(cell)
    seed_ok(seed)
    if smoke and cell == NEN:
        raise F2BError("smoke khong dung cell NEN")
    name = "nen" if cell == NEN else cell
    return ("f2b-smk-" if smoke else "f2b-") + name + "-" + seed.lower()


def _jload(p):
    with open(p) as f:
        return json.load(f)


def _read(p):
    with open(p) as f:
        return f.read()


_A3_SHA = {}


def _a3_sha_cached():
    """R.a3_sha() bam 888MB moi lan -> cache trong tien trinh (chi bo nho, khong sua file)."""
    if "v" not in _A3_SHA:
        _A3_SHA["v"] = _orig_a3_sha()
    return _A3_SHA["v"]


_orig_a3_sha = R.a3_sha
R.a3_sha = _a3_sha_cached


@contextlib.contextmanager
def _tmp_workdir(ks):
    """R.build ghi run.py vao ks.WORKDIR/<tag> -> chuyen sang thu muc tam de KHONG dung toi workdir r1-a3-<seed>."""
    old = ks.WORKDIR
    d = tempfile.mkdtemp(prefix="f2b_base_")
    ks.WORKDIR = d
    try:
        yield d
    finally:
        ks.WORKDIR = old
        shutil.rmtree(d, ignore_errors=True)


def base_r1a3(seed):
    """(ks, ref, cfg, md, code) cua r1-a3-<seed> sinh boi R.build (ban goc, khong sua)."""
    seed_ok(seed)
    ks = R.GA.ks_mod()
    with _tmp_workdir(ks):
        _ks, folder, ref, cfg = R.build(seed)
        md = _jload(os.path.join(folder, "kernel-metadata.json"))
        code = _read(os.path.join(folder, "run.py"))
    return ks, ref, cfg, md, code


def build_f2b(seed, cell, smoke=False, write=True):
    ks, ref0, cfg0, md0, code0 = base_r1a3(seed)
    c = CELLS[cell_ok(cell)]
    tag = tag_of(cell, seed, smoke)
    ov = {k: v for k, v in cfg0["overrides"].items() if k not in c.drop}
    clash = set(c.add) & set(ov)
    if clash:
        raise F2BError("key them da co trong OV r1-a3 (prereg gia dinh sai): %s" % sorted(clash))
    ov.update(c.add)
    cfg = dict(cfg0)
    cfg["tag"] = tag
    cfg["overrides"] = ov
    cfg["extra_env"] = dict(c.env)
    if cfg["sim_end_date"] != SIM_END or int(cfg["sim_end_date"]) > SIM_END_MAX:
        raise F2BError("sim_end_date %r vuot / khac %s" % (cfg["sim_end_date"], SIM_END))
    old_js, new_js = repr(json.dumps(cfg0)), repr(json.dumps(cfg))
    if code0.count(old_js) != 1:
        raise F2BError("run.py r1-a3: khong tim thay dung 1 lan CFG json")
    code = code0.replace(old_js, new_js)
    ref = ks.kernel_ref(tag)
    md = dict(md0)
    md["id"] = ref
    md["title"] = ref.split("/")[1]
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    if write:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "run.py"), "w") as f:
            f.write(code)
        with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
            json.dump(md, f, indent=1)
    return {"ks": ks, "tag": tag, "ref": ref, "folder": folder, "cfg": cfg, "md": md, "code": code,
            "cell": cell, "seed": seed, "base_ref": ref0, "base_cfg": cfg0, "base_md": md0, "base_code": code0}


def _ref_result(ks, tag):
    return _jload(os.path.join(ks.OUTDIR, ks.slug(tag), "result.json"))


def _s(d):
    return {str(k): str(v) for k, v in d.items()}


def check_f2b(b):
    """(a) OV r1-a3 tru drop == tsx-x14-<seed> (va r1-a3-<seed>) tru drop; (b) key them trong whitelist;
    (c) extra_env chi WFO_DISABLE_DCA; (d) jar sim-jar-tsx; (e) sim_end_date == 20251231; (f) phan con lai cfg/md
    trung r1-a3 tru tag/id/title. Loi -> F2BError."""
    ks, cfg, md, seed = b["ks"], b["cfg"], b["md"], b["seed"]
    c = CELLS[b["cell"]]
    err = []
    ov = _s(cfg["overrides"])
    for k in FORBIDDEN:
        if k in ov:
            err.append("cam key %s" % k)
    for reft in ("tsx-x14-" + seed.lower(), "r1-a3-" + seed.lower()):
        rj = _ref_result(ks, reft)
        rov = _s(rj["overrides"])
        miss = [k for k in c.drop if k not in rov]
        if miss:
            err.append("%s: key bo %s khong co trong run tham chieu" % (reft, miss))
        base = {k: v for k, v in rov.items() if k not in c.drop}
        mine = {k: v for k, v in ov.items() if k not in c.add}
        if base != mine:
            err.append("(a) OV r1-a3 (tru drop) khac %s: tsx=%s f2b=%s" % (reft, json.dumps(base, sort_keys=True)[:400],
                                                                          json.dumps(mine, sort_keys=True)[:400]))
        if rj.get("profile") != cfg["profile"]:
            err.append("profile %s != %s (%s)" % (cfg["profile"], rj.get("profile"), reft))
        extra = set(ov) - set(base)
        if not extra <= WL_ADD:
            err.append("(b) key them ngoai whitelist: %s" % sorted(extra - WL_ADD))
        changed = [k for k in set(ov) & set(base) if ov[k] != base[k]]
        if changed:
            err.append("(b) key r1-a3 bi doi gia tri: %s" % sorted(changed))
    env = _s(cfg.get("extra_env") or {})
    if not set(env) <= WL_ENV:
        err.append("(c) extra_env ngoai whitelist: %s" % sorted(set(env) - WL_ENV))
    if any(v != "1" for v in env.values()):
        err.append("(c) extra_env gia tri != '1': %s" % env)
    if cfg.get("jar_ds") != JAR_DS or (ks.USER + "/" + JAR_DS) not in md["dataset_sources"]:
        err.append("(d) jar_ds %r != %s" % (cfg.get("jar_ds"), JAR_DS))
    if cfg.get("sim_end_date") != SIM_END or int(cfg["sim_end_date"]) > SIM_END_MAX:
        err.append("(e) sim_end_date %r" % cfg.get("sim_end_date"))
    rest = {k: v for k, v in cfg.items() if k not in ("tag", "overrides", "extra_env")}
    rest0 = {k: v for k, v in b["base_cfg"].items() if k not in ("tag", "overrides", "extra_env")}
    if rest != rest0:
        err.append("(f) cfg ngoai overrides/extra_env/tag khac r1-a3")
    if b["base_cfg"].get("extra_env"):
        err.append("(f) r1-a3 extra_env khong rong")
    m1 = {k: v for k, v in md.items() if k not in ("id", "title")}
    m0 = {k: v for k, v in b["base_md"].items() if k not in ("id", "title")}
    if m1 != m0:
        err.append("(f) kernel-metadata khac r1-a3 ngoai id/title")
    if err:
        for e in err:
            log.error("CHECK_FAIL %s: %s", b["tag"], e)
        raise F2BError("check_f2b %s: %d loi" % (b["tag"], len(err)), err)
    log.info("CHECK_OK %s (cell %s seed %s): add=%s drop=%s env=%s", b["tag"], b["cell"], seed,
             json.dumps(c.add, sort_keys=True), list(c.drop), json.dumps(c.env))
    return True


# ---- loi bo sung ----
class NotCommitted(F2BError):
    code = 5


class SmokeFail(F2BError):
    code = 6


class KernelError(F2BError):
    code = 7


# ---- state (ngoai worktree) ----
def _state(*p):
    d = os.path.join(STATE_DIR, *p[:-1])
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, p[-1])


def parity_file(seed):
    return os.path.join(STATE_DIR, "PARITY_OK_%s.json" % seed_ok(seed))


def pushed_file(tag):
    return os.path.join(STATE_DIR, "pushed", tag + ".json")


def _marker(tag):
    p = pushed_file(tag)
    return _jload(p) if os.path.exists(p) else None


def _save_marker(tag, j):
    with open(_state("pushed", tag + ".json"), "w") as f:
        json.dump(j, f, indent=1)


def out_dir(ks, tag):
    return os.path.join(ks.OUTDIR, ks.slug(tag))


def _find(d, name):
    m = []
    for root, _dirs, files in os.walk(d):
        if name in files:
            m.append(os.path.join(root, name))
    return sorted(m)[0] if m else None


def ref_md5(ks, seed):
    """md5 printDone DAY DU cua r1-a3-<seed> tu ho so run tham chieu; doi chieu tien to prereg."""
    r = _ref_result(ks, "r1-a3-" + seed.lower())
    m = r["r1_a3"]["md5_printdone"]
    if not m.startswith(REF_MD5_PREFIX[seed]):
        raise F2BError("md5 ho so r1-a3-%s=%s khong khop tien to prereg %s" % (seed, m, REF_MD5_PREFIX[seed]))
    return m, r


def _md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# ---- C1: chi push ban da commit ----
GUARD_FILES = ("f2b_driver.py", "test_f2b_driver.py")


def _git_state():
    """(top, head, porcelain) cua worktree chua file nay."""
    top = subprocess.check_output(["git", "-C", HERE, "rev-parse", "--show-toplevel"], text=True).strip()
    head = subprocess.check_output(["git", "-C", top, "rev-parse", "HEAD"], text=True).strip()
    rel = [os.path.relpath(os.path.join(HERE, f), top) for f in GUARD_FILES]
    por = subprocess.check_output(["git", "-C", top, "status", "--porcelain", "--"] + rel, text=True)
    return top, head, por


def git_guard():
    top, head, por = _git_state()
    if por.strip():
        raise NotCommitted("driver/test chua commit hoac da sua sau commit -> CAM push:\n%s" % por.rstrip())
    return {"git_top": top, "git_head": head, "driver_sha256": _sha256f(os.path.join(HERE, "f2b_driver.py"))}


# ---- N3: PARITY_OK kiem lai tu dia ----
def parity_ok(seed, why=None):
    """Dat <=> PARITY_OK_<seed>.json hop le VA printDone.csv cua f2b-nen-<seed> TREN DIA bam lai == md5 r1-a3-<seed>
    VA result.json tren dia: tag dung, jar_sha256 == r1-a3."""
    why = why if why is not None else []
    seed_ok(seed)
    p = parity_file(seed)
    if not os.path.exists(p):
        why.append("khong co %s" % p)
        return False
    j = _jload(p)
    ks = R.GA.ks_mod()
    want, rref = ref_md5(ks, seed)
    tag = tag_of(NEN, seed)
    d = out_dir(ks, tag)
    pd, rj = _find(d, "printDone.csv"), _find(d, "result.json")
    if j.get("seed") != seed or j.get("md5_ref") != want or j.get("md5_f2b") != want:
        why.append("noi dung PARITY_OK sai")
    if not pd or not rj:
        why.append("khong co printDone/result tren dia %s" % d)
        return False
    got = _md5f(pd)
    if got != want:
        why.append("md5 printDone tren dia %s != r1-a3 %s" % (got, want))
    res = _jload(rj)
    if res.get("tag") != tag:
        why.append("result.json tag %r != %s" % (res.get("tag"), tag))
    if res.get("jar_sha256") != rref.get("jar_sha256"):
        why.append("jar_sha256 %r != r1-a3" % res.get("jar_sha256"))
    if why:
        log.warning("PARITY_OK %s KHONG hop le: %s", seed, "; ".join(why))
        return False
    return True


def parity_compare(ks, seed, fr):
    """fr = ks.fetch(...) cua f2b-nen-<seed> (vua fetch). Dat -> ghi PARITY_OK_<seed>.json; lech -> ParityMismatch."""
    want, rref = ref_md5(ks, seed)
    res = fr.get("result") or {}
    got = (res.get("r1_a3") or {}).get("md5_printdone")
    filemd5 = _md5f(fr["print_done"]) if fr.get("print_done") else None
    tag = tag_of(NEN, seed)
    info = {"seed": seed, "tag": tag, "md5_ref": want, "md5_f2b": got, "md5_printdone_file": filemd5,
            "n_trades": res.get("n_trades"), "n_trades_ref": rref.get("n_trades"),
            "jar_sha256": res.get("jar_sha256"), "jar_sha256_ref": rref.get("jar_sha256"), "prereg": PREREG}
    log.info("PARITY %s", json.dumps(info))
    bad = []
    if res.get("tag") != tag:
        bad.append("result.json tag %r != %s" % (res.get("tag"), tag))
    if got != want:
        bad.append("md5 printDone %s != r1-a3 %s" % (got, want))
    if filemd5 != want:
        bad.append("md5 file printDone %s != r1-a3 %s" % (filemd5, want))
    if res.get("jar_sha256") != rref.get("jar_sha256"):
        bad.append("jar_sha256 %s != r1-a3 %s" % (res.get("jar_sha256"), rref.get("jar_sha256")))
    if bad:
        p = parity_file(seed)
        if os.path.exists(p):
            os.remove(p)
        raise ParityMismatch("PARITY_FAIL %s: %s" % (seed, "; ".join(bad)), bad)
    info["ts"] = time.time()
    with open(_state("PARITY_OK_%s.json" % seed), "w") as f:
        json.dump(info, f, indent=1)
    log.info("PARITY_OK %s md5=%s", seed, got)
    return True


# ---- push / fetch ----
def _push(b, allow_repush=False):
    """check_f2b -> chong push trung -> C1 git -> free_slots() -> kernels_push -> ghi dau (git HEAD + sha driver)."""
    check_f2b(b)
    if _marker(b["tag"]) and not allow_repush:
        raise AlreadyPushed("%s da push (%s); dung --repush neu that su can" % (b["tag"], pushed_file(b["tag"])))
    g = git_guard()
    ks = b["ks"]
    free = ks.free_slots()
    log.info("free_slots=%d", free)
    if free <= 0:
        raise NoSlot("FREE=0 -> DUNG, khong push %s" % b["tag"])
    r = ks._api().kernels_push(b["folder"])
    ver = getattr(r, "version_number", None) or getattr(r, "versionNumber", None)
    log.info("PUSHED %s -> %s version=%s", b["ref"], getattr(r, "url", r), ver)
    j = {"tag": b["tag"], "ref": b["ref"], "cell": b["cell"], "seed": b["seed"], "ts_push": time.time(),
         "version": ver, "overrides": b["cfg"]["overrides"], "extra_env": b["cfg"]["extra_env"], "prereg": PREREG}
    j.update(g)
    _save_marker(b["tag"], j)
    return b["ref"]


def _fresh_fetch(ks, tag):
    """N6: CHUYEN tuong minh out cu sang out/_stale/<slug>.<ts> (khong xoa) roi fetch MOI; kiem result.tag."""
    slug = ks.slug(tag)
    if not slug.startswith("f2b-"):
        raise F2BError("tu choi dung toi out dir khong phai f2b: %s" % slug)
    d = out_dir(ks, tag)
    if os.path.exists(d):
        st = os.path.join(ks.OUTDIR, "_stale")
        os.makedirs(st, exist_ok=True)
        dst = os.path.join(st, "%s.%d" % (slug, int(time.time() * 1000)))
        os.rename(d, dst)
        log.info("out cu %s -> %s", d, dst)
    fr = ks.fetch(tag)
    res = fr.get("result") or {}
    if res.get("tag") != tag:
        raise KernelError("fetch %s: result.json tag %r (thieu / khong phai lan chay nay)" % (tag, res.get("tag")))
    m = _marker(tag)
    if m is not None:
        m.update(ts_fetch=time.time(), ok=res.get("ok"), java_rc=res.get("java_rc"), n_trades=res.get("n_trades"),
                 equity_final=res.get("equity_final"), md5_printdone=(res.get("r1_a3") or {}).get("md5_printdone"))
        _save_marker(tag, m)
    return fr


def _status_of(ks, m):
    try:
        return ks._status(m["ref"])
    except Exception as e:  # noqa: BLE001
        return "STATUS_ERR %s" % e


TERMINAL_BAD = ("ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED")


def cmd_dry(cell, seed, smoke=False):
    b = build_f2b(seed, cell, smoke=smoke, write=False)
    check_f2b(b)
    log.info("DRY tag=%s ref=%s folder=%s", b["tag"], b["ref"], b["folder"])
    log.info("DRY cfg=%s", json.dumps(b["cfg"], indent=1, sort_keys=True))
    log.info("DRY kernel-metadata=%s", json.dumps(b["md"], indent=1))
    return b


def cmd_smoke(cell, seed, repush=False):
    if (cell, seed) != ("A10R1-S1", "A1"):
        log.warning("prereg muc 9 chi dinh smoke A10R1-S1 seed A1; dang dung %s %s", cell, seed)
    return _push(build_f2b(seed, cell, smoke=True), allow_repush=repush)


def cmd_push(cell, seed, repush=False):
    cell_ok(cell)
    seed_ok(seed)
    if cell == NEN:
        raise F2BError("NEN chi chay qua lenh parity")
    why = []
    if not parity_ok(seed, why):
        raise ParityMissing("chua co PARITY_OK hop le cho seed %s -> chan push: %s" % (seed, "; ".join(why)))
    return _push(build_f2b(seed, cell), allow_repush=repush)


def cmd_parity(seed, wait=False, repush=False):
    """MOT buoc (mac dinh khong cho). Khong bao gio dung lai out cu: COMPLETE -> chuyen out cu sang _stale + fetch moi."""
    seed_ok(seed)
    b = build_f2b(seed, NEN)
    ks, tag = b["ks"], b["tag"]
    m = _marker(tag)
    if m is None or repush:
        p = parity_file(seed)
        if os.path.exists(p):
            os.remove(p)
        _push(b, allow_repush=repush)
        if not wait:
            log.info("parity %s: da push %s; goi lai 'parity %s' khi kernel xong", seed, b["ref"], seed)
            return None
        m = _marker(tag)
    else:
        check_f2b(b)
    if wait:
        log.info("wait -> %s", ks.wait([m["ref"]]))
    st = _status_of(ks, m)
    log.info("parity %s: %s status=%s", seed, m["ref"], st)
    if st in TERMINAL_BAD or st.startswith("STATUS_ERR"):
        raise KernelError("kernel %s ket thuc %s -> bao MASTER (khong tu push lai)" % (m["ref"], st))
    if st != "COMPLETE":
        log.info("parity %s: chua xong (%s) -> goi lai sau", seed, st)
        return None
    fr = _fresh_fetch(ks, tag)
    return parity_compare(ks, seed, fr)


# ---- N1/N2: kiem smoke ----
RX_TSX = re.compile(r"\[TSX\] extHours=(-?\d+)")
RX_JAR = re.compile(r"JAR_SHA256=([0-9a-f]{64})")
RX_MAPPER = re.compile(r"Loaded Symbol Mapper: (\d+)")
PAT_PARSE_ERR = "SIM env override parse error"
PAT_TP = "TAKEPROFIT sym="
PAT_SL = "PREARM_SL sym="
PAT_HARD = "HARD SL"


def _log_files(d):
    """Moi file log trong out dir (*.log, sim.out); ban .gz chi lay khi chua co ban giai nen."""
    ok = lambda fn: fn.endswith(".log") or fn == "sim.out"  # noqa: E731
    out = []
    for root, _dirs, files in os.walk(d):
        for fn in files:
            if ok(fn) or (fn.endswith(".gz") and ok(fn[:-3]) and fn[:-3] not in files):
                out.append(os.path.join(root, fn))
    return sorted(out)


def scan_logs(paths):
    """Dem theo TUNG file (khong cong don giua file vi sim-<tag>.log co the lap lai stdout).
    Quy tac X14 (A1 N1): dem dong chua '[TSX] extHours=<so>' voi <so> > 0 (Java chi in dong nay khi EXT_HOURS > 0)."""
    per = {}
    for p in paths:
        c = {"parse_err": 0, "tp": 0, "prearm_sl": 0, "hard_sl": 0, "tsx_ext_pos": 0, "jar": set(), "mapper": []}
        op = gzip.open if p.endswith(".gz") else open
        with op(p, "rt", errors="replace") as f:
            for ln in f:
                if PAT_PARSE_ERR in ln:
                    c["parse_err"] += 1
                if PAT_TP in ln:
                    c["tp"] += 1
                if PAT_SL in ln:
                    c["prearm_sl"] += 1
                if PAT_HARD in ln:
                    c["hard_sl"] += 1
                for mm in RX_TSX.finditer(ln):
                    if int(mm.group(1)) > 0:
                        c["tsx_ext_pos"] += 1
                c["jar"].update(RX_JAR.findall(ln))
                c["mapper"].extend(int(x) for x in RX_MAPPER.findall(ln))
        per[p] = c
    return per


def scan_printdone(p, ntp=5):
    """(so dong level DCA_LEVEL*, 5 dong TAKE_PROFIT_DONE dau, dem status)."""
    dca, tps, st = 0, [], collections.Counter()
    with open(p, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            st[row.get("status")] += 1
            if (row.get("level") or "").startswith("DCA_LEVEL"):
                dca += 1
            if row.get("status") == "TAKE_PROFIT_DONE" and len(tps) < ntp:
                tps.append({k: row.get(k) for k in ("sym", "entry", "tp", "profit", "status", "level", "start", "end")})
    return dca, tps, st


def smoke_check(cell, fr, jar_ref):
    """Tra ve (fails, info). FAIL: parse error >= 1; JAR khac cc0f9d11/r1-a3 hoac khong thay; mapper < 800;
    leg DCA_LEVEL* trong printDone; (o co SL) 0 dong PREARM_SL; (o co TP) 0 dong TAKEPROFIT; (nhanh A) dong
    '[TSX] extHours=' > 0. In 5 dong TAKE_PROFIT_DONE (khong tu ket luan +TP%)."""
    c = CELLS[cell]
    res = fr.get("result") or {}
    per = scan_logs(_log_files(fr["dir"]))
    tot = lambda k: sum(v[k] for v in per.values())  # noqa: E731
    jars = set().union(*[v["jar"] for v in per.values()]) if per else set()
    if res.get("jar_sha256"):
        jars.add(res["jar_sha256"])
    mappers = [m for v in per.values() for m in v["mapper"]]
    if isinstance(res.get("symbol_mapper"), int):
        mappers.append(res["symbol_mapper"])
    fails = []
    if tot("parse_err") > 0:
        fails.append("co '%s' (%d)" % (PAT_PARSE_ERR, tot("parse_err")))
    if not jars:
        fails.append("khong thay JAR_SHA256")
    elif any(not j.startswith(JAR_SHA_PREFIX) or j != jar_ref for j in jars):
        fails.append("JAR_SHA256 %s != %s" % (sorted(jars), jar_ref))
    if not mappers:
        log.warning("SMOKE: khong thay so mapper (log / result.json)")
    elif min(mappers) < 800:
        fails.append("mapper %s < 800" % mappers)
    pd = fr.get("print_done")
    dca, tps, st = scan_printdone(pd) if pd else (None, [], {})
    if pd is None:
        fails.append("khong co printDone.csv")
    elif dca > 0:
        fails.append("printDone co %d leg DCA_LEVEL*" % dca)
    if "SIM_PRE_ARM_SL" in c.add and tot("prearm_sl") == 0:
        fails.append("0 dong '%s'" % PAT_SL)
    if "SIM_TAKE_PROFIT_RATE" in c.add and tot("tp") == 0:
        fails.append("0 dong '%s'" % PAT_TP)
    if set(X14_KEYS) <= set(c.drop) and tot("tsx_ext_pos") > 0:
        fails.append("nhanh A nhung co %d dong '[TSX] extHours=' > 0 (X14 con bat)" % tot("tsx_ext_pos"))
    info = {"per_file": {p: {k: (sorted(v) if isinstance(v, set) else v) for k, v in d.items()} for p, d in per.items()},
            "mapper": mappers, "jar": sorted(jars), "dca_legs": dca, "status_count": dict(st),
            "take_profit_done_first5": tps, "tp_rate": c.add.get("SIM_TAKE_PROFIT_RATE"),
            "hard_sl_lines": tot("hard_sl"), "tsx_ext_pos_lines": tot("tsx_ext_pos")}
    return fails, info


def cmd_fetch(cell, seed, smoke=False):
    tag = tag_of(cell, seed, smoke)
    ks = R.GA.ks_mod()
    fr = _fresh_fetch(ks, tag)
    res = fr.get("result") or {}
    log.info("FETCH %s dir=%s ok=%s java_rc=%s n_trades=%s equity_final=%s jar=%s mapper=%s md5_printdone=%s",
             tag, fr["dir"], res.get("ok"), res.get("java_rc"), res.get("n_trades"), res.get("equity_final"),
             str(res.get("jar_sha256"))[:16], res.get("symbol_mapper"), (res.get("r1_a3") or {}).get("md5_printdone"))
    if smoke:
        _, rref = ref_md5(ks, seed)
        fails, info = smoke_check(cell, fr, rref["jar_sha256"])
        for p, d in info["per_file"].items():
            log.info("SMOKE_FILE %s %s", p, json.dumps(d))
        log.info("SMOKE mapper=%s jar=%s dca_legs=%s status=%s HARD_SL_lines=%d TSX_extHours>0_lines=%d",
                 info["mapper"], info["jar"], info["dca_legs"], info["status_count"], info["hard_sl_lines"],
                 info["tsx_ext_pos_lines"])
        log.info("SMOKE 5 dong TAKE_PROFIT_DONE dau (cot profit, %%; nguoi doc doi chieu TP=%s):", info["tp_rate"])
        for r in info["take_profit_done_first5"]:
            log.info("  %s", json.dumps(r))
        if fails:
            raise SmokeFail("SMOKE_FAIL %s: %s" % (tag, "; ".join(fails)), fails)
        log.info("SMOKE_CHECKS_PASS %s (con doc tay: profit TP, HARD SL) - A1/MASTER phan xet", tag)
    return fr


# ---- N5: grid ----
def grid_order():
    """Thu tu CO DINH: bang prereg (CELLS, bo NEN) x seed (A1, S7)."""
    return [(c, s) for c in CELLS if c != NEN for s in SEEDS]


def _row_state(ks, tag, act):
    """Trang thai 1 o: CHUA_PUSH | DANG_CHAY | XONG | LOI | CHO_FETCH. act=True: COMPLETE chua fetch -> fetch moi."""
    m = _marker(tag)
    if m is None:
        return "CHUA_PUSH", None
    if m.get("error"):
        return "LOI", m
    if m.get("ts_fetch"):
        return ("XONG" if m.get("ok") and m.get("java_rc") == 0 else "LOI"), m
    st = _status_of(ks, m)
    if st == "COMPLETE":
        if not act:
            return "CHO_FETCH", m
        try:
            _fresh_fetch(ks, tag)
        except F2BError as e:
            m = _marker(tag)
            m["error"] = "fetch: %s" % e
            _save_marker(tag, m)
            return "LOI", m
        m = _marker(tag)
        return ("XONG" if m.get("ok") and m.get("java_rc") == 0 else "LOI"), m
    if st in TERMINAL_BAD:
        if act:
            m["error"] = st
            _save_marker(tag, m)
        return "LOI", m
    return "DANG_CHAY", m


def grid_round(max_slots=5, act=True):
    """MOT vong (khong lap, khong sleep). act=False (status): chi doc trang thai."""
    ks = R.GA.ks_mod()
    rows = collections.OrderedDict()
    for cell, seed in grid_order():
        tag = tag_of(cell, seed)
        rows[(cell, seed)] = [tag] + list(_row_state(ks, tag, act))
    nrun = sum(1 for r in rows.values() if r[1] == "DANG_CHAY")
    pushed = 0
    if act:
        for (cell, seed), r in rows.items():
            if r[1] != "CHUA_PUSH":
                continue
            if nrun >= max_slots:
                log.info("GRID: %d kernel f2b dang chay >= max_slots %d -> dung push", nrun, max_slots)
                break
            if not parity_ok(seed):
                continue
            try:
                _push(build_f2b(seed, cell))
            except NoSlot as e:
                log.info("GRID: %s", e)
                break
            r[1], r[2] = "DANG_CHAY", _marker(r[0])
            nrun += 1
            pushed += 1
    cnt = collections.Counter(r[1] for r in rows.values())
    log.info("GRID %-10s %-3s %-22s %-10s %-8s %s", "cell", "sd", "tag", "trang_thai", "n_trades", "equity_final / loi")
    for (cell, seed), (tag, st, m) in rows.items():
        m = m or {}
        log.info("GRID %-10s %-3s %-22s %-10s %-8s %s", cell, seed, tag, st, m.get("n_trades", "-"),
                 m.get("error") or m.get("equity_final", "-"))
    for s in SEEDS:
        log.info("GRID PARITY_OK %s: %s", s, parity_ok(s))
    sm = sorted(fn for fn in os.listdir(os.path.join(STATE_DIR, "pushed")) if fn.startswith("f2b-smk-")) \
        if os.path.isdir(os.path.join(STATE_DIR, "pushed")) else []
    log.info("GRID smoke da push: %s", sm or "-")
    log.info("GRID tong: %s; vong nay push %d", dict(cnt), pushed)
    if cnt.get("LOI"):
        log.warning("GRID co %d o LOI -> bao MASTER (driver KHONG tu push lai)", cnt["LOI"])
    return rows


def cmd_list():
    log.info("%-10s | %-62s | %-30s | %s", "cell", "overrides THEM", "BO", "extra_env")
    for n, c in CELLS.items():
        log.info("%-10s | %-62s | %-30s | %s", n, ",".join("%s=%s" % kv for kv in c.add.items()) or "-",
                 ",".join(c.drop) or "-", json.dumps(c.env) if c.env else "-")
    log.info("tong %d cau hinh (24 + NEN) x seed %s; prereg %s", len(CELLS), SEEDS, PREREG)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "dry", "smoke", "parity", "push", "status", "fetch", "grid"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--wait", action="store_true", help="parity: cho kernel xong (mac dinh KHONG cho)")
    ap.add_argument("--repush", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="fetch/dry tag smoke")
    ap.add_argument("--max-slots", type=int, default=5)
    a = ap.parse_args(argv)
    need = {"list": 0, "status": 0, "grid": 0, "parity": 1, "dry": 2, "smoke": 2, "push": 2, "fetch": 2}[a.cmd]
    if len(a.args) != need:
        log.error("lenh %s can %d tham so, nhan %s", a.cmd, need, a.args)
        return 2
    try:
        if a.cmd == "list":
            cmd_list()
        elif a.cmd == "status":
            grid_round(a.max_slots, act=False)
        elif a.cmd == "grid":
            grid_round(a.max_slots, act=True)
        elif a.cmd == "parity":
            cmd_parity(a.args[0], wait=a.wait, repush=a.repush)
        elif a.cmd == "dry":
            cmd_dry(a.args[0], a.args[1], smoke=a.smoke)
        elif a.cmd == "smoke":
            cmd_smoke(a.args[0], a.args[1], repush=a.repush)
        elif a.cmd == "push":
            cmd_push(a.args[0], a.args[1], repush=a.repush)
        else:
            cmd_fetch(a.args[0], a.args[1], smoke=a.smoke)
    except F2BError as e:
        log.error("DUNG: %s", e)
        return e.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
