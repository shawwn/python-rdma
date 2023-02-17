# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
# Fairly simple status/inquery commands
import sys
import copy
import struct;
import rdma;
import rdma.IBA as IBA;
import rdma.IBA_describe as IBA_describe;
import rdma.madtransactor;
import rdma.satransactor;
import rdma.binstruct;
from libibtool import *;
from libibtool.libibopts import *;

def cmd_ibv_devices(argv,o):
    """Display the RDMA devices in the system.
       Usage: %prog"""
    (args,values) = o.parse_args(argv,expected_values = 0);

    print("    %-16s\t    node GUID"%("device"));
    print("    %-16s\t-------------------"%("------"));
    for I in rdma.get_devices():
        print("    %-16s\t%s"%(I.name,I.node_guid));
    return True;

def cmd_ibstat(argv,o):
    """Display the RDMA end ports in the system.
       Usage: %prog [-lsp] [DEVICE [PORT]]"""
    o.add_option("-l","--list_of_cas",action="store_true",dest="list_cas",
                 help="List all IB devices names");
    o.add_option("-s","--short",action="store_true",dest="short",
                 help="Do not show port information");
    o.add_option("-p","--port_list",action="store_true",dest="ports",
                 help="Show only port GUIDs");
    (args,values) = o.parse_args(argv);

    if args.list_cas:
        if len(values) != 0: raise CmdError("Too many arguments");
        for I in rdma.get_devices():
            print(I.name);
        return True;

    if len(values) == 0:
        end_ports = (I for J in rdma.get_devices() for I in J.end_ports);
    elif len(values) == 1:
        end_ports = (I for I in rdma.get_device(values[0]).end_ports);
    elif len(values) == 2:
        end_ports = (rdma.get_end_port("%s/%s"%(values[0],values[1])),);
    else:
        raise CmdError("Too many arguments");

    if args.ports:
        for I in end_ports:
            print(I.port_guid);
        return True;

    def show_ca(dev):
        print("CA %r"%(dev.name));
        print("\tCA type: %s"%(dev.hca_type));
        print("\tNumber of ports: %s"%(len(dev.end_ports)));
        print("\tFirmware version: %s"%(IBA_describe.dstr(dev.fw_ver)));
        print("\tHardware version: %s"%(IBA_describe.dstr(dev.hw_ver)));
        print("\tNode GUID: %s"%(dev.node_guid));
        print("\tSystem image GUID: %s"%(dev.sys_image_guid));
    def show_port(port,offset="\t\t"):
        print("%sState: %s"%(offset,IBA_describe.link_state(port.state)));
        print("%sPhysical state: %s"%(offset,IBA_describe.phys_link_state(port.phys_state)));
        print("%sRate: %r"%(offset,port.rate));
        print("%sBase lid: %r"%(offset,port.lid));
        print("%sLMC: %r"%(offset,port.lmc));
        print("%sSM lid: %r"%(offset,port.sm_lid));
        print("%sCapability mask: 0x%08x"%(offset,port.cap_mask));
        print("%sPort GUID: %s"%(offset,port.port_guid));

    last_ca = None;
    if args.short:
        for I in end_ports:
            if last_ca != I.parent:
                show_ca(I.parent);
                last_ca = I.parent;
        return True;

    if isinstance(end_ports,tuple):
        I = end_ports[0];
        print("CA: %r"%(I.parent.name));
        print("Port %u:"%(I.port_id));
        show_port(I,offset="");
        return True;

    for I in end_ports:
        if last_ca != I.parent:
            show_ca(I.parent);
            last_ca = I.parent;
        print("\tPort %u:"%(I.port_id));
        show_port(I);
    return True;

def cmd_ibstatus(argv,o):
    """Display the RDMA end ports in the system.
       Usage: %prog [DEVICE[/PORT]]"""
    (args,values) = o.parse_args(argv);

    if len(values) == 0:
        end_ports = (I for J in rdma.get_devices() for I in J.end_ports);
    elif len(values) == 1:
        end_ports = (rdma.get_end_port(values[0]),);
    else:
        raise CmdError("Too many arguments");

    for I in end_ports:
        print("""Infiniband device %r port %u status:
\tdefault gid:\t %s
\tbase lid:\t %u
\tsm lid:\t\t %u
\tstate:\t\t %u: %s
\tphys state:\t %u: %s
\trate:\t\t %s\n"""%(I.parent.name,I.port_id,I.default_gid,I.lid,I.sm_lid,
             I.state,IBA_describe.link_state(I.state).upper(),
             I.phys_state,IBA_describe.phys_link_state(I.phys_state),I.rate));
    return True;

