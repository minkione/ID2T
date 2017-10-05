#! /usr/bin/env python3
import argparse
import sys

from ID2TLib.Controller import Controller


class LoadFromFile(argparse.Action):
    """
    Parses the parameter file given by application param -c/--config.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        with values as f:
            parser.parse_args(f.read().split(), namespace)


class CLI(object):
    def __init__(self):
        """
        Creates a new CLI object used to handle
        """
        # Reference to PcapFile object
        self.args = None
        self.attack_config = None

    def process_arguments(self):
        """
        Loads the application controller, the PCAP file statistics and if present, processes the given attacks. Evaluates
        given queries.
        """
        # Create ID2T Controller
        controller = Controller(self.args.input, self.args.tests)

        # Load PCAP statistics
        controller.load_pcap_statistics(self.args.export, self.args.recalculate, self.args.statistics)

        # Create statistics plots
        if self.args.plot is not None:
            controller.create_statistics_plot(self.args.plot)

        # Process attack(s) with given attack params
        if self.args.attack is not None:
            # If attack is present, load attack with params
            controller.process_attacks(self.args.attack)

        # Parameter -q without arguments was given -> go into query loop
        if self.args.query == [None]:
            controller.enter_query_mode()
        # Parameter -q with arguments was given -> process query
        elif self.args.query is not None:
            controller.process_db_queries(self.args.query, True)

    def parse_arguments(self, args):
        """
        Defines the allowed application arguments and invokes the evaluation of the arguments.

        :param args: The application arguments
        """
        # Create parser for arguments
        parser = argparse.ArgumentParser(description="Intrusion Detection Dataset Toolkit (ID2T) - A toolkit for "
                                         "injection of synthetically created attacks into PCAP datasets.",
                                         prog="id2t")
        # Define required arguments
        requiredNamed = parser.add_argument_group('required named arguments')
        requiredNamed.add_argument('-i', '--input', metavar="FILEPATH", help='path to the input pcap file', required=True)

        # Define optional arguments
        parser.add_argument('-c', '--config', metavar='FILEPATH', help='file containing parameters used as input.',
                            action=LoadFromFile, type=open)
        parser.add_argument('-e', '--export',
                            help='stores the statistics as a textfile with ending .stat into the dataset directory',
                            action='store_true', default=False)
        parser.add_argument('-a', '--attack', metavar="ATTACKNAME", action='append',
                            help='injects a new attack into the given dataset. '
                                 'Attacks parameters are: ip.src, ip.dst, ip.dns, mac.src, mac.dst, port.open, '
                                 'port.dst, port.src, packets.limit, attackers.count, attack.duration, victim.buffer, '
                                 'target.uri, target.host, packets.per-second, inject.at-timestamp, inject.after-pkt, '
                                 'port.dst.shuffle, port.dst.order-desc, ip.src.shuffle, port.src.shuffle', nargs='+')
        parser.add_argument('-r', '--recalculate',
                            help='forces to recalculate the statistics in case of an already existing statistics database.',
                            action='store_true', default=False)
        parser.add_argument('-s', '--statistics', help='print general file statistics to stdout.', action='store_true',
                            default=False)
        parser.add_argument('-p', '--plot', help='creates a plot of common dataset statistics', action='append',
                            nargs='?')
        parser.add_argument('-q', '--query', metavar="QUERY",
                            action='append', nargs='?',
                            help='queries the statistics database. If no query is provided, the application enters into query mode.')
        # Aidmar
        parser.add_argument('-t', '--tests', help='perform defects tests on input pcap file.', action='store_true')

        # Parse arguments
        self.args = parser.parse_args(args)

        # Either PCAP filepath or GUI mode must be enabled
        if not self.args.input:
            parser.error("Parameter -i/--input required. See available options with -h/--help ")

        self.process_arguments()

def main(args):
    """
    Creates a new CLI object and invokes the arguments parsing.

    :param args: The provided arguments
    """
    cli = CLI()
    # Check arguments
    cli.parse_arguments(args)

# Test main
"""def main_0(args):
    from scapy.utils import RawPcapReader
    from scapy.layers.inet import IP, Ether, TCP

    pkts = RawPcapReader("Win7_eternalblue_scan_vulnerable.pcap")
    for pkt in pkts:
        eth_frame = Ether(pkt[0])
        ip_pkt = eth_frame.payload
        tcp_pkt = ip_pkt.payload

        new_pkt = (eth_frame / ip_pkt / tcp_pkt)
        new_pkt.time = 0


        print(tcp_pkt.getfieldval("sport"))
"""



# Uncomment to enable calling by terminal
if __name__ == '__main__':
    main(sys.argv[1:])



