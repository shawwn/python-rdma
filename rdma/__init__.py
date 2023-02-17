# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
import sys
import os
import os.path

__version__ = "1.0";

class RDMAError(Exception):
    '''General exception class for RDMA related errors.'''

class MADError(RDMAError):
    """Thrown when a MAD RPC fails in some way. The throw site includes as
    much information about the error context as possible. Depending on the
    throw context not all members may be available.

    If the RPC is an incoming request then this exception contains enough information
    for the catch to generate an error reply MAD."""
    req = None;
    rep = None;
    rep_buf = None;
    path = None;
    status = 0;
    exc_info = None;
    messages = None;

    def __init__(self,**kwargs):
        """
        :type req: derived from :class:`~rdma.binstruct.BinStruct`
        :param req: The MAD's `*Format` that was originally sent.
        :type req_buf: :class:`bytearray`
        :param req_buf: The entire raw request MAD data, if *fmt* is not present.
        :type reply_status: :class:`int`
        :param reply_status: The status value to use when generating an error reply for *req_buf*.
        :type path: :class:`~rdma.path.IBPath`
        :param path: The destination path for the request.
        :type rep: derived from :class:`~rdma.binstruct.BinStruct`
        :param rep: The MAD's `*Format` reply.
        :type rep_buf: :class:`bytearray`
        :param rep_buf: The entire raw reply MAD data.
        :type status: :class:`int`
        :param status: The entire 16 bit status value.
        :param exc_info: Result of :func:`sys.exc_info` if MAD processing failed due to an unexpected exception.
        """
        RDMAError.__init__(self);
        for k,v in kwargs.items():
            if k == "msg":
                self.message(v);
            else:
                setattr(self,k,v);

        if self.messages is None:
            if self.req is not None and self.status is not None:
                import rdma.IBA_describe;
                self.message("RPC %s got error status 0x%x - %s"%(
                    self.req.describe(),self.status,
                    rdma.IBA_describe.mad_status(self.status)));
        if self.exc_info is not None:
            self.message("Internal error, unexpected MAD exception: %r"%(
                self.exc_info,))

    def _copy_init(self,err):
        """Copy all the information from err into this class. This calls
        `__init__` on the base class."""
        RDMAError.__init__(self);
        if err is not None:
            for k,v in err.__dict__.items():
                if k[0] != "_":
                    setattr(self,k,v);

    def message(self,s):
        """Used to annotate additional messages onto the exception. For
        instance the library function issuing the RPC can call this with a
        short version of what the RPC actually was trying to do."""
        if self.messages is None:
            self.messages = [s];
        else:
            self.messages.append(s);

    def dump_detailed(self,F=None,prefix="",level=1):
        """Display detailed information about the exception. This prints
        a multi-line description to *F*. Many lines are prefixed with
        the text *prefix*. If *level* is 0 then the default summary
        line is displayed. If *level* is 1 then all summary information
        is shown. If *level* is 2 then request and reply packets are dumped.

        If the :exc:`MADError` includes a captured exception then
        dump_detailed will re-throw it after printing our information."""
        if F is None:
            F = sys.stderr;
        if level == 0 and self.exc_info is not None:
            print(prefix,self.__str__(), file=F);
            return;
        if self.messages:
            first = True;
            for I in reversed(self.messages):
                if first:
                    print(prefix,I, file=F);
                    first = False;
                else:
                    print(prefix,"+%s"%(I), file=F);
        else:
            print(prefix,self.__str__(), file=F);
        if level >= 1 and self.path is not None:
            print(prefix,"+MAD path was %r"%(self.path), file=F);
        if level >= 2 and self.req is not None:
            print(prefix,"+Request Packet %s"%(self.req.__class__.__name__), file=F)
            self.req.printer(F,header=False);
            if self.rep:
                print(prefix,"+Reply Packet %s"%(self.rep.__class__.__name__), file=F)
                self.rep.printer(F,header=False);
        if self.exc_info is not None:
            raise self.exc_info[0](self.exc_info[1]).with_traceback(self.exc_info[2]);

    def __str__(self):
        if self.messages is not None:
            if len(self.messages) == 1:
                return self.messages[-1];
            return "%s [%s]"%(self.messages[-1],self.messages[-2]);
        return "Unlabeled exception %s: %r"%(self.__name__,self.__dict__);

class MADTimeoutError(MADError):
    '''Thrown when a MAD RPC times out.'''
    def __init__(self,req,path):
        MADError.__init__(self,req=req,path=path,
                          msg="RPC %s timed out to '%s'"%(
                              req.describe(),path));

class MADClassError(MADError):
    '''Thrown when a MAD RPC returns with a class specific error code.'''
    #: Decoded error code
    code = None;

    def __init__(self,req,code,**kwargs):
        import rdma.IBA as IBA;
        if isinstance(req,IBA.SAFormat):
            MADError.__init__(self,req=req,code=code,
                              msg="RPC %s got class specific error %s"%(
                    req.describe(),IBA.const_str("MAD_STATUS_SA_",code,True)),**kwargs);
        else:
            MADError.__init__(self,req=req,code=code,
                              msg="RPC %s got class specific error %u"%(
                    req.describe(),code),**kwargs);

