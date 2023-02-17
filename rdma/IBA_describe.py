# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
# Describe various IBA constants as strings
import rdma.IBA as IBA;
import rdma.binstruct;

def mad_status(status):
    """Decode a MAD status into a string."""
    res = "";
    if status & IBA.MAD_STATUS_BUSY:
        res = res + "BUSY ";
    if status & IBA.MAD_STATUS_REDIRECT:
        res = res + "REDIECT ";
    code = (status >> 2) & 7;
    if code == 0:
        return res + "Ok";
    if code == 1:
        return res + "Bad version";
    if code == 2:
        return res + "Unsupported method";
    if code == 3:
        return res + "Unsupported method+attr";
    if code == 7:
        return res + "Invalid attr or modifier";
    return res + "??";

def node_type(value):
    """Decode a Node Type *value* into a string."""
    if value == IBA.NODE_CA:
        return "Channel Adapter"
    if value == IBA.NODE_SWITCH:
        return "Switch"
    if value == IBA.NODE_ROUTER:
        return "Router"
    return "?? %u"%(value);

def link_state(value):
    """Decode a Port Info port state *value* into a string."""
    if value == IBA.PORT_STATE_DOWN:
        return "Down";
    if value == IBA.PORT_STATE_INIT:
        return "Init";
    if value == IBA.PORT_STATE_ARMED:
        return "Armed";
    if value == IBA.PORT_STATE_ACTIVE:
        return "Active";
    return "?? %u"%(value);

def phys_link_state(value):
    """Decode a Port Info port physical state *value* into a string."""
    if value == IBA.PHYS_PORT_STATE_SLEEP:
        return "Sleep";
    if value == IBA.PHYS_PORT_STATE_POLLING:
        return "Polling";
    if value == IBA.PHYS_PORT_STATE_DISABLED:
        return "Disabled";
    if value == IBA.PHYS_PORT_STATE_CFG_TRAIN:
        return "Config.Train";
    if value == IBA.PHYS_PORT_STATE_LINK_UP:
        return "Link UP";
    if value == IBA.PHYS_PORT_STATE_LINK_ERR_RECOVERY:
        return "Error Recovery";
    if value == IBA.PHYS_PORT_STATE_PHY_TEST:
        return "Phy Test";
    return "?? %u"%(value);

def link_speed(value):
    """Decode a Port Info linkSpeedActive value into a string."""
    res = [];
    if value & IBA.LINK_SPEED_2Gb5:
        res.append("SDR");
    if value & IBA.LINK_SPEED_5Gb0:
        res.append("DDR");
    if value & IBA.LINK_SPEED_10Gb0:
        res.append("QDR");
    return ",".join(res);

def link_speed_ext(value):
    """Decode a Port Info linkSpeedExtActive value into a string."""
    res = [];
    if value & IBA.LINK_SPEED_EXT_14Gb0:
        res.append("FDR");
    if value & IBA.LINK_SPEED_EXT_25Gb7:
        res.append("EDR");
    return ",".join(res);

def link_width(width):
    """Convert a link with constant into an integer number of lanes."""
    if width == IBA.LINK_WIDTH_1x:
        return 1;
    if width == IBA.LINK_WIDTH_4x:
        return 4;
    if width == IBA.LINK_WIDTH_8x:
        return 8;
    if width == IBA.LINK_WIDTH_12x:
        return 12;
    return 0;

def rate(value):
    """Return the rate (eg a :attr:`rdma.IBA.SAPathRecord.rate`) *value*
    as an integer bits/sec."""
    if value == IBA.PR_RATE_2Gb5:
        return 2500000000;
    if value == IBA.PR_RATE_5Gb0:
        return 500000000;
    if value == IBA.PR_RATE_10Gb0:
        return 1000000000;
    if value == IBA.PR_RATE_14Gb0:
        return 1400000000;
    if value == IBA.PR_RATE_20Gb0:
        return 2000000000;
    if value == IBA.PR_RATE_25Gb0:
        return 2500000000;
    if value == IBA.PR_RATE_30Gb0:
        return 3000000000;
    if value == IBA.PR_RATE_40Gb0:
        return 4000000000;
    if value == IBA.PR_RATE_56Gb0:
        return 5600000000;
    if value == IBA.PR_RATE_60Gb0:
        return 6000000000;
    if value == IBA.PR_RATE_80Gb0:
        return 8000000000;
    if value == IBA.PR_RATE_100Gb0:
        return 10000000000;
    if value == IBA.PR_RATE_112Gb0:
        return 11200000000;
    if value == IBA.PR_RATE_120Gb0:
        return 12000000000;
    if value == IBA.PR_RATE_168Gb0:
        return 16800000000;
    if value == IBA.PR_RATE_200Gb0:
        return 20000000000;
    if value == IBA.PR_RATE_300Gb0:
        return 30000000000;
    return 2499999999; # ???

