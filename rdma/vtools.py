# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
;

import collections;
import mmap;
import math
import select;
import rdma.tools;
import rdma.ibverbs as ibv;

class BufferPool(object):
    """Hold onto a block of fixed size buffers and provide some helpers for
    using them as send and receive buffers with a QP.

    This can be used to provide send buffers for a QP, as well as receive
    buffers for a QP or a SRQ. Generally the *qp* argument to methods of this
    class can be a :class:`rdma.ibverbs.QP` or :class:`rdma.ibverbs.SRQ`."""
    #: Constant value to set *wr_id* to when it is not being used.
    NO_WR_ID = 0xFFFFFFFF;
    #: Constant value to or into *wr_id* to indicate it was posted as a recv.
    RECV_FLAG = 0;
    #: Mask to convert a *wr_id* back into a *buf_idx*.
    BUF_ID_MASK = 0;
    _mr = None;
    _mem = None;
    #: `deque` of buffer indexes.
    _buffers = None;
    #: Size of a single buffer.
    size = 0;
    #: Number of buffers.
    count = 0;

    def __init__(self,pd,count,size):
        """A :class:`rdma.ibverbs.MR` is created in *pd* with *count* buffers of
        *size* bytes."""
        self.count = count;
        self.size = size;
        self._mem = mmap.mmap(-1,count*size);
        self._mr = pd.mr(self._mem,ibv.IBV_ACCESS_LOCAL_WRITE |
                         ibv.IBV_ACCESS_LOCAL_WRITE);
        self._buffers = collections.deque(range(count),count);
        self.RECV_FLAG = 1 << (int(math.log(count,2))+1)
        self.BUF_ID_MASK = self.RECV_FLAG-1

    def close(self):
        """Close held objects"""
        if self._mr is not None:
            self._mr.close();
            self._mr = None;
        if self._mem is not None:
            self._mem.close();
            self._mem = None;

    def pop(self):
        """Return a new buffer index."""
        return self._buffers.pop();

    def post_recvs(self,qp,count):
        """Post *count* buffers for receive to *qp*, which may be any object
        with a `post_recv` method."""
        if count == 0:
            return;

        wr = [];
        for I in range(count):
            buf_idx = self._buffers.pop();
            wr.append(ibv.recv_wr(wr_id=buf_idx | self.RECV_FLAG,
                                  sg_list=self.make_sge(buf_idx,self.size)));
        qp.post_recv(wr);

    def finish_wcs(self,qp,wcs):
        """Process work completion list *wcs* to recover buffers attached to
        completed work and re-post recv buffers to qp. Every work request with
        an attached buffer must have a signaled completion to recover the
        buffer.

        *wcs* may be a single wc.

        :raises rdma.ibverbs.WCError: For WC's marked as error."""
        new_recvs = 0;
        err = None;
        if isinstance(wcs,ibv.wc):
            wcs = (wcs,);
        for wc in wcs:
            if wc is None:
                continue;

            # Note, we cannot rely on the opcode here to determine
            # RQ/SQ for the buffer, so it is encoded in the wr_id.
            if wc.wr_id != self.NO_WR_ID:
                self._buffers.append(wc.wr_id & self.BUF_ID_MASK);
                if wc.wr_id & self.RECV_FLAG:
                    new_recvs = new_recvs + 1;

            if wc.status != ibv.IBV_WC_SUCCESS and err is None:
                err = wc;
        self.post_recvs(qp,new_recvs);

        if err is not None:
            rq = None
            if wc.wr_id != self.NO_WR_ID:
                rq = wc.wr_id & self.RECV_FLAG;
            raise ibv.WCError(err,None,obj=qp,is_rq=rq);

    def make_send_wr(self,buf_idx,buf_len,path=None):
        """Return a :class:`rdma.ibverbs.send_wr` for *buf_idx* and path.
        If *path* is `None` then the wr does not contain path information
        (eg for connected QPs)"""
        if path is not None:
            return ibv.send_wr(wr_id=buf_idx,
                               sg_list=self.make_sge(buf_idx,buf_len),
                               opcode=ibv.IBV_WR_SEND,
                               send_flags=ibv.IBV_SEND_SIGNALED,
                               ah=self._mr.pd.ah(path),
                               remote_qpn=path.dqpn,
                               remote_qkey=path.qkey);
        else:
            return ibv.send_wr(wr_id=buf_idx,
                               sg_list=self.make_sge(buf_idx,buf_len),
                               opcode=ibv.IBV_WR_SEND,
                               send_flags=ibv.IBV_SEND_SIGNALED);

    def make_sge(self,buf_idx,buf_len):
        """Return a :class:`rdma.ibverbs.SGE` for *buf_idx*."""
        return self._mr.sge(buf_len,buf_idx*self.size);

    def copy_from(self,buf_idx,offset=0,length=0xFFFFFFFF):
        """Return a copy of buffer *buf_idx*. *buf_idx* may be a *wr_id*.

        :rtype: :class:`bytearray`"""
        buf_idx = buf_idx & self.BUF_ID_MASK;
        length = min(length,self.size - offset)
        return bytearray(self._mem[buf_idx*self.size + offset:
                                   buf_idx*self.size + offset + length]);

    def copy_to(self,buf,buf_idx,offset=0,length=0xFFFFFFFF):
        """Copy *buf* into the buffer *buf_idx*"""
        blen = len(buf)
        length = min(length,self.size - offset,blen)
        if isinstance(buf,bytearray):
            buf = bytes(buf);
        if blen > length:
            self._mem[buf_idx*self.size + offset:
                      buf_idx*self.size + offset + length] = buf[:blen];
        else:
            self._mem[buf_idx*self.size + offset:
                      buf_idx*self.size + offset + length] = buf;

