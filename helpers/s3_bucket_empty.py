def main(event, context):

    # get modules
    import logging as log
    import cfnresponse
    import boto3

    log.getLogger().setLevel(log.INFO)

    # This needs to change if there are to be multiple resources
    # in the same stack
    physical_id = event["ResourceProperties"]["PhysicalId"]

    try:
        log.info(f"Input event: {event}")

        # Check if this is a Create and we're failing Creates
        if event["RequestType"] == "Create" and event["ResourceProperties"].get(
            "FailCreate", False
        ):
            raise RuntimeError("Create failure requested")

        # Delete objects from the bucket if event is delete
        if event["RequestType"] == "Delete":
            bucket = boto3.resource("s3").Bucket(
                event["ResourceProperties"]["BucketName"]
            )
            bucket.objects.all().delete()

        # do some reporting
        attributes = {"Response": f'{event["ResourceProperties"]["BucketName"]}'}

        cfnresponse.send(event, context, cfnresponse.SUCCESS, attributes, physical_id)
    except Exception as e:
        log.exception(e)
        # cfnresponse's error message is always "see CloudWatch"
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_id)
