FROM centos:8

# use bash
SHELL ["/bin/bash", "-c"] 

# copy in the lambda function code
ADD lambda_handler.py /home/lambda_handler.py
ADD requirements.txt /tmp/requirements.txt

# get python3
RUN yum install python3 -y
# get pip
RUN yum install python3-pip -y
# pip in requirements
RUN python3 -m pip install -r /tmp/requirements.txt -t /home
RUN ls -l home
# fix permissions
RUN chmod -R 755 /home

RUN yum install zip -y
WORKDIR /home
RUN zip -r -J ../kibana_lambda.zip *

# Entrypoint
ENTRYPOINT [ "/bin/bash" ]