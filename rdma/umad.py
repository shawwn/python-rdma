#!/usr/bin/python
from __future__ import with_statement;

import rdma,rdma.tools,rdma.path,rdma.madtransactor;
import rdma.IBA as IBA;
import fcntl,struct,copy;
from socket import htonl as cpu_to_be32;
from socket import htons as cpu_to_be16;

SYS_INFINIBAND_MAD = "/sys/class/infiniband_mad/";

class LazyIBPath(rdma.path.IBPath):
    """Similar to IBPath but the unpack of the umad AH is deferred until
    necessary since most of the time we do not care."""
    def __getattribute__(self,name):
        if name[0] != '_':
            # I wonder if this is evil? We switch out class to the
            # parent the first time someone requests an attribute.
            object.__setattr__(self,"__class__",rdma.path.IBPath);
            LazyIBPath._unpack_rcv(self);
        return object.__getattribute__(self,name);

    @staticmethod
    def _unpack_rcv(self):
        """Switch a UMAD AH back into an IBPath. Note this is only
        used for recv'd AH's where the meaning of the fields is altered.

        Our convention is that the path describes the packet headers as they
        existed on the wire, so this untwiddles things."""
        (sqpn,
         qkey,
         SLID,
         self.SL,
         DLID_bits,
         self.has_grh,
         DGID_index,
         self.hop_limit,
         self.traffic_class,
         self.SGID,
         flow_label,
         self.pkey_index) = \
         UMad.ib_mad_addr_t.unpack(self._cache_umad_ah);
        self.sqpn = cpu_to_be32(sqpn);
        # FIXME: dqpn can be derived from agent_id
        self.qkey = cpu_to_be32(qkey);
        self.DLID = DLID_bits | self.end_port.lid;
        self.SLID = cpu_to_be16(SLID);
        if self.has_grh:
            del self.SGID
            self.DGID = self.end_port.gids[DGID_index];
            self.flow_label = cpu_to_be32(flow_label);
        
