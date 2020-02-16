#!/usr/bin/env python3

# get modules
import time
import datetime
import random
from faker import Faker
from tzlocal import get_localzone
from pathlib import Path

local = get_localzone()
faker = Faker()
timestr = time.strftime("%Y%m%d-%H%M%S")
otime = datetime.datetime.now()

def main():
    
    # open the new logfile
    Path("log").mkdir(parents=True, exist_ok=True)
    f = open(f"log/access_log_{timestr}.log", "w")

    # write 10 lines
    for ln in range(10):
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

if __name__ == "__main__":
    main()