# modules
import os
import logging
import requests
import json
import base64
from typing import Optional, Tuple, Union
import boto3
from io import BytesIO
from urllib.parse import urlencode

s3 = boto3.client("s3")

# settings ...
AES_DOMAIN_ENDPOINT = os.environ.get("AES_DOMAIN_ENDPOINT")
CLOUDFRONT_CACHE_URL = os.environ.get("CLOUNDFRONT_CACHE_URL")
KIBANA_BUCKET = os.environ.get("KIBANA_BUCKET")
S3_MAX_AGE = os.environ.get("S3_MAX_AGE", "2629746")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "warning")
CACHEABLE_TYPES = ["image", "javascript", "css", "font"]
ACCEPTED_HEADERS = ["accept", "host", "content-type"]
METHOD_MAP = {
    "get": requests.get,
    "options": requests.options,
    "put": requests.put,
    "post": requests.post,
    "head": requests.head,
    "patch": requests.patch,
    "delete": requests.delete,
}
LOGGING_LEVELS = {
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "fatal": logging.FATAL,
}

# utils
if len(logging.getLogger().handlers) > 0:
    # The Lambda environment pre-configures a handler logging to stderr.
    # If a handler is already configured,
    # `.basicConfig` does not execute. Thus we set the level directly.
    logging.getLogger().setLevel(LOGGING_LEVELS[LOG_LEVEL])
else:
    logging.basicConfig(level=LOGGING_LEVELS[LOG_LEVEL])
logger = logging.getLogger()


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


# the lambda handler
# noinspection PyUnusedLocal
def lambda_handler(event: dict, context: object) -> dict:
    """
    Accept the incoming proxy integration event from API Gateway and forward
    the request to the Amazon ElasticSearch domain defined in environment
    variables.

    .. info::
        The request will have been authorized by a separate Lambda function
        defined as the Authorizer function on the API Gateway.

    :param event: A dictionary of attributes passed to the function by API
        Gateway. See the documentation for further details:

        https://docs.aws.amazon.com/lambda/latest/dg/with-on-demand-https.html
    :param context: An ``EventContext`` object which gives access to various
        attributes of the runtime environment. See the documentation for further
        details:

        https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
    :return: A dictionary containing necessary response attributes used to
        indicate success or failure of the request to API Gateway. The ``body``
        attribute will be passed back to the requesting client by API Gateway,
        after transformation.
    """
    # validate the incoming request before proxying to ES cluster
    if not valid_request():
        # return an error response through API Gateway
        return error_response()
    # validate and clean the incoming request's body data (if any)
    body = clean_body(event)
    # generate headers to send to ES, based on the incoming request headers
    headers = proxy_headers(event)
    # generate a url and query parameters (if any) for the request to ES
    url, params = generate_url(event)
    # get the correct request function to use for the request to ES
    # will raise an unhandled KeyError if an unsupported method is found
    # within the event
    request_func = choose_request_func(event)
    try:
        # send the formed request to ElasticSearch
        data, content_type = send_to_es(url, body, headers, request_func)
    except requests.RequestException as e:
        # the request to ES returned an error response so proxy that error
        # back to API Gateway
        return exception_response(e, body, params, headers)
    # check if the returned content-type is cache-able
    if any([t in content_type for t in CACHEABLE_TYPES]):
        # if cache-able, upload the object to S3 and redirect the incoming
        # request to the location of the uploaded file. Sets the appropriate
        # value for the cache-control header
        return redirect_to_object(data, event, content_type)
    else:
        # if not cache-able, return the data from ES back through API Gateway
        # to the user. Sets the appropriate value for the cache-control header
        return proxied_request(data, content_type)
