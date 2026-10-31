#!/usr/bin/env python3
"""fix_mapper_dirty_242.py — go DUNG 3 muc test ABCUSDT/ZZZUSDT/XUSDT khoi ticker.symbol_mapper.global_id_map (242).
Chay tren ORACLE (goi tu fix_mapper_dirty_242.sh). KHONG dung planRepair (no doi id ca 2 symbol).
  check                      CHI DOC: gen, n, id trung, ke hoach go
  apply <backup.json>        GHI: can CONFIRM=YES; backup (dinh dang SymbolMapperRepairTool) -> 1 lenh CAS(gen) go dung cac key
                             -> doc lai, verify; verify FAIL => tu khoi phuc tu backup (exit 2)
  restore <backup.json>      GHI: can CONFIRM=YES; tra lai cac key co trong backup ma thieu/khac (CAS gen) -> verify
  selftest                   khong I/O
Ma thoat: 0 OK | 1 dung, khong doi gi | 2 da doi va loi/khoi phuc (bao MASTER) | 3 check thay id trung."""
import sys, os, json

NS, SET, KEY, BIN = "ticker", "symbol_mapper", "global_id_map", "data"
HOST = ("103.157.218.242", 3222)
REMOVE = {"ABCUSDT": 2, "ZZZUSDT": 3, "XUSDT": 1}      # muc do test ghi (khong co tren san, khong co kline/price)
KEEP = {"BTCUSDT": 1, "ETHUSDT": 2, "BNBUSDT": 3}


def dups(m):
    inv = {}
    for s, i in m.items():
        inv.setdefault(i, []).append(s)
    return {i: sorted(v) for i, v in inv.items() if len(v) > 1}


def plan_remove(m):
    """-> (keys can go, loi). Chi go key test co id dung nhu ky vong; moi nhom trung phai dung {KEEP, REMOVE}."""
    errs = []
    for s, i in KEEP.items():
        if m.get(s) != i:
            errs.append("KEEP %s=%s (can %d)" % (s, m.get(s), i))
    keys = []
    for s, i in REMOVE.items():
        if s in m:
            if m[s] != i:
                errs.append("REMOVE %s=%s (ky vong %d) — khong go" % (s, m[s], i))
            else:
                keys.append(s)
    allowed = {i: sorted([k for k, v in KEEP.items() if v == i] + [k for k, v in REMOVE.items() if v == i]) for i in KEEP.values()}
    for i, v in dups(m).items():
        if i not in allowed or not set(v) <= set(allowed[i]):
            errs.append("id trung LA %d=%s (khong thuoc 3 muc test) — dung, bao MASTER" % (i, v))
    return keys, errs


def verify(before, after, removed):
    errs = []
    for s in removed:
        if s in after:
            errs.append("%s van con" % s)
    for s, i in KEEP.items():
        if after.get(s) != i:
            errs.append("KEEP %s=%s" % (s, after.get(s)))
    for s, i in before.items():
        if s in removed:
            continue
        if after.get(s) != i:
            errs.append("doi/thieu %s: %s -> %s" % (s, i, after.get(s)))
    new = sorted(set(after) - set(before))
    if dups(after):
        errs.append("con id trung %s" % dups(after))
    return errs, new


def to_json(m, gen):
    return json.dumps({"generation": gen, "map": dict(sorted(m.items()))}, separators=(",", ":")) + "\n"


def client():
    import aerospike
    return aerospike, aerospike.client({"hosts": [HOST], "policies": {"timeout": 10000}}).connect()


def read(c):
    _, meta, b = c.get((NS, SET, KEY))
    return int(meta["gen"]), {str(k): int(v) for k, v in b[BIN].items()}