def cmd_ibaddr(argv,o):
    """Display the GID and LID addresses for end ports.
       Usage: %prog [-glL] [TARGET]"""
    o.add_option("-l","--lid_show",action="store_true",dest="lid",
                 help="Show LID information");
    o.add_option("-L","--Lid_show",action="store_true",dest="lid",
                 help="Show LID information");
    o.add_option("-g","--gid_show",action="store_true",dest="gid",
                 help="Show GID information");
    LibIBOpts.setup(o);
    (args,values) = o.parse_args(argv);
    lib = LibIBOpts(o,args,values,1,(tmpl_target,));

    if not values:
        values = (None,);

    if args.lid is None and args.gid is None:
        args.lid = True;
        args.gid = True;

    with lib.get_umad_for_target(values[0]) as umad:
        path = lib.path;
        ninf = umad.SubnGet(IBA.SMPNodeInfo,path);
        path.DGID = IBA.GID(prefix=IBA.GID_DEFAULT_PREFIX,guid=ninf.portGUID);
        pinf = umad.SubnGet(IBA.SMPPortInfo,path,0);

        if args.gid:
            print("GID %s"%(path.DGID), end=' ')
        if args.lid:
            print("LID start %u end %u"%(pinf.LID,pinf.LID + (1 << pinf.LMC)-1), end=' ')
        print()
    return lib.done();

methods = set(('SubnGet','PerformanceGet','SubnAdmGet','SubnAdmGetTable',
               'BMGet','CommMgtGet','DevMgtGet','SNMPGet'));
methods.intersection_update(dir(rdma.madtransactor.MADTransactor));

def is_valid_attribute(attr):
    if (getattr(attr,"MAD_LENGTH",None) is None or
        getattr(attr,"MAD_ATTRIBUTE_ID",None) is None):
        return False;
    for I in methods:
        if getattr(attr,"MAD_%s"%(I.upper()),None) is not None:
            return True;
    return False;

def tmpl_method(v):
    if v not in methods:
        raise CmdError("Invalid method %r"%(v));
    return v;

def tmpl_attribute(v):
    attr = getattr(rdma.IBA,v,None);
    if attr is None:
        raise CmdError("Invalid attribute %r"%(v));
    if not is_valid_attribute(attr):
        raise CmdError("Invalid attribute %r"%(v));
    return attr;

def cmd_query_help(o,cmd,usage):
    """Generate the help text by merging in information from OPS."""
    def get_attrs():
        for k,v in rdma.IBA.__dict__.items():
            if is_valid_attribute(v):
                yield k;

    return (usage + "\n    Valid METHOD:\n    " + "\n    ".join("   %s"%(I) for I in sorted(methods)) +
            "\n    Valid ATTRIBUTE:\n    " + "\n    ".join("   %s"%(I) for I in sorted(get_attrs())))

def cmd_query(argv,o):
    """Issue any GET type query for any known attribute
       Usage: %prog METHOD ATTRIBUTE [TARGET]

       Eg:
          %prog PerformanceGet PMPortCounters -f portSelect=1
          %prog SubnAdmGet SAPathRecord -f SGID=fe80::0002:c903:0000:1491 -f DGID=fe80::0002:c903:0000:1492
          """
    import libibtool.saquery;

    o.add_option("-a","--attribute-id",action="store",dest="attribute_id",
                 default=0,type=int,
                 help="Set the attribute ID field in the request MAD");
    o.add_option("-f","--field",action="append",dest="fields",
                 default=[],
                 help="Set the given field in the request MAD.");
    LibIBOpts.setup(o);
    (args,values) = o.parse_args(argv);
    lib = LibIBOpts(o,args,values,3,(tmpl_method,tmpl_attribute,tmpl_target));

    if len(values) == 2:
        values.append('');
    if len(values) < 3:
        raise CmdError("Too few arguments");

    with lib.get_umad_for_target(values[2],
                                 gmp=(values[0] != "SubnGet")) as umad:
        meth = getattr(umad,values[0]);
        req = values[1]();
        if values[0].startswith("SubnAdm"):
            req = IBA.ComponentMask(req);
        for I in args.fields:
            try:
                n,v = I.split("=");
            except ValueError:
                raise CmdError("Field %r does not have exactly 1 equals."%(I))
            libibtool.saquery.set_mad_attr(req,n,v);
        ret = meth(req,lib.path,args.attribute_id);
        if isinstance(ret,list):
            out = libibtool.saquery.Indentor(sys.stdout);
            for num,I in enumerate(ret):
                print("Reply structure #%u"%(num));
                I.printer(out,**lib.format_args);
        else:
            ret.printer(sys.stdout,**lib.format_args);
    return lib.done();

