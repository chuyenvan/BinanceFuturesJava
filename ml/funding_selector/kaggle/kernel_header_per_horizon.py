import os, glob
def find1(p):
    m=sorted(glob.glob(p,recursive=True))
    assert m, p
    return m[0]
os.environ['HORIZONS']='4h'
os.environ['TOOL1_GLOB']='/kaggle/input/**/ff_*.bin'
os.environ['OI_FILE']=find1('/kaggle/input/**/oi_percoin_full.bin')
os.environ['LABEL_CSV']=find1('/kaggle/input/**/funding_label.csv')
os.environ['MAP_CSV']=find1('/kaggle/input/**/symbol_map.csv')
os.environ['OUT_DIR']='/kaggle/working'