class CQPoller(object):
    """Simple wrapper for a :class:`rdma.ibverbs.CQ` and
    :class:`rdma.ibverbs.CompChannel` to provide a blocking API for getting
    work completions."""
    _cq = None
    _cc = None
    _poll = None

    #: `True` if iteration was stopped due to a timeout
    timedout = False
    #: Value of :func:`rdma.tools.clock_monotonic` to stop iterating. This can
    #: be altered while iterating.
    wakeat = None

    def __init__(self,cq,async_events=True,solicited_only=False):
        """*cq* is the completion queue to read work completions from.
        If the *cq* does not have a completion channel then this will
        spin loop on *cq* otherwise it sleeps on the completion channel.

        If *async_events* is `True` then the async event queue will be
        monitored while sleeping."""
        self._cq = cq;
        self._solicited_only = solicited_only
        cc = cq.comp_chan;
        if cc is not None:
            self._cc = cc;
            self._poll = select.poll();
            cc.register_poll(self._poll);
            self._ctx = cq.ctx
            if async_events:
                self._ctx.register_poll(self._poll);

    def __iter__(self):
        return self.iterwc(self);

    def sleep(self,wakeat):
        """Go to sleep until the cq gets a completion. *wakeat* is the
        value of :func:`rdma.tools.clock_monotonic` after which the function
        returns `None`. Returns `True` if the completion channel triggered.

        If no completion channel is in use this just returns `True`.

        Note: It is necessary to call :meth:`rdma.ibverbs.CQ.req_notify`
        on the CQ, then poll the CQ before calling :meth:`sleep`. Otherwise
        the edge triggered nature of the completion channels can cause
        deadlock."""
        if self._poll is None:
            if wakeat is not None:
                timeout = wakeat - rdma.tools.clock_monotonic();
                if timeout <= 0:
                    return None;
            return True;
        while True:
            if wakeat is None:
                ret = self._poll.poll(-1);
            else:
                timeout = wakeat - rdma.tools.clock_monotonic();
                if timeout <= 0:
                    return None;
                ret = self._poll.poll(timeout*1000);
            if ret is None:
                return None;
            for I in ret:
                if self._cc.check_poll(I) is not None:
                    return True;
                if self._ctx.check_poll(I):
                    ev = self._ctx.get_async_event()
                    self._ctx.handle_async_event(ev);

    def iterwc(self,count=None,timeout=None,wakeat=None):
        """Generator that returns work completions from the CQ. If not `None`
        at most *count* wcs will be returned. *timeout* is the number of
        seconds this function can run for, and *wakeat* is the value of
        :func:`rdma.tools.clock_monotonic` after which iteration stops.

        :rtype: :class:`rdma.ibverbs.wc`"""
        self.timedout = False;
        self.wakeat = wakeat;
        if timeout is not None:
            self.wakeat = rdma.tools.clock_monotonic() + timeout;
        limit = -1;
        if count is not None:
            limit = count;
        while True:
            if limit == 0:
                return
            ret = self._cq.poll(1);
            while not ret:
                self._cq.req_notify(self._solicited_only);
                ret = self._cq.poll(1);
                if not ret and self.sleep(self.wakeat) is None:
                    self.timedout = True;
                    return
            for I in ret:
                yield I;
                if limit > 0:
                    limit = limit - 1;
