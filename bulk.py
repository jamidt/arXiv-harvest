import requests
import xml.etree.ElementTree as ET
import time
import json
import logging.config
import re

__LOG_CONF = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

logging.config.dictConfig(__LOG_CONF)
logger = logging.getLogger(__name__)


TOP_URL = "http://export.arxiv.org/oai2?verb=ListRecords&set={field}&metadataPrefix=arXiv"
TOKEN_URL = "http://export.arxiv.org/oai2?verb=ListRecords&resumptionToken={token}"


def xml2json(xml: ET.Element) -> (dict, str):
    json_dict = dict()
    list_records = xml.find("{http://www.openarchives.org/OAI/2.0/}ListRecords")
    for arxiv_entry in list_records.iter("{http://arxiv.org/OAI/arXiv/}arXiv"):
        id = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}id").text
        abstract = arxiv_entry.find("{http://arxiv.org/OAI/arXiv/}abstract").text
        json_dict[id] = abstract
    token = list_records.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken").text
    logger.info("Found token: {}".format(token))
    return json_dict, token


def get_delay(page: str) -> int:
    delay = re.search(r"Retry after (\d*) seconds", page).group(1)
    return int(delay)


class ArXivRequestError(Exception):
    pass


class ArXivRequest(object):
    def __init__(self, depth: int=None, **kwargs):
        if "token" in kwargs:
            url = TOKEN_URL.format(token=kwargs["token"])
        elif "field" in kwargs:
            url = TOP_URL.format(field=kwargs["field"])
        else:
            msg = ", ".join(kwargs)
            raise ArXivRequestError("Arguments wrong: {}".format(msg))

        count = 0
        self.json_data = dict()
        token = 0
        while token is not None and count != depth:
            logger.info("Get url: {}".format(url))
            req = requests.get(url)
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

    def save(self, filename):
        logger.debug("Save to file {}".format(filename))
        with open(filename, "w") as f:
            json.dump(self.json_data, f)
