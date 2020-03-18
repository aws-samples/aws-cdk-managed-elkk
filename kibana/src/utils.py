"""
utils
-------
"""
import logging
import json
import base64
from typing import Optional, Tuple, Union

import requests
import boto3
from io import BytesIO
from urllib.parse import urlencode

from settings import (
    AES_DOMAIN_ENDPOINT,
    CLOUDFRONT_CACHE_URL,
    KIBANA_BUCKET,
    S3_MAX_AGE,
    LOG_LEVEL,
    CACHEABLE_TYPES,
    ACCEPTED_HEADERS,
    METHOD_MAP,
    LOGGING_LEVELS,
)

if len(logging.getLogger().handlers) > 0:
    # The Lambda environment pre-configures a handler logging to stderr.
    # If a handler is already configured,
    # `.basicConfig` does not execute. Thus we set the level directly.
    logging.getLogger().setLevel(LOGGING_LEVELS[LOG_LEVEL])
else:
    logging.basicConfig(level=LOGGING_LEVELS[LOG_LEVEL])
logger = logging.getLogger()


s3 = boto3.client("s3")


def clean_body(event: dict) -> Optional[dict]:
    request_body = event.get("body")
    if event.get("isBase64Encoded", False) is True:
        request_body = base64.b64decode(request_body)
    try:
        request_body = request_body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        pass
    return request_body


def generate_url(event: dict) -> Tuple[str, Optional[str]]:
    path = event["path"]
    params = None
    if event.get("queryStringParameters"):
        if "path" in event["queryStringParameters"].keys():
            path = f'/{event["queryStringParameters"]["path"]}'
            params = None
        else:
            # Kibana likes to use multi-value query string parameters, so make
            # sure we urlencode the multi-value version of the
            # queryStringParameters and set "doseq=True" to set the multiple
            # values back into the request URL
            params = urlencode(event["multiValueQueryStringParameters"], doseq=True)
    if params:
        url = f"{AES_DOMAIN_ENDPOINT}{path}?{params}"
    else:
        url = f"{AES_DOMAIN_ENDPOINT}{path}"
    return url, params


def exception_response(
    e: requests.RequestException,
    body: Union[str, bytes, dict],
    params: Optional[str],
    clean_headers: dict,
):
    try:
        error = str(e.response.reason)
        status_code = str(e.response.status_code)
        headers = dict(e.response.headers)
    except AttributeError:
        error = str(e)
        status_code = "500"
        headers = dict()
    data = {
        "error": error,
        "request_body": body,
        "request_params": params,
        "request_headers": clean_headers,
    }
    data = json.dumps(data)
    headers["Cache-Control"] = "max-age=0"
    response = {
        "statusCode": status_code,
        "body": data.encode("utf-8"),
        "headers": headers,
    }
    response["headers"]["Content-Type"] = "application/json"
    logger.error(response)
    return response


def error_response():
    data = json.dumps({"error": "Environment incorrectly configured"})
    response = {
        "statusCode": "500",
        "body": data.encode("utf-8"),
        "headers": {"Content-Type": "application/json", "Cache-Control": "max-age=0"},
    }
    logger.error(response)
    return response


def redirect_to_object(data: bytes, event: dict, content_type: str):
    data = BytesIO(data)
    bucket_path = f'bucket-cached{event["path"]}'
    s3.upload_fileobj(
        data, KIBANA_BUCKET, bucket_path, ExtraArgs={"ContentType": content_type}
    )
    response = {
        "statusCode": "301",
        "body": None,
        "headers": {
            "Location": f'{CLOUDFRONT_CACHE_URL}{event["path"]}',
            "Cache-Control": f"max-age={S3_MAX_AGE}",
        },
    }
    logger.info(response)
    return response


def proxied_request(data: Union[bytes, str], content_type: str):
    data = base64.b64encode(data).decode("utf-8")
    return {
        "statusCode": "200",
        "body": data,
        "headers": {"Content-Type": content_type, "Cache-Control": "max-age=0"},
        "isBase64Encoded": True,
    }


def proxy_headers(event: dict) -> dict:
    return {
        k: v
        for k, v in event["headers"].items()
        if k.lower().startswith("x-amz")
        or k.lower().startswith("kbn-")
        or k.lower() in ACCEPTED_HEADERS
    }


def valid_request():
    return all([CLOUDFRONT_CACHE_URL, AES_DOMAIN_ENDPOINT, KIBANA_BUCKET])


def choose_request_func(event: dict) -> callable:
    if (
        event.get("queryStringParameters")
        and "method" in event["queryStringParameters"].keys()
    ):
        return METHOD_MAP[event["queryStringParameters"]["method"].lower()]
    else:
        return METHOD_MAP[event["httpMethod"].lower()]


def send_to_es(
    url: str, body: dict, headers: dict, request_func: callable
) -> Tuple[Union[bytes, str], str]:
    # send the request to ES
    response = request_func(url, data=body, headers=headers)
    # raise an exception if the status code of the response from ES is
    # >= 400
    response.raise_for_status()
    # because we can deal with JSON or binary data, use the raw response
    # content attribute
    data = response.content
    # get the content-type returned by ES to send back to API Gateway
    content_type = response.headers.get("content-type", "").lower()
    # log a dictionary containing all of this function's arguments, as well as
    # the value of `data` and `content_type`
    logger.debug(locals())
    # return the response data and the content_type from ElasticSearch
    return data, content_type
