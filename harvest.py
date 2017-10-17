#!/usr/bin/env python3

"""
Grab meta data from the arXiv. This program only parses the abstracts
and stores them as a json file with the arXiv id as key.

Copyright 2017 Jan Schmidt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from bulk import ArXivRequest
import logging
import argparse


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download bulk of arXiv meta data")
    parser.add_argument("field", nargs='+', type=str)
    parser.add_argument("--depth", "-d", default=None, metavar="D",
                        help="Maximal number of search entries is D*1000", type=int)
    args = parser.parse_args()
    logger.info("Searching in {}".format(", ".join(args.field)))
    for field in args.field:
        logger.info("Field: {}".format(field))
        req = ArXivRequest(field=field, depth=args.depth)
        req.save("{}.json".format(field))
