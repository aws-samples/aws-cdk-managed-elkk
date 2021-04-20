import os
import boto3
import json


def lambda_handler(event, context):

    # show the event
    print("event", event)

    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception("Invalid request type: %s" % request_type)


def on_create(event):

    # get the cloudfront domain name
    distributions_list = cf_client.list_distributions()["DistributionList"]["Items"]
    cloudfront_domain = [
        dist["DomainName"]
        for dist in distributions_list
        if "elkk-kibana" in dist["Origins"]["Items"][0]["DomainName"]
    ][0]

    # get the s3 bucket name
    s3_bucket_list = s3_client.list_buckets()
    for bkt in s3_bucket_list["Buckets"]:
        try:
            bkt_tags = s3_client.get_bucket_tagging(Bucket=bkt["Name"])["TagSet"]
            for keypairs in bkt_tags:
                if (
                    keypairs["Key"] == "aws:cloudformation:stack-name"
                    and keypairs["Value"] == "elkk-kibana"
                ):
                    kibana_bucket_name = bkt["Name"]
        except ClientError:
            pass

    # get the elastic endpoint details
    es_domains = es_client.list_domain_names()
    try:
        es_domain = [
            dom["DomainName"]
            for dom in es_domains["DomainNames"]
            if "elkk-" in dom["DomainName"]
        ][0]
    except IndexError:
        return ""

    es_endpoint = es_client.describe_elasticsearch_domain(DomainName=es_domain)
    elastic_endpoint = es_endpoint["DomainStatus"]["Endpoints"]["vpc"]

    # update the functions env
    update_env = la_client.update_function_configuration(
        FunctionName=api_function,
        Environment={
            "Variables": {
                "AES_DOMAIN_ENDPOINT": f"https://{elastic_endpoint}",
                "KIBANA_BUCKET": kibana_bucket_name,
                "S3_MAX_AGE": "2629746",
                "LOG_LEVEL": "warning",
                "CLOUDFRONT_CACHE_URL": f"https://{cloudfront_domain}/bucket_cached",
            }
        },
    )

    return {"PhysicalResourceId": "kibanaLambdaUpdate"}


def on_update(event):
    return on_create(event)


def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    print(f"Delete resource {physical_id}")
    pass