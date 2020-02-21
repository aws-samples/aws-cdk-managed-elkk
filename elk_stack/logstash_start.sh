#!/bin/bash

exec /opt/logstash/bin/logstash agent -f /etc/logstash/conf.d/logstash.conf >> /opt/logs/logstash.log 2>&1