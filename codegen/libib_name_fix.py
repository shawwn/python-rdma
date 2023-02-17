#!/usr/bin/env python
# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
import sys,re

MATCH_NORMAL = "([^.]+):\.+(.*)$";
MATCH_SA = "\W+([^.]+)\.+(.*)$";

def matchify(ref,me,match):
    gr = [_f for _f in [re.match(match,I) for I in ref] if _f];
    gm = [_f for _f in [re.match(match,I) for I in me] if _f];
    gr = [(I.groups()[0],I.groups()[1]) for I in gr];
    gm = [(I.groups()[0],I.groups()[1]) for I in gm];

    idxm = 0;
    idxr = 0;
    while idxm < len(gm) and idxr < len(gr):
        r,ra = gr[idxr];
        m,ma = gm[idxm];
        if r != m:
            try:
                idxr = gr.index(m,idxr);
                continue;
            except ValueError: pass;

            try:
                idxm = gm.index(r,idxm);
                continue;
            except ValueError: pass;

            translate[m] = r;
        else:
            if ra != ma:
                print(r,ra,ma)
        idxr = idxr + 1;
        idxm = idxm + 1;

def pull_file(F):
    res = {};
    coll = [];
    for I in F.readlines():
        if I.startswith("------------- "):
            if coll:
                res[thing] = coll;
            thing = I;
            coll = [];
        else:
            coll.append(I);
    return res;

with open(sys.argv[1]) as F:
    reference = pull_file(F);
with open(sys.argv[2]) as F:
    me = pull_file(F);

translate = {};
for thing,coll in me.items():
    if thing.find("saquery', 'NR") != -1:
        try:
            matchify(reference[thing],coll,MATCH_SA)
        except KeyError:
            pass;
for I in translate.items():
    print("    %r: %r,"%I);
