"""
settings
-------
"""
import os
import logging
import requests


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