def cmd_sminfo(argv,o):
    """Display the SASMInfo record for a subnet manager.
       Usage: %prog [TARGET [ATTR_MOD]]

       This command includes the ability to send a SubnSet(SASMInfo)
       packet formed with a given priority, state, SMKey and Attribute
       Modifier. A set is performed if a ATTR_MOD is provided. See IBA 14.4.1."""
    o.add_option("-s","--state",action="store",dest="state",type="int",
                 help="Set the SM state");
    o.add_option("-p","--priority",action="store",dest="priority",type="int",
                 help="Set the SM priority");
    o.add_option("--sminfo_smkey",action="store",dest="sminfo_smkey",type="int",default=0,
                 help="Use this value for the SMPSMInfo.SMKey");
    LibIBOpts.setup(o);
    (args,values) = o.parse_args(argv);
    lib = LibIBOpts(o,args,values,2,(tmpl_target,tmpl_int));

    if not values:
        values = (None,);

    with lib.get_umad_for_target(values[0]) as umad:
        if values[0]:
            path = lib.path;
        else:
            path = umad.end_port.sa_path.copy(dqpn=0,qkey=IBA.IB_DEFAULT_QP0_QKEY);

        sinf = IBA.SMPSMInfo();
        if args.smkey is not None:
            sinf.SMKey = args.sminfo_smkey;
        sinf = umad.SubnGet(sinf,path);
        smlid = path.DLID;
        if smlid == IBA.LID_PERMISSIVE:
            smlid = umad.SubnGet(IBA.SMPPortInfo,path).LID;
        print("sminfo: sm lid %u sm guid %s, activity count %u priority %u state %u"%(
            smlid,sinf.GUID,sinf.actCount,sinf.priority,sinf.SMState));

        if args.smkey is not None:
            sinf.SMKey = args.smkey;
        if len(values) == 2:
            if args.state is not None:
                sinf.SMState = args.state;
            if args.priority is not None:
                sinf.priority = args.priority;
            amod = values[1];
            sinf = umad.SubnSet(sinf,path,amod);
            print("sminfo: sm lid %u sm guid %s, activity count %u priority %u state %u"%(
                smlid,sinf.GUID,sinf.actCount,sinf.priority,sinf.SMState));
    return lib.done();

def cmd_smpdump(argv,o):
    """Display an arbitrary SMP record
       Usage: %prog TARGET ATTR [ATTR_MOD]

       ATTR is the attribute ID and ATTR_MOD is an optional modifier."""
    o.add_option("-p","--decode",action="store_true",dest="decode",
                 help="Pretty print the entire reply.");
    LibIBOpts.setup(o);
    (args,values) = o.parse_args(argv);
    lib = LibIBOpts(o,args,values,3,(tmpl_target,tmpl_int,tmpl_int));

    if len(values) < 2:
        raise CmdError("Too few arguments");

    with lib.get_umad_for_target(values[0]) as umad:
        path = lib.path;
        class Dummy(rdma.binstruct.BinStruct):
            buf = None
            def unpack_from(self,buf,offset=0):
                self.buf = buf[offset:];
                pass;
            def pack_into(self,buf,offset=0):
                pass;

        setattr(Dummy,"MAD_ATTRIBUTE_ID",values[1]);
        setattr(Dummy,"MAD_SUBNGET",IBA.MAD_METHOD_GET);
        payload = Dummy;
        res = umad.SubnGet(payload,path,values[2] if len(values) >= 3 else 0);
        if args.decode:
            umad.reply_fmt.printer(sys.stdout);
        else:
            assert(len(res.buf) % 4 == 0);
            ret = res.buf.encode("hex");
            for I in range(len(ret)/4):
                print(ret[I*4:I*4+4], end=' ')
                if (I+1) % 8 == 0:
                    print();
            if (I+1) % 8 != 0:
                print();
            print("SMP status: 0x%04x"%(umad.reply_fmt.status | (umad.reply_fmt.D << 15)))
    return lib.done();

