#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gop 2 doan export (doan dau bi dung boi timeout cua phien shell; doan sau replay lai
voi warmup 48h rieng) thanh 1 file duy nhat, KHONG trung phut.

  python3 devexport_merge.py --a <old.csv.gz> --b <new.csv.gz> --cutover <ms> --out <merged.csv.gz>

Giu tu A: ts < cutover ; tu B: ts >= cutover. Kiem: khong trung ts, khong trung header.
"""
import argparse, gzip, io, sys, zlib


def read_lines(p):
    """Doc tolerant: file .gz co the bi cat cut (tien trinh bi kill giua luc ghi)."""
    if not p.endswith(".gz"):
        return open(p, "rt").read().split("\n")
    raw = open(p, "rb").read()
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = d.decompress(raw)
    except zlib.error:
        out = b""
    return out.decode("utf-8", errors="replace").split("\n")


def head_of(p):
    return read_lines(p)[0].rstrip("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--cutover", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ha, hb = head_of(a.a), head_of(a.b)
    if ha != hb:
        print("HEADER KHAC NHAU -> dung"); print(ha); print(hb); return 2
    rows = {}
    for p, mode in ((a.a, "a"), (a.b, "b")):
        n = 0
        for line in read_lines(p)[1:]:
            if not line.strip():
                continue
            ts = int(line.split(",", 1)[0])
            if mode == "a" and ts >= a.cutover:
                continue
            if mode == "b" and ts < a.cutover:
                continue
            if ts in rows:
                print("TRUNG ts", ts, "-> bo ban sau"); continue
            rows[ts] = line if line.endswith("\n") else line + "\n"
            n += 1
        print("doc %s: %d dong dung" % (p, n))
    ks = sorted(rows)
    with gzip.open(a.out, "wt") as fh:
        fh.write(ha + "\n")
        for k in ks:
            fh.write(rows[k])
    gaps = sum(1 for i in range(1, len(ks)) if ks[i] - ks[i - 1] != 60000)
    print("ghi %s: %d dong | ts %d..%d | so cho trong >1 phut: %d" % (a.out, len(ks), ks[0], ks[-1], gaps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
