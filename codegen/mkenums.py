import os
import re
import sys

def get_enums(F):
    s = []
    skip = True
    for I in F.readlines():
        if I[0] == '#':
            skip = I.find("infiniband/verbs.h") == -1
        else:
            if not skip:
                s.append(I)
    s = "".join(s)

    enum = {}
    for m in re.finditer(r'enum\s+(\w+)\s*{(.*?)}', s, re.DOTALL):
        name = m.group(1)
        constants = [c.partition('=')[0].strip() for c in m.group(2).split(',') if c.strip() != ""]
        enum[name] = tuple(constants)

    return enum

def write_enums_pxd(F,enums):
    print('\n\n'.join('\n'.join('%s = c.%s' % (c, c) for c in v)
                            for e,v in sorted(enums.items())), file=F)
def write_enums_pxi(F,enums):
    sep = '\n' + ' '*8
    print('\n\n'.join('    enum %s:%s' % (e,sep) + sep.join(v)
                                for e,v in sorted(enums.items())), file=F)


def codegen():
    verbs_h = "verbs_h.c"
    verbs_h_o = verbs_h + ".out"
    with open(verbs_h,"w") as F:
        F.write("#include <infiniband/verbs.h>")
    with open(verbs_h_o) as F:
        enums = get_enums(F)
    with open("rdma/libibverbs_enums.pxd","w") as F:
        print("cdef extern from 'infiniband/verbs.h':", file=F)
        write_enums_pxi(F,enums)
    with open("rdma/libibverbs_enums.pxi","w") as F:
        write_enums_pxd(F,enums)

if __name__ == '__main__':
    codegen()