def to_rate(value):
    """Convert a rate in integer bits/sec to an IBA rate (eg a
    :attr:`rdma.IBA.SAPathRecord.rate`). The lowest matching rate constant
    is returned."""
    if value >= 30000000000:
        return IBA.PR_RATE_300Gb0
    if value >= 20000000000:
        return IBA.PR_RATE_200Gb0
    if value >= 16800000000:
        return IBA.PR_RATE_168Gb0
    if value >= 12000000000:
        return IBA.PR_RATE_120Gb0
    if value >= 11200000000:
        return IBA.PR_RATE_112Gb0
    if value >= 10000000000:
        return IBA.PR_RATE_100Gb0
    if value >= 8000000000:
        return IBA.PR_RATE_80Gb0
    if value >= 6000000000:
        return IBA.PR_RATE_60Gb0
    if value >= 5600000000:
        return IBA.PR_RATE_56Gb0
    if value >= 4000000000:
        return IBA.PR_RATE_40Gb0
    if value >= 3000000000:
        return IBA.PR_RATE_30Gb0
    if value >= 2500000000:
        return IBA.PR_RATE_25Gb0
    if value >= 2000000000:
        return IBA.PR_RATE_20Gb0
    if value >= 1400000000:
        return IBA.PR_RATE_14Gb0
    if value >= 1000000000:
        return IBA.PR_RATE_10Gb0
    if value >= 500000000:
        return IBA.PR_RATE_5Gb0
    return IBA.PR_RATE_2Gb5

def description(value):
    """Decodes a fixed length string from a IBA MAD (such as
    :class:`rdma.IBA.SMPNodeDescription`) These strings are considered to be
    UTF-8 and null padding is removed."""
    if isinstance(value,bytearray):
        zero = 0;
    else:
        zero = ord(0);
    for I in range(0,len(value)-1,1):
        if value[I] == zero:
            return value[:I].decode("UTF-8");
    return '';

def dstr(value,quotes = False):
    """Convert to a display string. This escapes values like `repr` but
    returns with no extra adornment like quotes or a starting u. The intent of
    this function is to provide a safe printable that has undesired values
    escaped. FIXME: This should not be so aggressive with `repr`, that throws
    away the unicode as well."""
    if value is None:
        return "None";
    r = repr(value);
    if isinstance(value,str):
        r = r[1:];
    if quotes:
        return r;
    return r[1:-1];

def _array_dump(F,a,buf,mbits,name,offset=0):
    """Dump an array beside the hex values. Each array member is printed
    beside the hex dword that it starts on."""
    cur_dword = 0;
    off = 0
    idx = 0;
    mb = [];
    max_idx = len(a);
    max_dword = (mbits*max_idx)//8;
    while cur_dword < max_dword:
        del mb[:]
        while off < cur_dword*8 + 32 and idx < max_idx:
            off = off + mbits;
            if idx == 0:
                mb.append("%s=[%u:%r"%(name,idx,a[idx]));
            elif idx+1 == max_idx:
                mb.append("%u:%r]"%(idx,a[idx]));
            else:
                mb.append("%u:%r"%(idx,a[idx]));
            idx = idx + 1;

        print("%3u %02X%02X%02X%02X %s"%\
              (offset + cur_dword,ord(buf[cur_dword]),ord(buf[cur_dword+1]),
               ord(buf[cur_dword+2]),ord(buf[cur_dword+3]),
               ", ".join(mb)), file=F);
        cur_dword = cur_dword + 4;