def cmd_ibportstate(argv,o):
    """Manipulate the SMPPortInfo of a port
       Usage: %prog TARGET PORTNUM OP [OP_ARG]

       OP is one of enable, disable, reset, speed, width, query."""
    LibIBOpts.setup(o);
    (args,values) = o.parse_args(argv,);
    lib = LibIBOpts(o,args,values,4,(tmpl_target,tmpl_int,str,tmpl_int));

    if len(values) < 3:
        raise CmdError("Too few arguments");

    with lib.get_umad_for_target(values[0]) as umad:
        path = lib.path;

        portIdx = values[1];
        if isinstance(umad,rdma.satransactor.SATransactor):
            pinf = umad._parent.SubnGet(IBA.SMPPortInfo,path,portIdx);
        else:
            pinf = umad.SubnGet(IBA.SMPPortInfo,path,portIdx);

        if isinstance(path,rdma.path.IBDRPath):
            peer_path = path.copy();
            peer_path.drPath += chr(portIdx);
        else:
            peer_path = rdma.path.IBDRPath(path.end_port,
                                           SLID=path.SLID,
                                           drSLID=path.SLID,
                                           DLID=path.DLID,
                                           drPath="\0" + chr(portIdx));
        if pinf.portState != IBA.PORT_STATE_DOWN:
            peer_pinf = umad.SubnGet(IBA.SMPPortInfo,peer_path,portIdx);
        else:
            peer_pinf = None;

        # NOP the modification pinf.
        mpinf = copy.copy(pinf);
        mpinf.portState = 0;
        mpinf.portPhysicalState = 0;
        mpinf.linkSpeedEnabled = 0;
        mpinf.linkWidthEnabled = 0;

        if values[2] == "query":
            if peer_pinf is not None:
                print("# Port info: Lid %u port %u (peer is Lid %u port %u)"%(
                    pinf.LID,pinf.localPortNum,
                    peer_pinf.LID,peer_pinf.localPortNum))
            else:
                print("# Port info: Lid %u port %u"%(
                    pinf.LID,pinf.localPortNum));
            pinf.printer(sys.stdout,**lib.format_args);
        elif values[2] == "enable" or values[2] == "reset":
            mpinf.portPhysicalState = IBA.PHYS_PORT_STATE_POLLING;
            umad.SubnSet(mpinf,path,portIdx);
        elif values[2] == "disable":
            mpinf.portPhysicalState = IBA.PHYS_PORT_STATE_DISABLED;
            umad.SubnSet(mpinf,path,portIdx);
        elif values[2] == "speed":
            mpinf.linkSpeedEnabled = values[3];
            umad.SubnSet(mpinf,path,portIdx);
        elif values[2] == "width":
            mpinf.linkWidthEnabled = values[3];
            umad.SubnSet(mpinf,path,portIdx);
        else:
            raise CmdError("Operation %r is not known"%(values[3]));
    return lib.done();

def decode_link(o,bytes):
    """Assume bytes starts with the LRH and parse accordingly. Returns bytes
       starting at the MAD header"""
    lhdr = IBA.HdrLRH(bytes);
    off = 8;
    if o.verbosity >= 1:
        lhdr.printer(sys.stdout);
    if lhdr.LNH & 1 == 1:
        ghdr = IBA.HdrGRH(bytes[off:]);
        if o.verbosity >= 1:
            ghdr.printer(sys.stdout);
        off = off + 40;
    bth = IBA.HdrBTH(bytes[off:]);
    if o.verbosity >= 1:
        bth.printer(sys.stdout);
    off = off + 12;
    if bth.service == 3 and bth.function == 4:
        deth = IBA.HdrDETH(bytes[off:]);
        if o.verbosity >= 1:
            deth.printer(sys.stdout);
        off = off + 8;
    return bytes[off:]

class UMADHdr(rdma.binstruct.BinStruct):
    MAD_LENGTH = 64;
    MEMBERS = [('agent_id',32,1),('status',32,1),('timeout_ms',32,1),
               ('retries',32,1),('length',32,1),
               ('qpn',32,1),('qkey',32,1),('lid',16,1),('sl',8,1),
               ('path_bits',8,1),('grh_present',8,1),('gid_index',8,1),('hop_limit',8,1),
               ('traffic_class',8,1),('gid',128,1),('flow_label',32,1),('pkey_index',16,1),
               ('reserved_58',8,6)];

    def __init__(self,buf = None,offset = 0):
        rdma.binstruct.BinStruct.__init__(self,buf,offset);
        self.buf = buf[offset : offset + self.MAD_LENGTH];
        assert len(self.buf) == self.MAD_LENGTH;

    def unpack_from(self,buffer,offset=0):
        from socket import htonl as cpu_to_be32;
        from socket import htons as cpu_to_be16;

        (self.agent_id,self.status,self.timeout_ms,self.retries,self.length,
         self.qpn,self.qkey,self.lid,self.sl,self.path_bits,self.grh_present,self.gid_index,
         self.hop_limit,self.traffic_class,self.gid,self.flow_label,self.pkey_index,self.reserved_58) = \
         struct.unpack_from("=LLLLLLLHBBBBBB16sLH6s",buffer,offset+0);

        self.qpn = cpu_to_be32(self.qpn);
        self.qkey = cpu_to_be32(self.qkey);
        self.lid = cpu_to_be16(self.lid);
        self.gid = IBA.GID(self.gid,raw=True);
        self.flow_label = cpu_to_be32(self.flow_label);

    def pack_into(self,buffer,offset=0):
        assert len(buffer) == self.MAD_LENGTH;
        buffer[:] = self.buf;

