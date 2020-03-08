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

local = get_localzone()
faker = Faker()
timestr = time.strftime("%Y%m%d-%H%M%S")
otime = datetime.datetime.now()

# initiate the parse
parser = argparse.ArgumentParser()
parser.add_argument(
    "-r", "-rows", help="number of records to generate", type=int, default=10
)
parser.add_argument(
    "-e",
    "-event",
    help="Simulate app events",
    type=str,
    default="apachelog",
    choices=["apachelog", "appevent"],
)

# read the args
args = vars(parser.parse_args())


def main():

    # open the new logfile
    Path("log").mkdir(parents=True, exist_ok=True)
    # set the filename
    if args["e"] == "appevent":
        filename = f"log/access_log_{timestr}.log"
        appevent = []
    else:
        f = open(f"log/access_log_{timestr}.log", "w")

    # write 10 lines
    for ln in range(args["r"]):
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
        # userid
        userid = str(uuid.uuid1())
        # treatment
        treatment = random.choice(["A", "B"])
        # purchase
        if treatment == "A":
            purchase = random.choices(population=["Yes", "No"], weights=[0.45, 0.55])
        else:
            purchase = random.choices(population=["Yes", "No"], weights=[0.55, 0.45])
        # item and amount
        if purchase == "No":
            item = "None"
            amount = 0
        else:
            if treatment == "B":
                item = random.choices(
                    population=["Monthly", "Annual"], weights=[0.30, 0.70]
                )
            else:
                item = random.choices(
                    population=["Monthly", "Annual"], weights=[0.50, 0.50]
                )
            if item == "Monthly":
                amount = 9.99
            else:
                amount = 99.99

        # write out the logs
        if args["e"] == "appevent":
            appevent.append(
                {
                    "userid": userid,
                    "timstamp": f"{dt} {tz}",
                    "treatment": treatment,
                    "purchase": purchase[0],
                    "item": item[0],
                    "amount": amount,
                }
            )
        else:
            f.write(
                f'{ip} - - [{dt} {tz}] "{method} {uri} HTTP/1.0" {response} {byt}\n'
            )
            f.flush()

    # write out the json for appevent
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(appevent, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
