#!/usr/bin/env python3
"""Unit test f2b_driver (KHONG mang). Chay: python3 -m unittest -v test_f2b_driver (trong research/r1_s1).
Bang ky vong GO TAY tu PREREG_FAMILY2B.md muc 4 (doc lap voi CELLS trong driver).
- a3_sha (bam 888MB bins) thay bang bins_sha256 ghi trong result.json run tham chieu r1-a3-<seed>.
- Moi ham mang cua kaggle_sim (_api, free_slots, _status, wait, fetch, submit) thay bang GIA LAP cuc bo (ghi nhan goi);
  fetch gia lap ghi file vao OUTDIR TAM (run tham chieu tsx-x14 / r1-a3 duoc symlink, chi doc).
- git: _git_state gia lap (sach / ban); 1 test goi git that (chi doc rev-parse / status).
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f2b_driver as F  # noqa: E402

R = F.R
KS = R.GA.ks_mod()
REAL_OUT = KS.OUTDIR
X14 = ("SIM_LOSER_TS_EXT_HOURS", "SIM_LOSER_TS_EXT_DAYS")
S2 = {"DCA_GRID_WEIGHTS": "1,0,0,0", "SIM_F_BASE": "0.0075"}
ENV = {"WFO_DISABLE_DCA": "1"}
WL_HAND = {"SIM_PRE_ARM_SL", "SIM_TAKE_PROFIT_RATE", "SIM_TAKE_PROFIT_ONLY", "DCA_GRID_WEIGHTS", "SIM_F_BASE"}

# ---- go tay tu prereg muc 4: ten -> (SIM_PRE_ARM_SL, SIM_TAKE_PROFIT_RATE, SIM_TAKE_PROFIT_ONLY, bo X14?) ----
EXPECT = {
    "A05R05": ("-0.05", "0.025", "true", True),
    "A05R1": ("-0.05", "0.05", "true", True),
    "A05R2": ("-0.05", "0.10", "true", True),
    "A10R05": ("-0.10", "0.05", "true", True),
    "A10R1": ("-0.10", "0.10", "true", True),
    "A10R2": ("-0.10", "0.20", "true", True),
    "A20R05": ("-0.20", "0.10", "true", True),
    "A20R1": ("-0.20", "0.20", "true", True),
    "A20R2": ("-0.20", "0.40", "true", True),
    "B05": ("-0.05", None, None, False),
    "B10": ("-0.10", None, None, False),
    "B20": ("-0.20", None, None, False),
}


def expected_add(name, sz):
    sl, tp, only, _ = EXPECT[name]
    d = {"SIM_PRE_ARM_SL": sl}
    if tp is not None:
        d["SIM_TAKE_PROFIT_RATE"] = tp
        d["SIM_TAKE_PROFIT_ONLY"] = only
    if sz == "S2":
        d.update(S2)
    return d


ALL = [n + "-" + s for n in EXPECT for s in ("S1", "S2")] + ["NEN"]


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def ref_res(seed):
    with open(os.path.join(REAL_OUT, "r1-a3-" + seed.lower(), "result.json")) as f:
        return json.load(f)


def ref_printdone(seed):
    return os.path.join(REAL_OUT, "r1-a3-" + seed.lower(), "storage", "printDone.csv")


class NetSpy(Exception):
    pass


class FakePush(object):
    def __init__(self, url):
        self.url = url
        self.version_number = 1


class Base(unittest.TestCase):
    """Moi test: OUTDIR / WORKDIR / STATE tam moi; ham mang gia lap; git sach (tru test git)."""

    def setUp(self):
        self.calls, self.pushes, self.free, self.status, self.fetch_src = [], [], 0, {}, {}
        self.saved = {nm: getattr(KS, nm) for nm in ("_api", "free_slots", "_status", "wait", "fetch", "submit")}
        self.saved.update(WORKDIR=KS.WORKDIR, OUTDIR=KS.OUTDIR, STATE=F.STATE_DIR, GIT=F._git_state)
        self.tmp = tempfile.mkdtemp(prefix="f2b_test_")
        KS.WORKDIR = os.path.join(self.tmp, "work")
        KS.OUTDIR = os.path.join(self.tmp, "out")
        os.makedirs(KS.WORKDIR)
        os.makedirs(KS.OUTDIR)
        for s in ("a1", "s7"):
            for t in ("tsx-x14-", "r1-a3-"):
                os.symlink(os.path.join(REAL_OUT, t + s), os.path.join(KS.OUTDIR, t + s))
        F.STATE_DIR = os.path.join(self.tmp, "state")
        F._A3_SHA["v"] = ref_res("A1")["r1_a3"]["bins_sha256"]
        F._git_state = lambda: ("/top", "a" * 40, "")
        me = self

        class Api(object):
            def kernels_push(self, folder):
                me.calls.append("kernels_push")
                me.pushes.append(os.path.basename(folder))
                return FakePush(folder)

        def _api():
            me.calls.append("_api")
            return Api()

        def free_slots():
            me.calls.append("free_slots")
            return me.free

        def _status(ref):
            me.calls.append("_status")
            return me.status.get(ref, "RUNNING")

        def wait(refs, **k):
            me.calls.append("wait")
            return {r: "COMPLETE" for r in refs}

        def fetch(tag, out_dir=None):
            me.calls.append("fetch")
            dest = os.path.join(KS.OUTDIR, KS.slug(tag))
            os.makedirs(dest, exist_ok=True)
            me.fetch_src[tag](dest)
            pd = os.path.join(dest, "storage", "printDone.csv")
            rj = os.path.join(dest, "result.json")
            return {"ref": KS.kernel_ref(tag), "dir": dest, "print_done": pd if os.path.exists(pd) else None,
                    "sim_out": None, "result": json.load(open(rj)) if os.path.exists(rj) else None, "log": None}

        def submit(*a, **k):
            me.calls.append("submit")
            raise NetSpy("submit")
        for nm, fn in (("_api", _api), ("free_slots", free_slots), ("_status", _status), ("wait", wait),
                       ("fetch", fetch), ("submit", submit)):
            setattr(KS, nm, fn)

    def tearDown(self):
        for nm in ("_api", "free_slots", "_status", "wait", "fetch", "submit"):
            setattr(KS, nm, self.saved[nm])
        KS.WORKDIR, KS.OUTDIR = self.saved["WORKDIR"], self.saved["OUTDIR"]
        F.STATE_DIR, F._git_state = self.saved["STATE"], self.saved["GIT"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- output gia lap ---
    def nen_src(self, seed, printdone=None, jar=None, tag=None):
        """Ghi output parity: printDone (mac dinh = ban that r1-a3) + result.json."""
        def w(dest):
            os.makedirs(os.path.join(dest, "storage"), exist_ok=True)
            pd = os.path.join(dest, "storage", "printDone.csv")
            if printdone is None:
                shutil.copyfile(ref_printdone(seed), pd)
            else:
                with open(pd, "w") as f:
                    f.write(printdone)
            rr = ref_res(seed)
            res = {"tag": tag or F.tag_of("NEN", seed), "ok": True, "java_rc": 0, "n_trades": rr["n_trades"],
                   "jar_sha256": jar or rr["jar_sha256"], "r1_a3": {"md5_printdone": md5f(pd)}}
            with open(os.path.join(dest, "result.json"), "w") as f:
                json.dump(res, f)
        return w

    def make_parity(self, seed):
        """Tao PARITY_OK hop le cho seed qua duong that (push -> COMPLETE -> fetch -> so)."""
        self.free = 5
        tag = F.tag_of("NEN", seed)
        self.fetch_src[tag] = self.nen_src(seed)
        F.cmd_parity(seed)
        self.status[KS.kernel_ref(tag)] = "COMPLETE"
        self.assertTrue(F.cmd_parity(seed))
        self.assertTrue(F.parity_ok(seed))
        del self.calls[:], self.pushes[:]
        self.free = 0


class TestTable(Base):
    def test_25_cells_exact_prereg(self):
        self.assertEqual(sorted(F.CELLS), sorted(ALL))
        for n in EXPECT:
            for sz in ("S1", "S2"):
                c = F.CELLS[n + "-" + sz]
                self.assertEqual(c.add, expected_add(n, sz), n + "-" + sz)
                self.assertEqual(set(c.drop), set(X14) if EXPECT[n][3] else set(), n)
                self.assertEqual(c.env, ENV, n)
        self.assertEqual((F.CELLS["NEN"].add, F.CELLS["NEN"].drop, F.CELLS["NEN"].env), ({}, (), {}))

    def test_overrides_built_each_cell_each_seed(self):
        for seed in ("A1", "S7"):
            for cell in ALL:
                b = F.build_f2b(seed, cell, write=False)
                ov = b["cfg"]["overrides"]
                if cell == "NEN":
                    self.assertEqual(ov, dict(R.OV))
                    continue
                n, sz = cell.rsplit("-", 1)
                exp = {k: v for k, v in R.OV.items() if not (EXPECT[n][3] and k in X14)}
                exp.update(expected_add(n, sz))
                self.assertEqual(ov, exp, (seed, cell))
                self.assertEqual(b["cfg"]["extra_env"], ENV)
                self.assertEqual(b["tag"], "f2b-%s-%s" % (cell, seed.lower()))
                F.check_f2b(b)
        self.assertEqual(self.calls, [])

    def test_A_no_x14_B_keeps_x14(self):
        for cell in ALL:
            ov = F.build_f2b("A1", cell, write=False)["cfg"]["overrides"]
            for k in X14:
                if cell.startswith("A"):
                    self.assertNotIn(k, ov, cell)
                else:
                    self.assertEqual(ov[k], R.OV[k], cell)

    def test_no_dca_grid_enabled(self):
        for cell in ALL:
            b = F.build_f2b("S7", cell, write=False)
            self.assertNotIn("DCA_GRID_ENABLED", b["cfg"]["overrides"])
            self.assertNotIn("DCA_GRID_ENABLED", b["cfg"]["extra_env"])


class TestNen(Base):
    def test_nen_bytes_equal_r1a3(self):
        for seed in ("A1", "S7"):
            b = F.build_f2b(seed, "NEN", write=False)
            self.assertEqual(json.dumps(b["cfg"]["overrides"]), json.dumps(b["base_cfg"]["overrides"]))
            self.assertEqual(json.dumps(R.OV), json.dumps(b["cfg"]["overrides"]))
            self.assertEqual(json.dumps(b["cfg"]), json.dumps(dict(b["base_cfg"], tag=b["tag"])))
            t0, t1 = '"tag": "r1-a3-%s"' % seed.lower(), '"tag": "f2b-nen-%s"' % seed.lower()
            self.assertEqual(b["code"], b["base_code"].replace(t0, t1))
            stored = os.path.join(self.saved["WORKDIR"], "r1-a3-" + seed.lower())  # ban da push that (chi doc)
            with open(os.path.join(stored, "run.py")) as f:
                self.assertEqual(b["code"], f.read().replace(t0, t1), seed)
            with open(os.path.join(stored, "kernel-metadata.json")) as f:
                md0 = json.load(f)
            self.assertEqual({k: v for k, v in b["md"].items() if k not in ("id", "title")},
                             {k: v for k, v in md0.items() if k not in ("id", "title")})
            self.assertEqual(b["md"]["id"], "chuyendinh/sim-f2b-nen-" + seed.lower())


class TestGuards(Base):
    def _b(self, cell="A10R1-S2", seed="A1"):
        return F.build_f2b(seed, cell, write=False)

    def test_whitelist_exact(self):
        self.assertEqual(set(F.WL_ADD), WL_HAND)
        self.assertEqual(set(F.WL_ENV), {"WFO_DISABLE_DCA"})

    def test_whitelist_catches_dca_grid_scale_specifically(self):
        b = self._b()
        b["cfg"]["overrides"]["DCA_GRID_SCALE"] = "3.0"
        with self.assertRaises(F.F2BError) as cm:
            F.check_f2b(b)
        self.assertTrue(any(e.startswith("(b) key them ngoai whitelist") and "DCA_GRID_SCALE" in e
                            for e in cm.exception.errs), cm.exception.errs)

    def test_whitelist_blocks_foreign_override(self):
        for k in ("SIM_FOO", "DCA_GRID_ENABLED"):
            b = self._b()
            b["cfg"]["overrides"][k] = "1"
            with self.assertRaises(F.F2BError, msg=k):
                F.check_f2b(b)

    def test_changed_r1a3_value_blocked(self):
        b = self._b("B10-S1")
        b["cfg"]["overrides"]["SELECTOR_RANK_TOPK"] = 25
        with self.assertRaises(F.F2BError):
            F.check_f2b(b)

    def test_extra_env_whitelist(self):
        b = self._b()
        b["cfg"]["extra_env"]["HOLDOUT_UNSEAL"] = "1"
        with self.assertRaises(F.F2BError):
            F.check_f2b(b)

    def test_jar_and_end_date(self):
        b = self._b()
        b["cfg"]["jar_ds"] = "sim-jar-tpsl"
        with self.assertRaises(F.F2BError):
            F.check_f2b(b)
        b = self._b()
        b["cfg"]["sim_end_date"] = "20260131"
        with self.assertRaises(F.F2BError):
            F.check_f2b(b)

    def test_end_date_never_past_2025(self):
        for seed in ("A1", "S7"):
            for cell in ALL:
                e = F.build_f2b(seed, cell, write=False)["cfg"]["sim_end_date"]
                self.assertEqual(e, "20251231")
        orig = R.build

        def bad(seed, arm="A3"):
            ks, folder, ref, cfg = orig(seed, arm)
            cfg["sim_end_date"] = "20260101"
            return ks, folder, ref, cfg
        R.build = bad
        try:
            with self.assertRaises(F.F2BError):
                F.build_f2b("A1", "NEN", write=False)
        finally:
            R.build = orig

    def test_bad_seed_rejected(self):
        for s in ("S13", "a1", "42", "S2024", ""):
            for fn in (lambda: F.tag_of("A10R1-S1", s), lambda: F.build_f2b(s, "A10R1-S1", write=False),
                       lambda: F.cmd_push("A10R1-S1", s), lambda: F.cmd_parity(s)):
                with self.assertRaises(F.F2BError, msg=s):
                    fn()
        self.assertEqual(F.main(["push", "A10R1-S1", "S13"]), 2)
        self.assertEqual(F.main(["dry", "A99R1-S1", "A1"]), 2)
        self.assertEqual(self.calls, [])

    def test_dry_no_network_no_write(self):
        for cell in ("A10R1-S1", "B20-S2", "NEN"):
            F.cmd_dry(cell, "S7")
        self.assertEqual(F.main(["dry", "A05R05-S2", "A1"]), 0)
        self.assertEqual(F.main(["list"]), 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(os.listdir(KS.WORKDIR), [])
        self.assertFalse(os.path.exists(F.STATE_DIR))

    def test_smoke_tag_distinct(self):
        self.assertEqual(F.tag_of("A10R1-S1", "A1", smoke=True), "f2b-smk-A10R1-S1-a1")
        self.assertEqual(F.tag_of("NEN", "S7"), "f2b-nen-s7")
        with self.assertRaises(F.F2BError):
            F.tag_of("NEN", "A1", smoke=True)


class TestGitC1(Base):
    def test_dirty_refuses_push(self):
        self.free = 5
        for por in (" M research/r1_s1/f2b_driver.py\n", "?? research/r1_s1/test_f2b_driver.py\n"):
            F._git_state = lambda por=por: ("/top", "a" * 40, por)
            with self.assertRaises(F.NotCommitted):
                F.cmd_smoke("A10R1-S1", "A1")
        self.assertNotIn("kernels_push", self.calls)
        self.assertNotIn("free_slots", self.calls)

    def test_marker_records_git_and_sha(self):
        self.free = 5
        F.cmd_smoke("A10R1-S1", "A1")
        m = F._marker("f2b-smk-A10R1-S1-a1")
        self.assertEqual(m["git_head"], "a" * 40)
        self.assertEqual(m["driver_sha256"], hashlib.sha256(open(os.path.join(HERE, "f2b_driver.py"), "rb").read()).hexdigest())
        self.assertEqual(self.pushes, ["f2b-smk-a10r1-s1-a1"])
        self.assertEqual(self.calls.index("free_slots") < self.calls.index("kernels_push"), True)
        with self.assertRaises(F.AlreadyPushed):
            F.cmd_smoke("A10R1-S1", "A1")

    def test_real_git_state_readonly(self):
        F._git_state = self.saved["GIT"]
        top, head, por = F._git_state()
        self.assertTrue(re.match(r"^[0-9a-f]{40}$", head))
        self.assertTrue(os.path.isdir(os.path.join(top, ".git")) or os.path.isfile(os.path.join(top, ".git")))


class TestParity(Base):
    def test_push_blocked_without_parity(self):
        with self.assertRaises(F.ParityMissing):
            F.cmd_push("A10R1-S1", "A1")
        self.assertEqual(F.main(["push", "A10R1-S1", "A1"]), 5)
        os.makedirs(F.STATE_DIR)
        want = ref_res("A1")["r1_a3"]["md5_printdone"]
        with open(F.parity_file("A1"), "w") as f:  # file dau "dung" nhung KHONG co output tren dia
            json.dump({"seed": "A1", "md5_ref": want, "md5_f2b": want}, f)
        with self.assertRaises(F.ParityMissing):
            F.cmd_push("A10R1-S1", "A1")
        with self.assertRaises(F.ParityMissing):
            F.cmd_push("A10R1-S1", "S7")
        self.assertEqual(self.calls, [])
        with self.assertRaises(F.F2BError):
            F.cmd_push("NEN", "A1")

    def test_ref_printdone_on_disk_matches_ref_md5(self):
        for s in ("A1", "S7"):
            self.assertEqual(md5f(ref_printdone(s)), ref_res(s)["r1_a3"]["md5_printdone"])

    def test_parity_default_no_wait_then_complete(self):
        self.free = 5
        tag = "f2b-nen-a1"
        ref = KS.kernel_ref(tag)
        self.fetch_src[tag] = self.nen_src("A1")
        self.assertIsNone(F.cmd_parity("A1"))                     # buoc 1: push, KHONG cho
        self.assertEqual(self.pushes, ["f2b-nen-a1"])
        self.assertNotIn("wait", self.calls)
        self.assertIsNone(F.cmd_parity("A1"))                     # buoc 2: RUNNING -> chua fetch
        self.assertNotIn("fetch", self.calls)
        self.assertEqual(self.pushes, ["f2b-nen-a1"])             # khong push lai
        self.status[ref] = "COMPLETE"
        self.assertTrue(F.cmd_parity("A1"))                       # buoc 3: fetch + so
        self.assertEqual(self.calls.count("fetch"), 1)
        self.assertTrue(F.parity_ok("A1"))
        self.assertNotIn("wait", self.calls)
        self.free = 0
        with self.assertRaises(F.NoSlot):                         # parity dat -> push luoi toi free_slots
            F.cmd_push("A10R1-S1", "A1")

    def test_parity_wait_flag(self):
        self.free = 5
        self.fetch_src["f2b-nen-s7"] = self.nen_src("S7")
        self.status[KS.kernel_ref("f2b-nen-s7")] = "COMPLETE"
        self.assertTrue(F.cmd_parity("S7", wait=True))
        self.assertIn("wait", self.calls)

    def test_parity_stale_result_not_reused(self):
        """N6: out cu DUNG md5 nam san tren dia; kernel moi tra printDone lech -> phai LECH (khong doc out cu)."""
        self.free = 5
        tag = "f2b-nen-a1"
        d = os.path.join(KS.OUTDIR, tag)
        self.nen_src("A1")(d)                                      # out cu (tu lan chay khac) - dung md5
        self.fetch_src[tag] = self.nen_src("A1", printdone="sym,status\nX,Y\n")
        F.cmd_parity("A1")
        self.status[KS.kernel_ref(tag)] = "COMPLETE"
        with self.assertRaises(F.ParityMismatch):
            F.cmd_parity("A1")
        self.assertFalse(F.parity_ok("A1"))
        self.assertEqual(len(os.listdir(os.path.join(KS.OUTDIR, "_stale"))), 1)  # out cu duoc chuyen tuong minh
        self.assertEqual(F.main(["parity", "A1"]), 3)

    def test_parity_wrong_tag_in_result(self):
        self.free = 5
        tag = "f2b-nen-a1"
        self.fetch_src[tag] = self.nen_src("A1", tag="r1-a3-a1")
        F.cmd_parity("A1")
        self.status[KS.kernel_ref(tag)] = "COMPLETE"
        with self.assertRaises(F.KernelError):
            F.cmd_parity("A1")

    def test_parity_kernel_error(self):
        self.free = 5
        self.fetch_src["f2b-nen-a1"] = self.nen_src("A1")
        F.cmd_parity("A1")
        self.status[KS.kernel_ref("f2b-nen-a1")] = "ERROR"
        self.assertEqual(F.main(["parity", "A1"]), 7)
        self.assertEqual(self.pushes, ["f2b-nen-a1"])

    def test_parity_compare_jar_mismatch_caught(self):
        """Mutant M17: bo so jar_sha256 -> test nay phai do."""
        want = ref_res("S7")["r1_a3"]["md5_printdone"]
        fr = {"result": {"tag": "f2b-nen-s7", "r1_a3": {"md5_printdone": want}, "jar_sha256": "0" * 64},
              "print_done": ref_printdone("S7")}
        with self.assertRaises(F.ParityMismatch) as cm:
            F.parity_compare(KS, "S7", fr)
        self.assertTrue(any("jar_sha256" in e for e in cm.exception.errs), cm.exception.errs)
        self.assertEqual(len(cm.exception.errs), 1)
        fr["result"]["jar_sha256"] = ref_res("S7")["jar_sha256"]
        self.assertTrue(F.parity_compare(KS, "S7", fr))

    def test_parity_ok_rehashes_disk(self):
        """N3: file dau hop le nhung printDone / jar tren dia bi doi -> KHONG hop le."""
        self.make_parity("A1")
        pd = os.path.join(KS.OUTDIR, "f2b-nen-a1", "storage", "printDone.csv")
        with open(pd, "a") as f:
            f.write("\n")
        why = []
        self.assertFalse(F.parity_ok("A1", why))
        self.assertTrue(any("md5 printDone tren dia" in w for w in why), why)
        with self.assertRaises(F.ParityMissing):
            F.cmd_push("A10R1-S1", "A1")
        self.make_parity("S7")
        rj = os.path.join(KS.OUTDIR, "f2b-nen-s7", "result.json")
        res = json.load(open(rj))
        res["jar_sha256"] = "1" * 64
        json.dump(res, open(rj, "w"))
        self.assertFalse(F.parity_ok("S7"))


class TestSmoke(Base):
    JAR = None

    def mk(self, cell, logs, pd_rows, mapper=863):
        d = os.path.join(self.tmp, "smk_" + cell)
        os.makedirs(os.path.join(d, "logs"))
        os.makedirs(os.path.join(d, "storage"))
        for name, lines in logs.items():
            with open(os.path.join(d, name), "w") as f:
                f.write("\n".join(lines) + "\n")
        pd = os.path.join(d, "storage", "printDone.csv")
        with open(pd, "w") as f:
            f.write("sym,side,entry,tp,profit,status,start,time_start_format,end,level\n")
            for r in pd_rows:
                f.write(r + "\n")
        return {"dir": d, "print_done": pd, "result": {"jar_sha256": ref_res("A1")["jar_sha256"], "symbol_mapper": mapper}}

    def good(self, cell="A10R1-S1", extra_logs=None, rows=None, mapper=863):
        jar = ref_res("A1")["jar_sha256"]
        logs = {"logs/full.log": ["x PREARM_SL sym=AAA", "x TAKEPROFIT sym=BBB", "Loaded Symbol Mapper: 863 symbols",
                                  "DumpConfig HARD SL -10.00%"],
                "sim-f2b-smk-a10r1-s1-a1.log": ['{"data":"INFO JAR_SHA256=%s"}' % jar]}
        for k, v in (extra_logs or {}).items():
            logs.setdefault(k, []).extend(v)
        rows = rows if rows is not None else [
            "AAA,BUY,1.0,0.9,-10.0,STOP_LOSS_DONE,s,t,e,PREDICT_SYMBOL_TRADE",
            "BBB,BUY,1.0,1.1,10.0,TAKE_PROFIT_DONE,s,t,e,PREDICT_SYMBOL_TRADE"]
        return self.mk(cell + str(len(os.listdir(self.tmp))), logs, rows, mapper)

    def check(self, fr, cell="A10R1-S1"):
        return F.smoke_check(cell, fr, ref_res("A1")["jar_sha256"])

    def test_good_passes_and_reports(self):
        fails, info = self.check(self.good())
        self.assertEqual(fails, [])
        self.assertEqual(info["take_profit_done_first5"][0]["profit"], "10.0")
        self.assertEqual(info["hard_sl_lines"], 1)
        self.assertEqual(info["tsx_ext_pos_lines"], 0)
        self.assertEqual(info["dca_legs"], 0)

    def test_each_failure_signal(self):
        cases = {
            "parse": dict(extra_logs={"logs/full.log": ["SIM env override parse error: x"]}),
            "jar": dict(extra_logs={"logs/sim.out": ["JAR_SHA256=" + "f" * 64]}),
            "mapper": dict(mapper=500),
            "dca": dict(rows=["AAA,BUY,1,1,1,STOP_MARKET_DONE,s,t,e,DCA_LEVEL1",
                              "BBB,BUY,1.0,1.1,10.0,TAKE_PROFIT_DONE,s,t,e,PREDICT_SYMBOL_TRADE"]),
            "x14": dict(extra_logs={"logs/full.log": ["[TSX] extHours=336 extDays=214 deferTicks=5"]}),
        }
        for name, kw in cases.items():
            fails, _ = self.check(self.good(**kw))
            self.assertTrue(fails, name)
        # thieu TAKEPROFIT / PREARM_SL
        for drop in ("TAKEPROFIT sym=", "PREARM_SL sym="):
            fr = self.good()
            p = os.path.join(fr["dir"], "logs", "full.log")
            txt = open(p).read().replace(drop, "zz")
            open(p, "w").write(txt)
            fails, _ = self.check(fr)
            self.assertTrue(any(drop in f for f in fails), (drop, fails))

    def test_tsx_zero_not_counted_and_branch_b(self):
        fails, info = self.check(self.good(extra_logs={"logs/full.log": ["[TSX] extHours=0 extDays=0"]}))
        self.assertEqual(fails, [])
        fr = self.good(cell="B10-S1", extra_logs={"logs/full.log": ["[TSX] extHours=336 extDays=214"]},
                       rows=["AAA,BUY,1.0,0.9,-10.0,STOP_LOSS_DONE,s,t,e,PREDICT_SYMBOL_TRADE"])
        p = os.path.join(fr["dir"], "logs", "full.log")
        with open(p) as f:
            txt = f.read().replace("TAKEPROFIT sym=", "zz")
        with open(p, "w") as f:
            f.write(txt)
        fails, info = self.check(fr, "B10-S1")
        self.assertEqual(fails, [])                     # nhanh B: X14 giu, khong can TP
        self.assertEqual(info["tsx_ext_pos_lines"], 1)

    def test_fetch_smoke_cli_exit6(self):
        tag = "f2b-smk-A10R1-S1-a1"
        bad = self.good(extra_logs={"logs/full.log": ["SIM env override parse error"]})

        def src(dest):
            shutil.copytree(bad["dir"], dest, dirs_exist_ok=True)
            with open(os.path.join(dest, "result.json"), "w") as f:
                json.dump(dict(bad["result"], tag=tag, ok=True, java_rc=0), f)
        self.fetch_src[tag] = src
        self.assertEqual(F.main(["fetch", "A10R1-S1", "A1", "--smoke"]), 6)


class TestGrid(Base):
    def test_order_fixed(self):
        o = F.grid_order()
        self.assertEqual(len(o), 48)
        self.assertEqual(o[:4], [("A05R05-S1", "A1"), ("A05R05-S1", "S7"), ("A05R05-S2", "A1"), ("A05R05-S2", "S7")])
        self.assertEqual(o[-1], ("B20-S2", "S7"))

    def test_status_readonly(self):
        rows = F.grid_round(act=False)
        self.assertEqual(len(rows), 48)
        self.assertTrue(all(r[1] == "CHUA_PUSH" for r in rows.values()))
        self.assertNotIn("kernels_push", self.calls)
        self.assertNotIn("fetch", self.calls)
        self.assertEqual(F.main(["status"]), 0)

    def test_grid_rounds(self):
        self.make_parity("A1")                                   # chi A1 co parity -> S7 khong push
        self.free = 3
        F.grid_round(max_slots=2)
        self.assertEqual(self.pushes, ["f2b-a05r05-s1-a1", "f2b-a05r05-s2-a1"])
        # vong 2: o 1 COMPLETE (fetch), o 2 ERROR (ghi nhan, KHONG push lai) -> push 2 o ke tiep
        for t in ("f2b-A05R05-S1-a1",):
            self.status[KS.kernel_ref(t)] = "COMPLETE"
            self.fetch_src[t] = lambda dest, t=t: json.dump({"tag": t, "ok": True, "java_rc": 0, "n_trades": 7,
                                                             "equity_final": 1.0}, open(os.path.join(dest, "result.json"), "w"))
        self.status[KS.kernel_ref("f2b-A05R05-S2-a1")] = "ERROR"
        del self.pushes[:]
        rows = F.grid_round(max_slots=2)
        self.assertEqual(rows[("A05R05-S1", "A1")][1], "XONG")
        self.assertEqual(rows[("A05R05-S2", "A1")][1], "LOI")
        self.assertEqual(rows[("A05R05-S1", "S7")][1], "CHUA_PUSH")
        self.assertEqual(self.pushes, ["f2b-a05r1-s1-a1", "f2b-a05r1-s2-a1"])
        # vong 3: FREE=0 -> khong push; o LOI van LOI
        self.free = 0
        del self.pushes[:]
        rows = F.grid_round(max_slots=5)
        self.assertEqual(self.pushes, [])
        self.assertEqual(rows[("A05R05-S2", "A1")][1], "LOI")
        self.assertEqual(self.calls.count("fetch"), 1)           # chi o XONG 1 lan (vong 2), khong fetch lai

    def test_grid_cli_one_round(self):
        self.assertEqual(F.main(["grid", "--max-slots", "1"]), 0)
        self.assertEqual(self.pushes, [])                        # chua parity -> khong push


if __name__ == "__main__":
    unittest.main(verbosity=2)
