import os
import time

import ID2TLib.libpcapreader as pr

from ID2TLib.PcapFile import PcapFile
from ID2TLib.StatsDatabase import StatsDatabase


class Statistics:
    def __init__(self, pcap_file: PcapFile):
        """
        Creates a new Statistics object.

        :param pcap_file: A reference to the PcapFile object
        """
        # Fields
        self.pcap_filepath = pcap_file.pcap_file_path
        self.pcap_processor = None
        pcap_file_hash = pcap_file.get_file_hash()

        # Create folder for statistics database if required
        self.path_db = pcap_file.get_db_path()
        path_dir = os.path.dirname(self.path_db)
        if not os.path.isdir(path_dir):
            os.makedirs(path_dir)

        # Class instances
        self.stats_db = StatsDatabase(self.path_db)

    def load_pcap_statistics(self, flag_write_file: bool, flag_recalculate_stats: bool, flag_print_statistics: bool):
        """
        Loads the PCAP statistics for the file specified by pcap_filepath. If the database is not existing yet, the
        statistics are calculated by the PCAP file processor and saved into the newly created database. Otherwise the
        statistics are gathered directly from the existing database.

        :param flag_write_file: Indicates whether the statistics should be written addiotionally into a text file (True)
        or not (False)
        :param flag_recalculate_stats: Indicates whether eventually existing statistics should be recalculated
        :param flag_print_statistics: Indicates whether the gathered basic statistics should be printed to the terminal
        """
        # Load pcap and get loading time
        time_start = time.clock()

        # Inform user about recalculation of statistics and its reason
        if flag_recalculate_stats:
            print("Flag -r/--recalculate found. Recalculating statistics.")

        # Recalculate statistics if database not exists OR param -r/--recalculate was provided
        if (not self.stats_db.get_db_exists()) or flag_recalculate_stats:
            self.pcap_processor = pr.pcap_processor(self.pcap_filepath)
            self.pcap_processor.collect_statistics()
            self.pcap_processor.write_to_database(self.path_db)
            outstring_datasource = "by PCAP file processor."
        else:
            outstring_datasource = "from statistics database."

        # Load statistics from database
        self.file_info = self.stats_db.get_file_info()

        time_end = time.clock()
        print("Loaded file statistics in " + str(time_end - time_start)[:4] + " sec " + outstring_datasource)

        # Write statistics if param -e/--export provided
        if flag_write_file:
            self.write_statistics_to_file()

        # Print statistics if param -s/--statistics provided
        if flag_print_statistics:
            self.print_statistics()

    def get_file_information(self):
        """
        Returns a list of tuples, each containing a information of the file.

        :return: a list of tuples, each consisting of (description, value, unit), where unit is optional.
        """
        return [("Pcap file", self.pcap_filepath),
                ("#Packets", self.get_packet_count(), "packets"),
                ("Capture length", self.get_capture_duration(), "seconds"),
                ("Capture start", self.get_pcap_timestamp_start()),
                ("Capture end", self.get_pcap_timestamp_end())]

    def get_general_file_statistics(self):
        """
        Returns a list of tuples, each containing a file statistic.

        :return: a list of tuples, each consisting of (description, value, unit).
        """
        return [("Avg. packet rate", self.file_info['avgPacketRate'], "packets/sec"),
                ("Avg. packet size", self.file_info['avgPacketSize'], "kbytes"),
                ("Avg. packets sent", self.file_info['avgPacketsSentPerHost'], "packets"),
                ("Avg. bandwidth in", self.file_info['avgBandwidthIn'], "kbit/s"),
                ("Avg. bandwidth out", self.file_info['avgBandwidthOut'], "kbit/s")]

    @staticmethod
    def _write_list(desc_val_unit_list, func, line_ending="\n"):
        """
        Takes a list of tuples (statistic name, statistic value, unit) as input, generates a string of these three values
        and applies the function func on this string.

        Before generating the string, it identifies text containing a float number, casts the string to a
        float and rounds the value to two decimal digits.

        :param desc_val_unit_list: The list of tuples consisting of (description, value, unit)
        :param func: The function to be applied to each generated string
        :param line_ending: The formatting string to be applied at the end of each string
        """
        for entry in desc_val_unit_list:
            # Convert text containing float into float
            (description, value) = entry[0:2]
            if isinstance(value, str) and "." in value:
                try:
                    value = float(value)
                except ValueError:
                    pass  # do nothing -> value was not a float
            # round float
            if isinstance(value, float):
                value = round(value, 2)
            # write into file
            if len(entry) == 3:
                unit = entry[2]
                func(description + ":\t" + str(value) + " " + unit + line_ending)
            else:
                func(description + ":\t" + str(value) + line_ending)

    def print_statistics(self):
        """
        Prints the basic file statistics to the terminal.
        """
        print("\nPCAP FILE INFORMATION ------------------------------")
        Statistics._write_list(self.get_file_information(), print, "")
        print("\nGENERAL FILE STATISTICS ----------------------------")
        Statistics._write_list(self.get_general_file_statistics(), print, "")
        print("\n")

    def write_statistics_to_file(self):
        """
        Writes the calculated basic statistics into a file.
        """

        def _write_header(title: str):
            """
            Writes the section header into the open file.

            :param title: The section title
            """
            target.write("====================== \n")
            target.write(title + " \n")
            target.write("====================== \n")

        target = open(self.pcap_filepath + ".stat", 'w')
        target.truncate()

        _write_header("PCAP file information")
        Statistics._write_list(self.get_file_information(), target.write)

        _write_header("General statistics")
        Statistics._write_list(self.get_general_file_statistics(), target.write)

        target.close()

    def get_capture_duration(self):
        """
        :return: The duration of the capture in seconds
        """
        return self.file_info['captureDuration']

    def get_pcap_timestamp_start(self):
        """
        :return: The timestamp of the first packet in the PCAP file
        """
        return self.file_info['timestampFirstPacket']

    def get_pcap_timestamp_end(self):
        """
        :return: The timestamp of the last packet in the PCAP file
        """
        return self.file_info['timestampLastPacket']

    def get_pps_sent(self, ip_address: str):
        """
        Calculates the sent packets per seconds for a given IP address.

        :param ip_address: The IP address whose packets per second should be calculated
        :return: The sent packets per seconds for the given IP address
        """
        packets_sent = self.stats_db.process_db_query("SELECT pktsSent from ip_statistics WHERE ipAddress=?", False,
                                                      (ip_address,))
        capture_duration = float(self.get_capture_duration())
        return int(float(packets_sent) / capture_duration)

    def get_packet_count(self):
        """
        :return: The number of packets in the loaded PCAP file
        """
        return self.file_info['packetCount']

    def get_statistics_database(self):
        """
        :return: A reference to the statistics database object
        """
        return self.stats_db

    def process_db_query(self, query_string_in: str, print_results: bool = False):
        """
        Executes a string identified previously as a query. This can be a standard SQL SELECT/INSERT query or a named
        query.

        :param query_string_in: The query to be processed
        :param print_results: Indicates whether the results should be printed to terminal
        :return: The result of the query
        """
        return self.stats_db.process_db_query(query_string_in, print_results)

    def is_query(self, value: str):
        """
        Checks whether the given string is a standard SQL query (SELECT, INSERT) or a named query.

        :param value: The string to be checked
        :return: True if the string is recognized as a query, otherwise False.
        """
        is_scalar_value = type(value) in (int, float)
        return not is_scalar_value and (
            any(x in value.lower().strip() for x in self.stats_db.get_all_named_query_keywords()) or
            any(x in value.lower().strip() for x in self.stats_db.get_all_sql_query_keywords()))