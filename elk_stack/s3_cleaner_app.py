#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto3
import logging as log
import cfnresponse


def lambda_handler(event, context):

    # log the event
    log.info("Input event: %s", event)
    # do the processing
    try:
        bucket = event["ResourceProperties"]["BucketName"]

        if event["RequestType"] == "Delete":
            s3 = boto3.resource("s3")
            bucket = s3.Bucket(bucket)
            for obj in bucket.objects.filter():
                s3.Object(bucket.name, obj.key).delete()
        cfnresponse.send(event, context, responseData="SUCCESS", responseStatus="SUCCESS")
    except Exception as e:
        print(e)
        cfnresponse.send(event, context, responseData="FAILED", responseStatus="FAILED")
