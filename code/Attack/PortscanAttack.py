import logging
import csv

from random import shuffle, randint, choice, uniform

from lea import Lea

from Attack import BaseAttack
from Attack.AttackParameters import Parameter as Param
from Attack.AttackParameters import ParameterTypes

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
# noinspection PyPep8
from scapy.layers.inet import IP, Ether, TCP
import numpy as np

class PortscanAttack(BaseAttack.BaseAttack):
    # Aidmar - Values derived empirically from Nmap experiments.
    maxDefaultPPS = randint(300,500)
    minDefaultPPS = randint(5,10)

    # Aidmar
    def get_ports_from_nmap_service_dst(self, ports_num):
        """
        Read the most ports_num frequently open ports from nmap-service-tcp file to be used in the port scan.

        :return: Ports numbers to be used as default destination ports or default open ports in the port scan.
        """
        ports_dst = []
        spamreader = csv.reader(open('resources/nmap-services-tcp.csv', 'rt'), delimiter=',')
        for count in range(ports_num):
            # escape first row (header)
            next(spamreader)
            # save ports numbers
            ports_dst.append(next(spamreader)[0])
        # shuffle ports numbers partially
        if(ports_num==1000): # used for port.dst
            temp_array = [[0 for i in range(10)] for i in range(100)]
            port_dst_shuffled = []
            for count in range(0, 9):
                temp_array[count] = ports_dst[count * 100:count * 100 + 99]
                shuffle(temp_array[count])
                port_dst_shuffled += temp_array[count]
        else: # used for port.open
            shuffle(ports_dst)
            port_dst_shuffled = ports_dst
        return port_dst_shuffled

    def __init__(self, statistics, pcap_file_path):
        """
        Creates a new instance of the PortscanAttack.

        :param statistics: A reference to the statistics class.
        """
        # Initialize attack
        super(PortscanAttack, self).__init__(statistics, "Portscan Attack", "Injects a nmap 'regular scan'",
                                             "Scanning/Probing")

        # Define allowed parameters and their type
        self.supported_params = {
            Param.IP_SOURCE: ParameterTypes.TYPE_IP_ADDRESS,
            Param.IP_DESTINATION: ParameterTypes.TYPE_IP_ADDRESS,
            Param.PORT_SOURCE: ParameterTypes.TYPE_PORT,
            Param.PORT_DESTINATION: ParameterTypes.TYPE_PORT,
            Param.PORT_OPEN: ParameterTypes.TYPE_PORT,
            Param.MAC_SOURCE: ParameterTypes.TYPE_MAC_ADDRESS,
            Param.MAC_DESTINATION: ParameterTypes.TYPE_MAC_ADDRESS,
            Param.INJECT_AT_TIMESTAMP: ParameterTypes.TYPE_FLOAT,
            Param.INJECT_AFTER_PACKET: ParameterTypes.TYPE_PACKET_POSITION,
            Param.PORT_DEST_SHUFFLE: ParameterTypes.TYPE_BOOLEAN,
            Param.PORT_DEST_ORDER_DESC: ParameterTypes.TYPE_BOOLEAN,
            Param.IP_SOURCE_RANDOMIZE: ParameterTypes.TYPE_BOOLEAN,
            Param.PACKETS_PER_SECOND: ParameterTypes.TYPE_FLOAT,
            Param.PORT_SOURCE_RANDOMIZE: ParameterTypes.TYPE_BOOLEAN
        }

        # PARAMETERS: initialize with default values
        # (values are overwritten if user specifies them)
        most_used_ip_address = self.statistics.get_most_used_ip_address()
        if isinstance(most_used_ip_address, list):
            most_used_ip_address = most_used_ip_address[0]

        self.add_param_value(Param.IP_SOURCE, most_used_ip_address)
        self.add_param_value(Param.IP_SOURCE_RANDOMIZE, 'False')
        self.add_param_value(Param.MAC_SOURCE, self.statistics.get_mac_address(most_used_ip_address))

        random_ip_address = self.statistics.get_random_ip_address()
        # Aidmar - ip-dst should be valid and not equal to ip.src
        while not self.is_valid_ip_address(random_ip_address) or random_ip_address==most_used_ip_address:
            random_ip_address = self.statistics.get_random_ip_address()

        self.add_param_value(Param.IP_DESTINATION, random_ip_address)
        destination_mac = self.statistics.get_mac_address(random_ip_address)
        if isinstance(destination_mac, list) and len(destination_mac) == 0:
            destination_mac = self.generate_random_mac_address()
        self.add_param_value(Param.MAC_DESTINATION, destination_mac)
        self.add_param_value(Param.PORT_DESTINATION, self.get_ports_from_nmap_service_dst(1000))
        # Temporal value to be changed later accordint to the destination host open ports
        self.add_param_value(Param.PORT_OPEN, '1')
        self.add_param_value(Param.PORT_DEST_SHUFFLE, 'False')
        self.add_param_value(Param.PORT_DEST_ORDER_DESC, 'False')
        self.add_param_value(Param.PORT_SOURCE, randint(1024, 65535))
        self.add_param_value(Param.PORT_SOURCE_RANDOMIZE, 'False')

        #self.add_param_value(Param.PACKETS_PER_SECOND,
                             #(self.statistics.get_pps_sent(most_used_ip_address) +
                             # self.statistics.get_pps_received(most_used_ip_address)) / 2)
        # Aidmar
        self.add_param_value(Param.PACKETS_PER_SECOND,self.maxDefaultPPS)

        self.add_param_value(Param.INJECT_AFTER_PACKET, randint(0, self.statistics.get_packet_count()))

    def generate_attack_pcap(self):
        def update_timestamp(timestamp, pps, maxdelay):
            """
            Calculates the next timestamp to be used based on the packet per second rate (pps) and the maximum delay.

            :return: Timestamp to be used for the next packet.
            """
            # Aidmar
            # To imitate the bursty behavior of traffic
            randomdelay = Lea.fromValFreqsDict({1 / pps: 70, 2 / pps: 20, 5 / pps: 7, 10 / pps: 3})
            return timestamp + uniform(1/pps ,  randomdelay.random())

        # Aidmar
        def getIntervalPPS(complement_interval_pps, timestamp):
            """
            Gets the packet rate (pps) for a specific time interval.

            :param complement_interval_pps: an array of tuples (the last timestamp in the interval, the packet rate in the crresponding interval).
            :param timestamp: the timestamp at which the packet rate is required.
            :return: the corresponding packet rate (pps) .
            """
            for row in complement_interval_pps:
                if timestamp<=row[0]:
                    return row[1]
            return complement_interval_pps[-1][1] # in case the timstamp > capture max timestamp

        mac_source = self.get_param_value(Param.MAC_SOURCE)
        mac_destination = self.get_param_value(Param.MAC_DESTINATION)
        pps = self.get_param_value(Param.PACKETS_PER_SECOND)
        # Aidmar - unjustified distribution
        #randomdelay = Lea.fromValFreqsDict({1 / pps: 70, 2 / pps: 20, 5 / pps: 7, 10 / pps: 3})
        #maxdelay = randomdelay.random()

        # Aidmar - calculate complement packet rates of the background traffic for each interval
        complement_interval_pps = self.statistics.calculate_complement_packet_rates(pps)

        # Determine ports
        dest_ports = self.get_param_value(Param.PORT_DESTINATION)
        if self.get_param_value(Param.PORT_DEST_ORDER_DESC):
            dest_ports.reverse()
        elif self.get_param_value(Param.PORT_DEST_SHUFFLE):
            shuffle(dest_ports)
        if self.get_param_value(Param.PORT_SOURCE_RANDOMIZE):
            sport = randint(1, 65535)
        else:
            sport = self.get_param_value(Param.PORT_SOURCE)

        # Timestamp
        timestamp_next_pkt = self.get_param_value(Param.INJECT_AT_TIMESTAMP)
        # store start time of attack
        self.attack_start_utime = timestamp_next_pkt
        timestamp_prv_reply, timestamp_confirm = 0,0

        # Initialize parameters
        packets = []
        ip_source = self.get_param_value(Param.IP_SOURCE)
        ip_destination = self.get_param_value(Param.IP_DESTINATION)

        # Aidmar - check ip.src == ip.dst
        self.ip_src_dst_equal_check(ip_source, ip_destination)

        # Aidmar
        # Select open ports
        ports_open = self.get_param_value(Param.PORT_OPEN)
        if ports_open == 1:  # user did not specify open ports
            # the ports that were already used by ip.dst (direction in) in the background traffic are open ports
            ports_used_by_ip_dst = self.statistics.process_db_query(
                "SELECT portNumber FROM ip_ports WHERE portDirection='in' AND ipAddress='" + ip_destination + "'")
            if ports_used_by_ip_dst:
                ports_open = ports_used_by_ip_dst
            else: # if no ports were retrieved from database
                ports_open = self.statistics.process_db_query(
                    "SELECT portNumber FROM ip_ports GROUP BY portNumber ORDER BY SUM(portCount) DESC LIMIT "+str(randint(1,10)))
        # in case of one open port, convert ports_open to array
        if not isinstance(ports_open, list):
            ports_open = [ports_open]

        # Aidmar
        # Set MSS (Maximum Segment Size) based on MSS distribution of IP address
        source_mss_dist = self.statistics.get_mss_distribution(ip_source)
        if len(source_mss_dist) > 0:
            source_mss_prob_dict = Lea.fromValFreqsDict(source_mss_dist)
            source_mss_value = source_mss_prob_dict.random()
        else:
            source_mss_value = self.statistics.process_db_query("most_used(mssValue)")
        destination_mss_dist = self.statistics.get_mss_distribution(ip_destination)
        if len(destination_mss_dist) > 0:
            destination_mss_prob_dict = Lea.fromValFreqsDict(destination_mss_dist)
            destination_mss_value = destination_mss_prob_dict.random()
        else:
            destination_mss_value = self.statistics.process_db_query("most_used(mssValue)")

        # Set TTL based on TTL distribution of IP address
        source_ttl_dist = self.statistics.get_ttl_distribution(ip_source)
        if len(source_ttl_dist) > 0:
            source_ttl_prob_dict = Lea.fromValFreqsDict(source_ttl_dist)
            source_ttl_value = source_ttl_prob_dict.random()
        else:
            source_ttl_value = self.statistics.process_db_query("most_used(ttlValue)")
        destination_ttl_dist = self.statistics.get_ttl_distribution(ip_destination)
        if len(destination_ttl_dist) > 0:
            destination_ttl_prob_dict = Lea.fromValFreqsDict(destination_ttl_dist)
            destination_ttl_value = destination_ttl_prob_dict.random()
        else:
            destination_ttl_value = self.statistics.process_db_query("most_used(ttlValue)")

        # Aidmar
        # Set Window Size based on Window Size distribution of IP address
        source_win_dist = self.statistics.get_win_distribution(ip_source)
        if len(source_win_dist) > 0:
            source_win_prob_dict = Lea.fromValFreqsDict(source_win_dist)
            source_win_value = source_win_prob_dict.random()
        else:
            source_win_value = self.statistics.process_db_query("most_used(winSize)")
        destination_win_dist = self.statistics.get_win_distribution(ip_destination)
        if len(destination_win_dist) > 0:
            destination_win_prob_dict = Lea.fromValFreqsDict(destination_win_dist)
            destination_win_value = destination_win_prob_dict.random()
        else:
            destination_win_value = self.statistics.process_db_query("most_used(winSize)")

        # Aidmar
        minDelay,maxDelay, SDDelay = self.get_reply_delay(ip_destination)

        for dport in dest_ports:
            # Parameters changing each iteration
            if self.get_param_value(Param.IP_SOURCE_RANDOMIZE) and isinstance(ip_source, list):
                ip_source = choice(ip_source)

            # 1) Build request package
            request_ether = Ether(src=mac_source, dst=mac_destination)
            request_ip = IP(src=ip_source, dst=ip_destination, ttl=source_ttl_value)

            # Aidmar - random src port for each packet
            sport = randint(1, 65535)

            request_tcp = TCP(sport=sport, dport=dport,  window= source_win_value, flags='S', options=[('MSS', source_mss_value)])

            request = (request_ether / request_ip / request_tcp)

            # Aidmar
            request.time = timestamp_next_pkt
            # Append request
            packets.append(request)

            # 2) Build reply (for open ports) package
            if dport in ports_open:  # destination port is OPEN
                reply_ether = Ether(src=mac_destination, dst=mac_source)
                reply_ip = IP(src=ip_destination, dst=ip_source, ttl=destination_ttl_value, flags='DF')
                reply_tcp = TCP(sport=dport, dport=sport, seq=0, ack=1, flags='SA', window=destination_win_value,
                                    options=[('MSS', destination_mss_value)])
                reply = (reply_ether / reply_ip / reply_tcp)
                # Aidmar - edit name timestamp_reply
                timestamp_reply = timestamp_next_pkt + uniform(minDelay, maxDelay)
                while (timestamp_reply <= timestamp_prv_reply):
                    timestamp_reply = timestamp_prv_reply + uniform(minDelay, maxDelay)
                timestamp_prv_reply = timestamp_reply

                reply.time = timestamp_reply
                # B_A_packets.append(reply)
                packets.append(reply)

                # requester confirms
                confirm_ether = request_ether
                confirm_ip = request_ip
                confirm_tcp = TCP(sport=sport, dport=dport, seq=1, window=0, flags='R')
                confirm = (confirm_ether / confirm_ip / confirm_tcp)
                # Aidmar - edit name timestamp_confirm
                timestamp_confirm = timestamp_reply + uniform(minDelay, maxDelay)
                confirm.time = timestamp_confirm
                # A_B_packets.append(confirm)
                packets.append(confirm)

                # else: destination port is NOT OPEN -> no reply is sent by target

            # Aidmar
            pps = max(getIntervalPPS(complement_interval_pps, timestamp_next_pkt),self.minDefaultPPS)
            timestamp_next_pkt = update_timestamp(timestamp_next_pkt, pps, minDelay)

        # store end time of attack
        self.attack_end_utime = packets[-1].time

        # write attack packets to pcap
        pcap_path = self.write_attack_pcap(sorted(packets, key=lambda pkt: pkt.time))

        # return packets sorted by packet time_sec_start
        return len(packets), pcap_path
