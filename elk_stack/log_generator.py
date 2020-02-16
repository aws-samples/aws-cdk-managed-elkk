#!/usr/bin/env python

# get modules
import time
import datetime
import pytz

# import numpy
import random
import gzip
import zipfile
import sys
import argparse
from faker import Faker
from random import randrange
from tzlocal import get_localzone

local = get_localzone()

class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


parser = argparse.ArgumentParser(__file__, description="Log Generator")
parser.add_argument(
    "--output",
    "-o",
    dest="output_type",
    help="Write to a Log file, a gzip file or to STDOUT",
    choices=["LOG", "GZ", "CONSOLE"],
)
parser.add_argument(
    "--num",
    "-n",
    dest="num_lines",
    help="Number of lines to generate (0 for infinite)",
    type=int,
    default=1,
)
parser.add_argument(
    "--prefix", "-p", dest="file_prefix", help="Prefix the output file name", type=str
)
parser.add_argument(
    "--sleep",
    "-s",
    help="Sleep this long between lines (in seconds)",
    default=0.0,
    type=float,
)

args = parser.parse_args()

log_lines = args.num_lines
file_prefix = args.file_prefix
output_type = args.output_type

faker = Faker()

timestr = time.strftime("%Y%m%d-%H%M%S")
otime = datetime.datetime.now()

outFileName = (
    "access_log_" + timestr + ".log"
    if not file_prefix
    else file_prefix + "_access_log_" + timestr + ".log"
)

for case in switch(output_type):
    if case("LOG"):
        f = open(outFileName, "w")
        break
    if case("GZ"):
        f = gzip.open(outFileName + ".gz", "w")
        break
    if case("CONSOLE"):
        pass
    if case():
        f = sys.stdout

flag = True
while flag:
    if args.sleep:
        increment = datetime.timedelta(seconds=args.sleep)
    else:
        increment = datetime.timedelta(seconds=random.randint(30, 300))
    otime += increment

    # set the ip
    ip = faker.ipv4()
    # set the timestamp
    dt = otime.strftime("%d/%b/%Y:%H:%M:%S")
    # set the time zone
    tz = datetime.datetime.now(local).strftime("%z")
    # get the method
    method = random.choices(
        population=["GET", "POST", "DELETE", "PUT"], weights=[0.6, 0.1, 0.1, 0.2]
    )[0]
    # generate the uri
    uri = random.choice(
        [
            "/list",
            "/wp-content",
            "/wp-admin",
            "/explore",
            "/search/tag/list",
            "/app/main/posts",
            "/posts/posts/explore",
            f"/apps/cart.jsp?appID={str(random.randint(1000, 10000))}",
        ]
    )
    # generate a response
    response = random.choices(
        population=[200, 404, 500, 301], weights=[0.9, 0.04, 0.02, 0.04]
    )[0]
    # generate the byte size
    byt = int(random.gauss(5000, 50))
    # write out the logs
    f.write(f'{ip} - - [{dt} {tz}] "{method} {uri} HTTP/1.0" {response} {byt}\n')
    f.flush()

    log_lines = log_lines - 1
    flag = False if log_lines == 0 else True
    if args.sleep:
        time.sleep(args.sleep)
