#!/usr/bin/env python3

# get modules
import time
import datetime
import random
from faker import Faker
from tzlocal import get_localzone
from pathlib import Path
import argparse
import uuid
import json
import sys

local = get_localzone()
faker = Faker()

# initiate the parse
parser = argparse.ArgumentParser()
parser.add_argument(
    "-r",
    "--rows",
    dest="row_number",
    help="number of records to generate",
    type=int,
    default=10,
)
parser.add_argument(
    "-e",
    "--event",
    dest="event_type",
    help="Logged event type",
    type=str,
    choices=["apachelog", "appevent"],
    default="apachelog",
)
parser.add_argument(
    "-o",
    "--output",
    dest="output_type",
    help="Write to a Log file or to STDOUT",
    type=str,
    choices=["LOG", "CONSOLE"],
    default="LOG",
)


def files_range(x):
    x = int(x)
    if x < 1:
        raise argparse.ArgumentTypeError("Minimum number of files is 1")
    if x > 100:
        raise argparse.ArgumentTypeError("Maximum number of files is 100")
    return x


parser.add_argument(
    "-f",
    "--files",
    dest="files_number",
    help="Number of files to write",
    type=files_range,
    default=1,
)


# read the args
args = parser.parse_args()

# sku
sku = {
    "Monthly": {"name": "Monthly", "code": "mthly20", "amount": 9.99},
    "Annual": {"name": "Annual", "code": "annua20", "amount": 99.99},
}


def main():

    # how many files
    for fls in range(args.files_number):
        # string for the output
        eventrows = ""
        timestr = time.strftime("%Y%m%d-%H%M%S")
        otime = datetime.datetime.now()

        # write 10 lines
        for ln in range(args.row_number):
            # set the ip
            ip = faker.ipv4()
            # set the timestamp
            dt = otime.strftime("%d/%b/%Y:%H:%M:%S")
            # set the time zone
            tz = datetime.datetime.now(local).strftime("%z")
            # get the method
            method = random.choices(
                population=["GET", "POST", "DELETE", "PUT"],
                weights=[0.6, 0.1, 0.1, 0.2],
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
            # userid
            userid = str(uuid.uuid1())
            # treatment
            treatment = random.choice(["A", "B"])
            # purchase
            if treatment == "A":
                purchase = random.choices(
                    population=[True, False], weights=[0.45, 0.55]
                )
            else:
                purchase = random.choices(
                    population=[True, False], weights=[0.55, 0.45]
                )
            if treatment == "A":
                item = sku[
                    random.choices(
                        population=["Monthly", "Annual"], weights=[0.50, 0.50]
                    )[0]
                ]
            else:
                item = sku[
                    random.choices(
                        population=["Monthly", "Annual"], weights=[0.30, 0.70]
                    )[0]
                ]
            # add the apache log record to the event
            if args.event_type == "apachelog":
                eventrows += (
                    f'{ip} - - [{dt} {tz}] "{method} {uri} HTTP/1.0" {response} {byt}\n'
                )
            # add the appevent record
            elif args.event_type == "appevent":
                this_event = {
                    "userid": userid,
                    "timestamp": f"{dt} {tz}",
                    "treatment": treatment,
                    "purchase": purchase[0],
                    "ip": ip,
                }
                if purchase[0] == True:
                    this_event["item"] = item["name"]
                    this_event["amount"] = item["amount"]
                    this_event["sku"] = item["code"]
                eventrows += f"{json.dumps(this_event, ensure_ascii=False)}\n"

        # write out the file
        if args.output_type == "LOG":
            filename = f"{args.event_type}/access_log_{timestr}.log"
            print(fls+1, filename)
            Path(args.event_type).mkdir(parents=True, exist_ok=True)
            # write out the files
            with open(filename, "w", encoding="utf-8") as f:
                f.write(eventrows)
        # print to the console
        elif args.output_type == "CONSOLE":
            print(filename)
            if args.event_type == "apachelog":
                print(eventrows)
            elif args.event_type == "appevent":
                print(json.dumps(eventrows, ensure_ascii=False, indent=4))

        if fls != args.files_number-1:
            time.sleep(30)


if __name__ == "__main__":
    main()
