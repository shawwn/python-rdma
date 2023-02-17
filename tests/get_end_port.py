# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
import unittest
import rdma
import rdma.IBA as IBA;

class get_end_port_test(unittest.TestCase):
    def test_guid(self):
        """Test IBA.GUID class"""
        pg = IBA.GUID("0002:c903:0000:1491");
        self.assertEqual(pg,pg);
        self.assertEqual(pg,IBA.GUID("0002:c903:0000:1491"));
        self.assertEqual(pg,IBA.GUID(pg));

    def test_gid(self):
        """Test IBA.GID class"""
        pg = IBA.GID("fe80::21c:23ff:fee2:946a");
        self.assertEqual(pg,pg);
        self.assertEqual(pg,IBA.GID("fe80::21c:23ff:fee2:946a"));
        self.assertEqual(pg,IBA.GID(pg));

    def test_good(self):
        """Test get_end_port calls that succeed.""";
        devices = rdma.get_devices();
        dev = devices.first();
        ep = dev.end_ports.first();
        self.assertEqual(rdma.get_end_port(),ep);
        self.assertEqual(rdma.get_end_port(dev.name),ep);
        self.assertEqual(rdma.get_end_port("%s/%s"%(dev.name,ep.port_id)),ep);
        self.assertEqual(rdma.get_end_port(ep.port_guid),ep)
        self.assertEqual(rdma.get_end_port("%s"%(ep.port_guid)),ep)
        self.assertEqual(rdma.get_end_port(ep.default_gid),ep)
        self.assertEqual(rdma.get_end_port("%s"%(ep.default_gid)),ep)

    def test_fail(self):
        """Test valid get_end_port calls that fail.""";
        devices = rdma.get_devices();
        dev = devices.first();
        self.assertRaises(rdma.RDMAError,
                          rdma.get_end_port,IBA.GID("::"));
        self.assertRaises(rdma.RDMAError,
                          rdma.get_end_port,IBA.GUID("0000:0000:0000:0000"));
        self.assertRaises(rdma.RDMAError,
                          rdma.get_end_port,"xxx");
        self.assertRaises(rdma.RDMAError,
                          rdma.get_end_port,"%s/99"%(dev.name));

if __name__ == '__main__':
    unittest.main()
