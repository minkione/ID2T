import os.path
from datetime import datetime
from xml.dom.minidom import *

import ID2TLib.Label as Label


class LabelManager:
    TAG_ROOT = 'LABELS'
    TAG_ATTACK = 'attack'
    TAG_ATTACK_NAME = 'attack_name'
    TAG_ATTACK_NOTE = 'attack_note'
    TAG_TIMESTAMP_START = 'timestamp_start'
    TAG_TIMESTAMP_END = 'timestamp_end'
    TAG_TIMESTAMP = 'timestamp'
    TAG_TIMESTAMP_HR = 'timestamp_hr'
    ATTR_VERSION = 'version_parser'

    # update this attribute if XML scheme was modified
    ATTR_VERSION_VALUE = '0.2'

    def __init__(self, filepath_pcap=None):
        """
        Creates a new LabelManager for managing the attack's labels.

        :param filepath_pcap: The path to the PCAP file associated to the labels.
        """
        self.labels = list()

        if filepath_pcap is not None:
            self.labelFilePath = filepath_pcap.strip('.pcap') + '_labels.xml'
            # only load labels if label file is existing
            if os.path.exists(self.labelFilePath):
                self._load_labels()

    def add_labels(self, labels):
        """
        Adds a label to the internal list of labels.

        :param labels: The labels to be added
        """
        if isinstance(labels, list):
            self.labels = self.labels + [labels]
        elif isinstance(labels, tuple):
            for l in labels:
                self.labels.append(l)
        else:
            self.labels.append(labels)

        # sorts the labels ascending by their timestamp
        self.labels.sort()

    def write_label_file(self, filepath=None):
        """
        Writes previously added/loaded labels to a XML file. Uses the given filepath as destination path, if no path is
        given, uses the path in labelFilePath.

        :param filepath: The path where the label file should be written to.
        """

        def get_subtree_timestamp(xml_tag_root, timestamp_entry) -> Element:
            """
            Creates the subtree for a given timestamp, consisting of the unix time format (seconds) and a human-readable
            output.

            :param xml_tag_root: The tag name for the root of the subtree
            :param timestamp_entry: The timestamp as unix time
            :return: The root node of the XML subtree
            """
            timestamp_root = doc.createElement(xml_tag_root)

            # add timestamp in unix format
            timestamp = doc.createElement(self.TAG_TIMESTAMP)
            timestamp.appendChild(doc.createTextNode(str(timestamp_entry)))
            timestamp_root.appendChild(timestamp)

            # add timestamp in human-readable format
            timestamp_hr = doc.createElement(self.TAG_TIMESTAMP_HR)
            timestamp_hr_text = datetime.fromtimestamp(int(timestamp_entry)).strftime('%Y-%m-%d %H:%M:%S')
            timestamp_hr.appendChild(doc.createTextNode(timestamp_hr_text))
            timestamp_root.appendChild(timestamp_hr)

            return timestamp_root

        if filepath is not None:
            self.labelFilePath = filepath.strip('.pcap') + '_labels.xml'

        # Generate XML
        doc = Document()
        node = doc.createElement(self.TAG_ROOT)
        node.setAttribute(self.ATTR_VERSION, self.ATTR_VERSION_VALUE)
        for label in self.labels:
            xml_tree = doc.createElement(self.TAG_ATTACK)

            # add attack to XML tree
            attack_name = doc.createElement(self.TAG_ATTACK_NAME)
            attack_name.appendChild(doc.createTextNode(str(label.attack_name)))
            xml_tree.appendChild(attack_name)
            attack_note = doc.createElement(self.TAG_ATTACK_NOTE)
            attack_note.appendChild(doc.createTextNode(str(label.attack_note)))
            xml_tree.appendChild(attack_note)

            # add timestamp_start to XML tree
            xml_tree.appendChild(get_subtree_timestamp(self.TAG_TIMESTAMP_START, label.timestamp_start))

            # add timestamp_end to XML tree
            xml_tree.appendChild(get_subtree_timestamp(self.TAG_TIMESTAMP_END, label.timestamp_end))

            node.appendChild(xml_tree)

        doc.appendChild(node)

        # Write XML to file
        file = open(self.labelFilePath, 'w')
        file.write(doc.toprettyxml())
        file.close()

    def _load_labels(self):
        """
        Loads the labels from an already existing label XML file located at labelFilePath (set by constructor).

        """
        print("Label file found. Loading labels...")
        dom = parse(self.labelFilePath)

        # Check if version of parser and version of file match
        version = dom.getElementsByTagName(self.TAG_ROOT)[0].getAttribute(self.ATTR_VERSION)
        if not version == self.ATTR_VERSION_VALUE:
            raise ValueError(
                "The file " + self.labelFilePath + " was created by another version of ID2TLib.LabelManager")

        # Parse attacks from XML file
        attacks = dom.getElementsByTagName(self.TAG_ATTACK)
        for a in attacks:
            attack_name = a.childNodes[1].firstChild.data
            attack_note = a.childNodes[3].firstChild.data
            timestamp_start = a.childNodes[5].childNodes[1].firstChild.data
            timestamp_end = a.childNodes[7].childNodes[1].firstChild.data
            label = Label.Label(attack_name, float(timestamp_start), float(timestamp_end), attack_note)
            self.labels.append(label)