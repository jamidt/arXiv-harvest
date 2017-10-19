# arXiv-harvest

Download meta data from the arXiv. As described on the help page of the [arXiv](https://arxiv.org/help/oa/index), this tool uses the [Open Archives Initiative protocol](http://www.openarchives.org/OAI/2.0/openarchivesprotocol.htm) for downloading the data.


## Requirements

This tool uses [requests](https://github.com/requests/requests) and
Python 3.5 (I tend to use type annotations).


## Usage
```
python3 harvest.py q-bio math physics:cond-mat -b 4
```
downloads up to 4000 abstracts from each of the repos q-bio, math, and
physics:cond-mat and stores each in a json file, (e.g q-bio in
q-bio.json).

The program takes either the field from the arXiv (e.g
physics:astro-ph, math, ...) or a previously identified token in the
form `4789242|2001`. Remember to escape `|` in the terminal.

```
python3 harvest.py 4789242\|2001
```
downloads the entries starting at `2001`.

The delay between two requests is set by default to 10 seconds, but can
be adjusted with the `-d` parameter. ArXiv seems to block too frequent
fired requests and return a 503. However, even if a request gets a 503
response, the request will be resent after the time that is specified in
the response.

If the messages clutter the screen to much, adjust the logger level in
logger_conf.json.

## License
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