class SysError(RDMAError,OSError):
    '''Thrown when a system call fails. Inclues errno'''
    def __init__(self,errno,func,msg=None):
        '''*errno* is the positive errno code, *func* is the system call that
        failed and msg is more information, if applicable.'''
        if msg is not None:
            strerror = "%s - %s (%s)"%(msg,func,os.strerror(errno))
        else:
            strerror = "%s (%s)"%(func,os.strerror(errno))
        OSError.__init__(self,errno,strerror);
        self.func = func;

def get_end_port(name=None):
    """Return a :class:`rdma.devices.EndPort` for the default end port if name
    is ``None``, or for the end port described by name.

    The end port string format is one of:
      =========== ===================
      Format      Example
      =========== ===================
      device      mlx4_0  (defaults to the first port)
      device/port mlx4_0/1
      Port GID    fe80::2:c903:0:1491
      Port GUID   0002:c903:0000:1491
      =========== ===================

    :rtype: :class:`rdma.devices.EndPort`
    :raises rdma.RDMAError: If no matching device is found or name is invalid."""
    devices = get_devices();
    if len(devices) == 0:
        raise RDMAError("No RDMA devices found.");
    if name is None:
        return devices.first().end_ports.first();

    # Try for a port GID
    import rdma.devices;
    import rdma.IBA;
    try:
        gid = IBA.GID(name);
    except ValueError:
        pass;
    else:
        return rdma.devices.find_port_gid(devices,gid)[0];

    # Port GUID
    try:
        guid = IBA.GUID(name);
    except ValueError:
        pass;
    else:
        return rdma.devices.find_port_guid(devices,guid);

    # Device name string
    return rdma.devices.find_port_name(devices,name);

def get_device(name=None):
    """Return a :class:`rdma.devices.Device` for the default device if name
    is ``None``, or for the device described by name.

    The device string format is one of:
      =========== ===================
      Format      Example
      =========== ===================
      device      mlx4_0
      Node GUID   0002:c903:0000:1491
      =========== ===================

    :rtype: :class:`rdma.devices.device`
    :raises rdma.RDMAError: If no matching device is found or name is invalid."""
    devices = get_devices();
    if len(devices) == 0:
        raise RDMAError("No RDMA devices found.");
    if name is None:
        return devices.first();

    # Port GUID
    import rdma.devices;
    import rdma.IBA;
    try:
        guid = IBA.GUID(name);
    except ValueError:
        pass;
    else:
        return rdma.devices.find_node_guid(devices,guid);

    # Device name string
    try:
        return devices[name];
    except KeyError:
        raise RDMAError("RDMA device %r not found."%(name));

_cached_devices = None;
def get_devices(refresh=False):
    '''Return a container of :class:`rdma.devices.RDMADevice` objects for all devices in the system.

    The return result is an object that looks like an ordered list of
    :class:`rdma.devices.RDMADevice` objects. However, indexing the list is
    done by device name not by index. If the length of the returned object is
    0 then no devices were detected. Programs are encouraged to use
    :func:`rdma.get_end_port`.

    :rtype: :class:`~.devices.DemandList` but this is an implementation detail.'''
    global _cached_devices;
    if _cached_devices is not None and not refresh:
        return _cached_devices;

    import rdma.devices;
    if not os.path.exists(rdma.devices.SYS_INFINIBAND):
        return ();

    _cached_devices = rdma.devices.DemandList2(
        rdma.devices.SYS_INFINIBAND,
        lambda x:rdma.devices.RDMADevice(x),
        lambda x:x);
    return _cached_devices;

def get_umad(port,path=None,**kwargs):
    '''Create a :class:`rdma.umad.UMAD` instance for the associated
    :class:`rdma.devices.EndPort`. UMAD instances can issue SMPs and GMPs.
    If only GMP is required then use :func:`get_gmp_mad`.'''
    import rdma.umad;
    return rdma.umad.UMAD(port,**kwargs);

def get_gmp_mad(port,path=None,verbs=None,**kwargs):
    '''Return a subclass instace of :class:`rdma.madtransactor.MADTransactor`
    for the associated :class:`rdma.devices.EndPort`. If a verbs instance is already
    open then it should be passed in as verbs'''
    import rdma.vmad;
    if path is None:
        path = port.sa_path;

    if verbs is None:
        try:
            verbs = get_verbs(port);
        except (ImportError, RDMAError):
            return rdma.umad.UMAD(port,path,**kwargs);
        ret = rdma.vmad.VMAD(verbs,path);
        ret._allocated_cts = True;
        return ret;

    return rdma.vmad.VMAD(verbs,path);

def get_verbs(port,**kwargs):
    '''Create a :class:`rdma.uverbs.UVerbs` instance for the associated
    :class:`rdma.devices.RDMADevice`/:class:`rdma.devices.EndPort`.'''
    import rdma.ibverbs;
    return rdma.ibverbs.Context(port,**kwargs);
