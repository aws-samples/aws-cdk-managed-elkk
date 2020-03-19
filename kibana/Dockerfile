# Use the same base image as the AWS SAM CLI to build the deployment package
FROM lambci/lambda-base-2:build
# Use the same python and pip install strategy as the lambci python3.8 Dockerfile
ENV PATH=/var/lang/bin:$PATH \
    LD_LIBRARY_PATH=/var/lang/lib:$LD_LIBRARY_PATH \
    AWS_EXECUTION_ENV=AWS_Lambda_python3.8 \
    PYTHONPATH=/var/runtime \
    PKG_CONFIG_PATH=/var/lang/lib/pkgconfig:/usr/lib64/pkgconfig:/usr/share/pkgconfig
RUN rm -rf /var/runtime /var/lang /var/rapid && \
  curl https://lambci.s3.amazonaws.com/fs/python3.8.tgz | tar -zx -C /
RUN pip install -U pip setuptools --no-cache-dir
# Copy our code over to the container
RUN mkdir /tmp/build
ADD lambda_function.py /tmp/build/lambda_function.py
ADD requirements.txt /tmp/requirements.txt
# Build the deployment package
RUN pip install -r /tmp/requirements.txt -t /tmp/build
RUN ls -l /tmp/build
# Create a zip file of the deployment package
WORKDIR /tmp/build
RUN zip -r -J ../kibana_lambda.zip *
