import Test.ID2TAttackTest as Test


class UnitTestPortscanAttack(Test.ID2TAttackTest):

    def test_portscan_basic(self):
        self.order_test([['PortscanAttack']])

    def test_portscan_revers_ports(self):
        self.order_test([['PortscanAttack', 'port.dst.order-desc=1']])

    def test_portscan_shuffle_dst_ports(self):
        self.order_test([['PortscanAttack', 'port.dst.shuffle=1']])

    def test_portscan_shuffle_src_ports(self):
        self.order_test([['PortscanAttack', 'port.dst.shuffle=1']])

    def test_portscan_ips_not_in_pcap(self):
        self.order_test([['PortscanAttack', 'ip.src=1.1.1.1', 'ip.dst=2.2.2.2']])
