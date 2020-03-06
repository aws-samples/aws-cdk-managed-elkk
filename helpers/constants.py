constants = {
    # project level constants
    "ELK_PROJECT_TAG": "elk-stack",
    # do not include the .pem in the keypair name
    "ELK_KEY_PAIR": "ElkKeyPair",
    # kafka settings
    "ELK_KAFKA_DOWNLOAD_VERSION": "kafka_2.12-2.4.0",
    "ELK_KAFKA_BROKER_NODES": 3,
    "ELK_KAFKA_VERSION": "2.3.1",
    "ELK_KAFKA_INSTANCE_TYPE": "kafka.m5.large",
    "ELK_TOPIC": "elkstacktopic",
    "ELK_KAFKA_CLIENT_INSTANCE": "t2.xlarge",
    # filebeat
    "ELK_FILEBEAT_INSTANCE": "t2.xlarge",
    # elastic
    "ELK_ELASTIC_CLIENT_INSTANCE": "t2.xlarge",
    "ELK_ELASTIC_MASTER_COUNT": 3,
    "ELK_ELASTIC_MASTER_INSTANCE": "r5.large.elasticsearch",
    "ELK_ELASTIC_INSTANCE_COUNT": 3,
    "ELK_ELASTIC_INSTANCE": "r5.large.elasticsearch",
    "ELK_ELASTIC_VERSION": "7.1",
    # logstash
    "ELK_LOGSTASH_INSTANCE": "t2.xlarge",
}

