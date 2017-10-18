import requests
import xml.etree.ElementTree as ET
import time
import json
import logging.config
import re
import os.path
from queue import Queue


logger = logging.getLogger(__name__)

TOP_URL = "http://export.arxiv.org/oai2?verb=ListRecords&set={field}&metadataPrefix=arXiv"
TOKEN_URL = "http://export.arxiv.org/oai2?verb=ListRecords&resumptionToken={token}"


def xml2json(xml: ET.Element) -> (dict, str):
    """
    Parses the xml formated request
    :param xml:
    :return: pair of a dictionary with all entries and if a token is found the string of the token and otherwise None
    """
    json_dict = dict()
    list_records = xml.find("{http://www.openarchives.org/OAI/2.0/}ListRecords")
    for arxiv_entry in list_records.iter("{http://arxiv.org/OAI/arXiv/}arXiv"):
        id = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}id").text
        abstract = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}abstract").text
        title = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}title").text
        json_dict[id] = {"title": title, "abstract": abstract}
    token = list_records.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken")
    if token is not None:
        token = token.text
        logger.info("Found token: {}".format(token))
    return json_dict, token


def get_delay(page: str) -> int:
    """
    Parse the web page in case of a 503 status and return the required delay time in seconds.
    :param page: String of the web page
    :return: Delay time in seconds
    """
    delay = re.search(r"Retry after (\d*) seconds", page).group(1)
    return int(delay)


class ArXivError(Exception):
    pass


class ArXivIter(object):
    def __init__(self, field: str, depth: int=None, write_tries: int=10):
        logger.debug("Starging iterator in {}".format(field))
        self.url = TOP_URL.format(field=field)
        self.write_tries = write_tries
        self.depth = depth or -1
        self.queue = Queue()
        self.count = 0
        self.token = 0

    def __iter__(self):
        return self

    def __next__(self):
        if not self.queue.empty():
            return self.queue.get()

        elif self.token is not None and self.count != self.depth:
            try:
                req = requests.get(self.url)
            except requests.RequestException as err:
                logger.error(err)
                raise ArXivError from err

            while req.status_code == 503:
                wait = get_delay(req.text) + 5
                logger.info("Returned status 503, waiting for {} seconds".format(wait))
                time.sleep(wait)
                req = requests.get(self.url)

            self.count += 1
            xml = ET.fromstring(req.text)
            abstract_dict, self.token = xml2json(xml)

            for arxiv_id, entry in abstract_dict.items():
                self.queue.put((arxiv_id, entry))

            self.url = TOKEN_URL.format(token=self.token)
            return self.queue.get()
        else:
            raise StopIteration


class ArXiv2json(object):
    def __init__(self, filename: str, mode: str="w", tries: int=10):
        if mode == "x":
            if os.path.exists(filename):
                logger.debug("File already exists, ")
                for i in range(tries):
                    appended_filename = filename + str(i)
                    if not os.path.exists(appended_filename):
                        filename = appended_filename
                        break
                else:
                    err_msg = "Could not write to file after {} tries".format(tries)
                    logger.error(err_msg)
                    raise ArXivError(err_msg)
            logger.info("Save to file {}".format(filename))
        try:
            self.file = open(filename, "w")
        except FileExistsError as err:
            raise ArXivError from err
        self.file.write("{")
        self.is_first = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.write("}")
        self.file.close()

    def append(self, pair: (str, dict)):
        arxiv_id, values = pair
        put = '"{}": {}'.format(arxiv_id, json.dumps(values))
        if not self.is_first:
            put = ", " + put
        self.file.write(put)
