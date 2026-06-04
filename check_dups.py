import os
from collections import defaultdict
import difflib

def get_files(path):
    files = []
    for root, _, filenames in os.walk(path):
        for f in filenames:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))
    return files

gillm_files = get_files("/home/tom/github/semcod/gillm/src/gillm")
sllm_files = get_files("/home/tom/github/semcod/sllm/src/sillm")

for g in gillm_files:
    with open(g, 'r') as gf:
        g_content = gf.read()
    for s in sllm_files:
        with open(s, 'r') as sf:
            s_content = sf.read()
        
        sm = difflib.SequenceMatcher(None, g_content.splitlines(), s_content.splitlines())
        ratio = sm.ratio()
        if ratio > 0.3:
            print(f"{ratio:.2f} {g} <-> {s}")

