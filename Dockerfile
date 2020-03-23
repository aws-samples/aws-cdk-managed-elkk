FROM docker.elastic.co/logstash/logstash:7.6.0
# remove conf as want to place custom pipeline
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
# set the pipeline
ADD logstash.conf.asset /usr/share/logstash/pipeline/logstash.conf 
# set the config
ADD logstash.yml /usr/share/logstash/config/logstash.yml
# install git (needs root user)
USER root
RUN yum update -y 
RUN yum install git -y
RUN mkdir /var/lib/logstash
RUN chown -R logstash:root /var/lib/logstash
# back to logastash user
USER logstash
# import the amazon elasticsearch plugin
RUN git clone https://github.com/awslabs/logstash-output-amazon_es.git /usr/share/logstash/plugins/logstash-output-amazon_es
# update gemfile
RUN sed -i '5igem "logstash-output-amazon_es", :path => "/usr/share/logstash/plugins/logstash-output-amazon_es"' /usr/share/logstash/Gemfile
# check the pipeline file
RUN /usr/share/logstash/bin/logstash --config.test_and_exit -f /usr/share/logstash/pipeline/logstash.conf
# Entrypoint
# "Entrypoint": [ "/usr/local/bin/docker-entrypoint" ]