def struct_dump(F,s,offset=0,name_prefix=''):
    """Pretty print the structure *s*. *F* is the output file, *offset* is
    added to all printed offsets and name_prefix is used to prefix names
    when descending."""
    buf = bytearray(s.MAD_LENGTH);
    s.pack_into(buf);
    buf = bytes(buf);

    idx = 0;
    off = 0;
    mb = [];
    max_idx = len(s.MEMBERS);
    max_dword = len(buf);
    for nz_dword in range(max_dword-1,-1,-1):
        if buf[nz_dword] != '\0':
            break;
    cur_dword = 0;
    while cur_dword < max_dword:
        del mb[:]
        if (idx >= max_idx and cur_dword > nz_dword):
            break;
        while off < cur_dword*8 + 32 and idx < max_idx:
            name,mbits,count = s.MEMBERS[idx];
            bits = mbits*count;
            aligned = (off % 32) == 0 and (bits % 32) == 0;
            off = off + bits;
            idx = idx + 1;
            attr = getattr(s,name);

            if aligned and count == 1:
                # Special automagic decode of format data members based on
                # attribute ID.
                if name == "data" and isinstance(s,rdma.binstruct.BinFormat):
                    nattr = IBA.ATTR_TO_STRUCT.get((s.__class__,s.attributeID));
                    if nattr != None:
                        if nattr.MAD_LENGTH <= max_dword - cur_dword:
                            attr = nattr(buf,cur_dword);

                # Recurse into children structs
                if isinstance(attr,rdma.binstruct.BinStruct):
                    print("   + %s%s %s"%(name_prefix,name,
                                               attr.__class__.__name__), file=F)
                    struct_dump(F,attr,cur_dword+offset,
                                name_prefix="%s%s."%(name_prefix,name));
                    cur_dword = cur_dword + bits//8;
                    if cur_dword >= max_dword:
                        return
                    print("   - %s%s"%(name_prefix,name), file=F)
                    continue;

            # Handle aligned arrays by pretty printing the array
            if aligned and count != 1 and count == len(attr):
                # Handle arrays of structures
                if isinstance(attr[0],rdma.binstruct.BinStruct):
                    for I,v in enumerate(attr):
                        print("   + %s%s[%u] %s"%(
                            name_prefix,name,I,v.__class__.__name__), file=F);
                        struct_dump(F,v,cur_dword,
                                    name_prefix="%s%s[%u]."%(
                                        name_prefix,name,I));
                        cur_dword = cur_dword + bits//8;
                    if cur_dword >= max_dword:
                        return
                    print("   - %s%s"%(name_prefix,name), file=F)
                    continue;

                _array_dump(F,attr,buf[cur_dword:cur_dword + bits//8],
                            mbits,name,offset=cur_dword+offset);
                cur_dword = cur_dword + bits//8;
                continue;

            if aligned:
                # Not much sense in printing bytes we can see in hex.
                if isinstance(attr,bytearray):
                    mb.append("%s=<%u bytes>"%(name,bits/8));
                    continue;
            mb.append("%s=%r"%(name,getattr(s,name)));

        if cur_dword+3 >= max_dword:
            return

        while off > cur_dword*8:
            print("%3u %02X%02X%02X%02X %s"%\
                (offset + cur_dword,ord(buf[cur_dword]),ord(buf[cur_dword+1]),
                 ord(buf[cur_dword+2]),ord(buf[cur_dword+3]),
                 ",".join(mb)), file=F);
            del mb[:]
            cur_dword = cur_dword + 4;

def struct_dotted(F,s,name_prefix='',dump_list=False,skip_reserved=True,
                  column=33,colon=False,name_map=None):
    """This tries to emulate the libib structure print format. Members are
    printed one per line with values aligned on column 32."""
    for name,mbits,count in s.MEMBERS:
        if skip_reserved and name.startswith("reserved_"):
            continue;
        attr = getattr(s,name);
        if attr is None:
            continue;
        cname = name[0].upper() + name[1:];
        if name_map:
            cname = name_map.get(cname,cname);

        # Special automagic decode of format data members based on
        # attribute ID.
        if name == "data" and isinstance(s,rdma.binstruct.BinFormat):
            nattr = IBA.ATTR_TO_STRUCT.get((s.__class__,s.attributeID));
            if nattr != None:
                if nattr.MAD_LENGTH <= len(attr):
                    attr = nattr(attr);

        if isinstance(attr,rdma.binstruct.BinStruct):
            struct_dotted(F,attr,"%s%s."%(name_prefix,name),
                          dump_list=dump_list,
                          skip_reserved=skip_reserved,
                          column=column,
                          colon=colon,
                          name_map=name_map);
            continue;

        if count != 1 and len(attr) == count:
            ref = attr[0];
        else:
            ref = attr;

        conv = None;
        if isinstance(ref,IBA.GID) or isinstance(ref,IBA.GUID):
            fmt = "%s";
        else:
            fmt = IBA.MEMBER_FORMATS.get(name,"%r");
            if fmt == "hex":
                fmt = "0x%%0%ux"%((mbits+3)//4);
            if fmt == "str":
                fmt = "%s";
                conv = lambda value: dstr(description(value),quotes=True);
            if fmt == "gid_prefix":
                fmt = "%s/64";
                conv = lambda value: IBA.GID(prefix=value,guid=IBA.GUID(0));

        if count != 1 and len(attr) == count and conv == None:
            if isinstance(attr[0],rdma.binstruct.BinStruct):
                for I,v in enumerate(attr):
                    struct_dotted(F,v,"%s%s[%u]."%(name_prefix,name,I),
                                  dump_list=dump_list,
                                  skip_reserved=skip_reserved,
                                  column=column,
                                  colon=colon,
                                  name_map=name_map);
                continue;

            if mbits > 16 or dump_list:
                for I,v in enumerate(attr):
                    n = "%s%s[%u]"%(name_prefix,cname,I);
                    if colon:
                        n = n + ":";
                    if conv:
                        v = conv(v);
                    print(("%s%s"+fmt)%(n,"."*(column-len(n)),v), file=F);
                continue;
            else:
                attr = "[%s]"%(", ".join(("%u:"+fmt)%(I,v) for I,v in enumerate(attr)));
                fmt = "%s";

        n = "%s%s"%(name_prefix,cname);
        if colon:
            n = n + ":";
        if conv:
            attr = conv(attr);
        print(("%s%s"+fmt)%(n,"."*(column-len(n)),attr), file=F);