def put_back(aerospike, c, items, gen):
    from aerospike_helpers.operations import map_operations as mo
    c.operate((NS, SET, KEY), [mo.map_put_items(BIN, items)], meta={"gen": gen}, policy={"gen": aerospike.POLICY_GEN_EQ})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "selftest":
        return selftest()
    aerospike, c = client()
    gen, m = read(c)
    keys, errs = plan_remove(m)
    print("[MAPPER-FIX] gen=%d n=%d maxId=%d idTrung=%s" % (gen, len(m), max(m.values()), dups(m)))
    print("[MAPPER-FIX] ke hoach go: %s | loi: %s" % ({k: m[k] for k in keys}, errs or "khong"))
    if mode == "check":
        return 3 if dups(m) else 0
    if os.environ.get("CONFIRM") != "YES":
        print("DUNG: can CONFIRM=YES"); return 1
    bak = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == "apply":
        if errs:
            print("DUNG (khong doi gi): %s" % errs); return 1
        if not keys:
            print("Khong co gi de go (da sach?)"); return 0
        if not bak or os.path.exists(bak):
            print("DUNG: can duong dan backup CHUA ton tai: %s" % bak); return 1
        with open(bak, "w") as f:
            f.write(to_json(m, gen)); f.flush(); os.fsync(f.fileno())
        print("[MAPPER-FIX] backup %s (n=%d gen=%d)" % (bak, len(m), gen))
        from aerospike_helpers.operations import map_operations as mo
        try:
            c.operate((NS, SET, KEY), [mo.map_remove_by_key_list(BIN, keys, aerospike.MAP_RETURN_KEY_VALUE)],
                      meta={"gen": gen}, policy={"gen": aerospike.POLICY_GEN_EQ})
        except aerospike.exception.RecordGenerationError:
            print("DUNG (khong doi gi): record bi ghi chen (gen doi) — chay lai sau 1 phut"); return 1
        gen2, m2 = read(c)
        verr, new = verify(m, m2, keys)
        print("[MAPPER-FIX] sau: gen=%d n=%d (truoc %d) idTrung=%s symbol_moi_trong_luc=%s" % (gen2, len(m2), len(m), dups(m2), new))
        if verr:
            print("VERIFY FAIL %s — TU KHOI PHUC tu backup" % verr)
            put_back(aerospike, c, {k: m[k] for k in m if m2.get(k) != m[k]}, gen2)
            gen3, m3 = read(c)
            ok = all(m3.get(k) == v for k, v in m.items())
            print("[MAPPER-FIX] khoi phuc %s gen=%d" % ("OK" if ok else "LOI", gen3))
            return 2
        print("[MAPPER-FIX] OK: go %s; BTC=1 ETH=2 BNB=3; %d id khac giu nguyen; 0 id trung." % (keys, len(m2) - 3))
        return 0
    if mode == "restore":
        if not bak or not os.path.isfile(bak):
            print("DUNG: khong co backup %s" % bak); return 1
        b = {str(k): int(v) for k, v in json.load(open(bak))["map"].items()}
        items = {k: v for k, v in b.items() if m.get(k) != v}
        print("[MAPPER-RESTORE] tra lai %s" % items)
        if not items:
            return 0
        clash = {k: v for k, v in m.items() if k not in b and v in items.values()}
        if clash:
            print("DUNG: tra lai se trung id voi symbol moi %s" % clash); return 1
        try:
            put_back(aerospike, c, items, gen)
        except aerospike.exception.RecordGenerationError:
            print("DUNG: gen doi — chay lai"); return 1
        gen2, m2 = read(c)
        ok = all(m2.get(k) == v for k, v in items.items())
        print("[MAPPER-RESTORE] %s gen=%d n=%d idTrung=%s" % ("OK" if ok else "LOI", gen2, len(m2), dups(m2)))
        return 0 if ok else 2
    print("mode = check|apply|restore|selftest"); return 1


def selftest():
    base = {"BTCUSDT": 1, "ETHUSDT": 2, "BNBUSDT": 3, "SOLUSDT": 4, "PEPEUSDT": 967}
    dirty = dict(base, ABCUSDT=2, ZZZUSDT=3, XUSDT=1)
    k, e = plan_remove(dirty); assert sorted(k) == ["ABCUSDT", "XUSDT", "ZZZUSDT"] and not e, (k, e)
    after = {s: i for s, i in dirty.items() if s not in k}
    ve, new = verify(dirty, after, k); assert not ve and not new and after == base, ve
    k, e = plan_remove(dict(dirty, ABCUSDT=5)); assert e and "ABCUSDT" not in k          # id khac ky vong => khong go
    k, e = plan_remove(dict(dirty, SOLUSDT=2)); assert e                                   # trung la => dung
    k, e = plan_remove(dict(dirty, ETHUSDT=9)); assert e                                   # KEEP sai => dung
    ve, _ = verify(dirty, dict(after, SOLUSDT=5), k); assert ve                            # id khac bi doi => FAIL
    ve, _ = verify(dirty, dict(after, ABCUSDT=2), k); assert ve                            # con sot => FAIL
    k, e = plan_remove(base); assert k == [] and not e                                     # da sach
    j = json.loads(to_json(dirty, 1313)); assert j["generation"] == 1313 and j["map"]["ETHUSDT"] == 2
    print("SELFTEST OK (8 ca)"); return 0


if __name__ == "__main__":
    sys.exit(main())
