import requests
from xml.etree import ElementTree
import time
import json
import logging.config
import re
import os.path
from queue import Queue
import math


logger = logging.getLogger(__name__)

TOP_URL = "http://export.arxiv.org/oai2?verb=ListRecords&set={field}&metadataPrefix=arXiv"
TOKEN_URL = "http://export.arxiv.org/oai2?verb=ListRecords&resumptionToken={token}"


def xml2json(xml: ElementTree.Element) -> (dict, str):
    """
    Parses the xml formatted request
    :param xml:
    :return: pair of a dictionary with all entries and if a token is found the string of the token and otherwise None
    """
    json_dict = dict()
    list_records = xml.find("{http://www.openarchives.org/OAI/2.0/}ListRecords")
    for arxiv_entry in list_records.iter("{http://arxiv.org/OAI/arXiv/}arXiv"):
        arxiv_id = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}id").text
        abstract = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}abstract").text
        title = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}title").text
        categories = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}categories").text.split()
        json_dict[arxiv_id] = {"title": title, "abstract": abstract, "categories": categories}
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
    def __init__(self, field: str, delay: int, batches: int=None, write_tries: int=10):
        reg = re.findall("\d*\|\d*", field)
        if reg:
            logger.debug("Starting at token {}".format(field))
            self.url = TOKEN_URL.format(token=field)
        else:
            logger.debug("Starting iterator in {}".format(field))
            self.url = TOP_URL.format(field=field)
        self.write_tries = write_tries
        self.depth = batches or -1
        self.queue = Queue()
        self.count = 0
        self.token = 0
        self.delay = delay
        self.last_update = 0

    def __iter__(self):
        return self

    def __next__(self):
        if not self.queue.empty():
            return self.queue.get()

        elif self.token is not None and self.count != self.depth:
            try:
                wait = time.time() - time.time() - self.delay
                if wait < 0:
                    time.sleep(math.fabs(wait))
                req = requests.get(self.url)
                self.last_update = time.time()
            except requests.RequestException as err:
                logger.error(err)
                raise ArXivError from err

            while req.status_code == 503:
                wait = get_delay(req.text) + 5
                logger.info("Returned status 503, waiting for {} seconds".format(wait))
                time.sleep(wait)
                req = requests.get(self.url)

            self.count += 1
            xml = ElementTree.fromstring(req.text)
            error = xml.find("{http://www.openarchives.org/OAI/2.0/}error")
            if error is not None:
                raise ArXivError(error.text)
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
        self.is_first = True
        self.file.write("{")

    def close(self):
        self.file.write("}")
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def append(self, pair: (str, dict)):
        arxiv_id, values = pair
        put = '"{}": {}'.format(arxiv_id, json.dumps(values))
        if self.is_first:
            self.is_first = False
        else:
            put = ", " + put
        self.file.write(put)
