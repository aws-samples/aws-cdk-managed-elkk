import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="elkk_stack",
    version="0.0.1",
    description="Build an ELKK stack with the AWS CDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="",
    package_dir={},
    packages=setuptools.find_packages(),
    install_requires=[
        "awscli",
        "aws_cdk.core",
        "aws_cdk.aws_ec2",
        "aws_cdk.aws_iam",
        "aws_cdk.aws_msk",
        "aws_cdk.aws_elasticsearch",
        "aws_cdk.aws_s3_assets",
        "aws_cdk.aws_lambda",
        "aws_cdk.aws_lambda_python",
        "aws_cdk.aws_logs",
        "aws_cdk.aws_s3",
        "aws_cdk.aws_cloudformation",
        "aws_cdk.aws_ecs",
        "aws_cdk.aws_ecr_assets",
        "aws_cdk.aws_glue",
        "boto3",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
