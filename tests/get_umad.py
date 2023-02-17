# Copyright 2011 Obsidian Research Corp. GPLv2, see COPYING.
import unittest
import rdma

class get_umad_test(unittest.TestCase):
    def test_get(self):
        for I in rdma.get_devices():
            for Q in I.end_ports:
                with rdma.get_umad(Q) as X:
                    print(X);

if __name__ == '__main__':
    unittest.main()
