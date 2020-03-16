"""
lambda_function
-------
"""
import requests

from .settings import CACHEABLE_TYPES

from .utils import (
    valid_request,
    error_response,
    exception_response,
    proxied_request,
    proxy_headers,
    choose_request_func,
    generate_url,
    clean_body,
    send_to_es,
    redirect_to_object
)


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
