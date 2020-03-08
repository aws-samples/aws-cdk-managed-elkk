constants = {
    # project level constants
    "PROJECT_TAG": "elkk-stack",
    # do not include the .pem in the keypair name
    "KEY_PAIR": "ElkKeyPair",
    # kafka settings
    "KAFKA_DOWNLOAD_VERSION": "kafka_2.12-2.4.0",
    "KAFKA_BROKER_NODES": 3,
    "KAFKA_VERSION": "2.3.1",
    "KAFKA_INSTANCE_TYPE": "kafka.m5.large",
    "ELKK_TOPIC": "elkkstacktopic",
    "KAFKA_CLIENT_INSTANCE": "t2.xlarge",
    # filebeat
    "FILEBEAT_INSTANCE": "t2.xlarge",
    # elastic
    "ELASTIC_CLIENT_INSTANCE": "t2.xlarge",
    "ELASTIC_MASTER_COUNT": 3,
    "ELASTIC_MASTER_INSTANCE": "r5.large.elasticsearch",
    "ELASTIC_INSTANCE_COUNT": 3,
    "ELASTIC_INSTANCE": "r5.large.elasticsearch",
    "ELASTIC_VERSION": "7.1",
    # logstash
    "LOGSTASH_INSTANCE": "t2.xlarge",
}

