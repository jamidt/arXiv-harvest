import requests
import xml.etree.ElementTree as ET
import time
import json
import logging.config
import re
import os.path


logger = logging.getLogger(__name__)


TOP_URL = "http://export.arxiv.org/oai2?verb=ListRecords&set={field}&metadataPrefix=arXiv"
TOKEN_URL = "http://export.arxiv.org/oai2?verb=ListRecords&resumptionToken={token}"


def xml2json(xml: ET.Element) -> (dict, str):
    json_dict = dict()
    list_records = xml.find("{http://www.openarchives.org/OAI/2.0/}ListRecords")
    for arxiv_entry in list_records.iter("{http://arxiv.org/OAI/arXiv/}arXiv"):
        id = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}id").text
        abstract = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}abstract").text
        title = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}title").text
        json_dict[id] = {"title": title, "abstract": abstract}
    token = list_records.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken").text
    logger.info("Found token: {}".format(token))
    return json_dict, token


def get_delay(page: str) -> int:
    delay = re.search(r"Retry after (\d*) seconds", page).group(1)
    return int(delay)


class ArXivRequestError(Exception):
    pass


class ArXivRequest(object):
    def __init__(self, field: str, depth: int=None, delay: int=10, write_tries: int=10):
        self.write_tries = write_tries
        url = TOP_URL.format(field=field)

        count = 0
        self.json_data = dict()
        token = 0
        while token is not None and count != depth:
            logger.info("Get url: {}".format(url))
            try:
                req = requests.get(url)
            except Exception as err:
                logger.error(err)
                for i in range(self.write_tries):
                    rescue_file = "resc-" + field + str(i) + ".json"
                    if not os.path.exists(rescue_file):
                        with open(rescue_file, "w") as fp:
                            json.dump(self.json_data, fp)
                        break
                else:
                    err_msg = "Can't write to rescue files after {} tries".format(self.write_tries)
                    raise ArXivRequestError(err_msg)
                logger.error("Writing all entries to file")

            logger.debug(req.url)
            if req.status_code == 503:
                wait = get_delay(req.text) + 5
                logger.warning("Returned status 503, waiting for {} seconds".format(wait))
                time.sleep(wait)
                continue
            else:
                count += 1
                xml = ET.fromstring(req.text)
                abstract_dict, token = xml2json(xml)
                self.json_data.update(abstract_dict)
                url = TOKEN_URL.format(token=token)
                time.sleep(delay)

    def save(self, filename: str, mode: str="x"):
        """
        Write json to file. If mode 'x' is provided and file already exists, a number is appended to
        the filename.
        :param filename:
        :param mode: Same as for open()
        """
        if os.path.exists(filename):
            for i in range(self.write_tries):
                appended_filename = filename + str(i)
                if not os.path.exists(appended_filename):
                    filename = appended_filename
                    break
            else:
                err_msg = "Could not write to file after {} tries".format(self.write_tries)
                logger.error(err_msg)
                raise ArXivRequestError(err_msg)
        logger.info("Save to file {}".format(filename))
        with open(filename, mode) as f:
            json.dump(self.json_data, f)