def decode_umad(o,bytes):
    """Assume bytes star ts with a umad header and parse accordingly."""
    if o.verbosity >= 1:
        UMADHdr(bytes).printer(sys.stdout);
    return bytes[UMADHdr.MAD_LENGTH:];

def cmd_decode_mad(argv,o):
    """Accept on stdin a hex dump of a MAD and pretty print it.
       Usage: %prog [-v]

       All spaces and newlines are removed from the input text, the
       result must be a single string of hex digits."""
    import libibtool.vendstruct
    libibtool.vendstruct.install_vend();
    o.add_option("-v","--verbosity",dest="verbosity",action="count",default=0,
                 help="Increase the verbosity level of diagnostic messages, each -v increases by 1.")
    o.add_option("-o","--offset",dest="offset",action="store",default=0,type=int,
                 help="Start at this offest before decoding.")
    o.add_option("-l",dest="lrh",action="store_true",
                 help="The data starts at the LRH, not the MAD header");
    o.add_option("--umad",dest="umad",action="store_true",
                 help="The data includes a kernel umad header, eg it is from /dev/infiniband/umadX");
    (args,values) = o.parse_args(argv,expected_values = 0);
    o.verbosity = args.verbosity;

    print("Input the MAD in HEX followed by Ctrl-D");
    inp = "".join(sys.stdin.readlines());
    if inp[0] == '"' or inp[0] == "'":
        bytes = inp.strip()[1:-1].decode("string_escape");
    else:
        inp = inp.replace(" ","").replace("\n","").replace("\r","").replace("\t","");
        if o.verbosity >= 2:
            print("Input HEX value is:\n  ",repr(inp));
        bytes = inp.decode("hex");
    bytes = bytes[args.offset:];
    if o.verbosity >= 2:
        print(bytes.encode("hex"));

    if args.umad:
        bytes = decode_umad(o,bytes);

    if args.lrh:
        bytes = decode_link(o,bytes);

    hdr = IBA.MADHeader(bytes);
    if o.verbosity >= 1:
        hdr.printer(sys.stdout);
    kind = IBA.get_fmt_payload(*rdma.madtransactor.MADTransactor.get_request_match_key(bytes));
    if kind[0] is None:
        if o.verbosity == 0:
            hdr.printer(sys.stdout);
        raise CmdError("Don't know what this mgmtClass/classVersion is.")
    fmt = kind[0](bytes);
    print(fmt.__class__.__name__,fmt.describe());
    fmt.printer(sys.stdout,header=False);

def cmd_set_nodedesc(argv,o):
    """Set or display the node description for CAs.
       Usage: %prog [-v] [NAME]

       By default all CAs are altered, use -C or -P to select a single CA."""
    o.add_option("-v",dest="view_all",action="store_true",
                 help="Increase the verbosity level of diagnostic messages, each -v increases by 1.")
    o.add_option("-C","--Ca",dest="CA",
                 help="RDMA device to use. Specify a device name or node GUID");
    o.add_option("-P","--Port",dest="port",
                 help="RDMA end port to use. Specify a GID, port GUID, DEVICE/PORT or port number.");
    (args,values) = o.parse_args(argv);

    dev = None
    if args.CA is not None:
        dev = rdma.get_device(args.CA);
    if dev is None and args.port is not None:
        dev = rdma.get_end_port(args.port).parent;

    if args.view_all or len(values) <= 0:
        for I in rdma.get_devices():
            if dev is not None and I != dev:
                continue;
            print("%s: %s"%(I.name,IBA_describe.dstr(I.node_desc)))
    else:
        name = values[0].decode();
        name = name.encode("utf-8");
        for I in rdma.get_devices():
            if dev is not None and I != dev:
                continue;
            with open(os.path.join(I._dir,"node_desc"),"w") as F:
                F.write(name);
    return True;
