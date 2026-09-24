"""VIEC A (A.2): doc doc lap cand.bin.gz cua TICKLOG (C2b-nen env-mode) de XAC NHAN lai
phan ra quyet dinh tung phut-ung-vien theo LY DO (docs/result/TICKLOG_RESULT.md §5)."""
import gzip, struct, collections, sys
NAME={0:"ENTERED",1:"ALREADY_OPEN",2:"NO_TICKER",3:"NO_PRED",4:"GATE_REJECT",5:"NO_BUDGET",
      6:"TIER3_DCA",7:"GRID_EXHAUSTED",8:"TOPK_CUT"}
def parse(path):
    f=gzip.open(path,"rb")
    hdr=f.read(16)
    magic,ver,reclen,_=struct.unpack(">iiii",hdr)
    assert reclen==32, reclen
    rec=struct.Struct(">qhhbbbBffff")
    dec=collections.Counter(); permin=collections.defaultdict(set); lvl=collections.Counter()
    n=0
    while True:
        b=f.read(32*200000)
        if not b: break
        for i in range(0,len(b),32):
            ts,sym,rank,d,l,leg,pad,score,thr,pr,price=rec.unpack_from(b,i)
            n+=1; dec[NAME.get(d,d)]+=1; permin[ts].add((sym,d)); lvl[(NAME.get(d,d),l)]+=1
    f.close()
    return n,dec,permin,lvl
for tag in sys.argv[1:]:
    p=f"/home/ubuntu/tick/{tag}/cand.bin.gz"
    n,dec,permin,lvl=parse(p)
    print(f"=== {tag}: candRows={n} (meta khop)" )
    tot=sum(dec.values())
    for k,v in dec.most_common():
        print("   %-16s %12d  %6.3f%%"%(k,v,100*v/tot))
    mins=len(permin)
    blocked=sum(1 for ts,s in permin.items() if any(d!=0 for _,d in s))
    tall=sum(1 for ts,s in permin.items() if any(d==0 for _,d in s))
    print("   phut co >=1 ung vien: %d ; co >=1 ung vien BI CHAN: %d ; co >=1 ENTERED: %d"%(mins,blocked,tall))
    # phut co n ung vien khong khoa
    free=collections.Counter()
    for ts,s in permin.items():
        free[len(s)]+=1
    import statistics
    print("   so ung vien/phut: min=%d med=%d max=%d"%(min(free),statistics.median([k for k,v in free.items() for _ in range(v)]),max(free)))
