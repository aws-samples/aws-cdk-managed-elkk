import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="elkk_stack",
    version="0.0.1",
    description="Build an ELKK stack with the AWS CDK v2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="",
    package_dir={},
    packages=setuptools.find_packages(),
    install_requires=[
        # cdk v2
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
    extras_require={
        "dev": [
            "awscli",
            "boto3",
            "pip==21.3.1",
            # for vscode
            "black",
        ]
    },
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