class UMad(rdma.tools.SysFSDevice,rdma.madtransactor.MADTransactor):
    '''Handle to a umad kernel interface. This supports the context manager protocol.'''
    IB_IOCTL_MAGIC = 0x1b
    IB_USER_MAD_REGISTER_AGENT = rdma.tools._IOC(3,IB_IOCTL_MAGIC,1,28);
    IB_USER_MAD_UNREGISTER_AGENT = rdma.tools._IOC(1,IB_IOCTL_MAGIC,2,4);
    IB_USER_MAD_ENABLE_PKEY = rdma.tools._IOC(0,IB_IOCTL_MAGIC,3,0);

    # typedef struct ib_user_mad {
    #  uint32_t agent_id;
    #  uint32_t status;
    #  uint32_t timeout_ms;
    #  uint32_t retries;
    #  uint32_t length;
    #  ib_mad_addr_t addr;
    #  uint8_t data[0];
    # } ib_user_mad_t;
    ib_user_mad_t = struct.Struct("=LLLLL44s");
    # typedef struct ib_mad_addr {
    #  uint32_t qpn; // network
    #  uint32_t qkey; // network
    #  uint16_t lid; // network
    #  uint8_t sl;
    #  uint8_t path_bits;
    #  uint8_t grh_present;
    #  uint8_t gid_index;
    #  uint8_t hop_limit;
    #  uint8_t traffic_class;
    #  uint8_t gid[16];
    #  uint32_t flow_label; // network
    #  uint16_t pkey_index;
    #  uint8_t reserved[6];
    # } ib_mad_addr_t;
    ib_mad_addr_t = struct.Struct("=LLHBBBBBB16sLH6x");
    ib_mad_addr_local_t = struct.Struct("=LLHBBxxxx16x4xH6x");

    def __init__(self,parent):
        rdma.madtransactor.MADTransactor.__init__(self);

        for I in parent._iterate_services_end_port(SYS_INFINIBAND_MAD,"umad\d+"):
            rdma.tools.SysFSDevice.__init__(self,parent,I);
            break;
        else:
            raise rdma.RDMAError("Unable to open umad device for %s"%(repr(parent)));
        
        with open(SYS_INFINIBAND_MAD + "abi_version") as F:
            self.abi_version = int(F.read().strip());
        if self.abi_version < 5:
            raise RDMAError("UMAD ABI version is %u but we need at least 5."%(self.abi_version));
        if not self._ioctl_enable_pkey():
            raise RDMAError("UMAD ABI is not compatible, we need PKey support.");

        self.sbuf = bytearray(320);

    def _ioctl_enable_pkey(self):
        return fcntl.ioctl(self.dev.fileno(),self.IB_USER_MAD_ENABLE_PKEY) == 0;
    def _ioctl_unregister_agent(self,agent_id):
        fcntl.ioctl(self.dev.fileno(),self.IB_USER_MAD_UNREGISTER_AGENT,
                    struct.pack("=I",agent_id));

    def _ioctl_register_agent(self,dqpn,mgmt_class,mgmt_class_version,
                                oui,rmpp_version,method_mask):
        """Returns agent_id"""
        buf = struct.pack("=L4LBBB3BB",
                          0,
                          method_mask[0],method_mask[1],method_mask[2],method_mask[3],
                          dqpn,
                          mgmt_class,
                          mgmt_class_version,
                          oui[0],oui[1],oui[2],
                          rmpp_version);
        buf = fcntl.ioctl(self.dev.fileno(),self.IB_USER_MAD_REGISTER_AGENT,
                          buf);
        return struct.unpack("=L",buf[:4])[0];

    def register_client(self,mgmt_class,mgmt_version):
        """This is the general entry point to start operating as a client.
        The class and version of outgoing MADs should be provided. agent_id is
        returned."""
        rmpp_version = 1 if mgmt_class == IBA.MAD_SUBNET_ADMIN else 0;
        qpn = 0 if (mgmt_class == IBA.MAD_SUBNET or
                    mgmt_class == IBA.MAD_SUBNET_DIRECTED) else 1;
        return self._ioctl_register_agent(qpn,mgmt_class,mgmt_version,
                                          (0x00,0x14,0x05),rmpp_version,
                                          [0]*4);

    def _cache_make_ah(self,path):
        """Construct the address handle for umad and cache it in the path
        class"""
        assert(path.end_port == self.parent);
        if path.has_grh:
            res = self.ib_mad_addr_t.pack(cpu_to_be32(path.dqpn),
                                          cpu_to_be32(path.qkey),
                                          cpu_to_be16(path.DLID),
                                          path.SL,
                                          path.path_bits,
                                          1,
                                          path.SGID_index,
                                          path.hop_limit,
                                          path.traffic_class,
                                          path.DGID,
                                          cpu_to_be32(path.flow_label),
                                          path.pkey_index);
        else:
            res = self.ib_mad_addr_local_t.pack(cpu_to_be32(path.dqpn),
                                                cpu_to_be32(path.qkey),
                                                cpu_to_be16(path.DLID),
                                                path.SL,
                                                path.SLID_bits,
                                                path.pkey_index);
        path._cache_umad_ah = res;
        return res;

    # The kernel API is lame, don't use the timers. Send all MADs with 0
    # timeout and rely on our own code to match things up. It isn't clear that
    # agent_id is actually useful except to pick QP1 or QP0.
    def sendto(self,buf,path):
        '''Send a MAD packet'''
        try:
            addr = path._cache_umad_ah;
        except:
            addr = self._cache_make_ah(path);

        self.ib_user_mad_t.pack_into(self.sbuf,0,
                                     path.umad_agent_id,0,0,0,len(buf),
                                     addr);
        del self.sbuf[64:];
        self.sbuf.extend(buf);
        self.dev.write(self.sbuf);

    def recvfrom(self):
        '''Recv a MAD packet into buf. Returns (buf,path).'''
        buf = bytearray(320);
        rc = self.dev.readinto(buf);

        path = rdma.path.IBPath(self.parent);
        (path.umad_agent_id,status,timeout_ms,retries,length,
         path._cache_umad_ah) = self.ib_user_mad_t.unpack_from(bytes(buf),0);
        path.__class__ = LazyIBPath;

        if status != 0:
            # With a 0 timeout this should never happen.
            raise RDMAError("umad send failure code=%d for %s"%(status,repr(buf)));
        return (buf[64:],path);

    def _genError(self,buf,path):
        """Sadly the kernel can return EIO if it could not process the MAD,
        eg if you ask for PortInfo of the local CA with an invalid attributeID
        the Mellanox driver will return EIO rather than construct an error
        MAD. I consider this to be a bug in the kernel, but we fix it here
        by constructing an error MAD."""
        buf[3] = buf[3] | IBA.MAD_METHOD_RESPONSE;
        buf[4] = 0;
        buf[5] = IBA.MAD_STATUS_INVALID_ATTR_OR_MODIFIER; # Guessing.
        path = copy.copy(path);
        path.reverse();
        return (buf,path);

    def _execute(self,buf,path):
        """Send the fully formed MAD in buf to path and copy the reply
        into buf. Return path of the reply. This is a synchronous method, all
        MADs received during this call are discarded until the reply is seen."""
        rmatch = self._getReplyMatchKey(buf);
        try:
            self.sendto(buf,path);
        except IOError:
            return self._genError(buf,path);

        # FIXME: Timeout/resend
        while True:
            rbuf,rpath = self.recvfrom();
            if rmatch == self._getMatchKey(rbuf):
                return (rbuf,rpath);

    def __repr__(self):
        return "<%s.%s object for %s at 0x%x>"%\
               (self.__class__.__module__,
                self.__class__.__name__,
                self.parent,
                id(self));

