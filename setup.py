import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="elkk_stack",
    version="0.0.1",

    description="Build an ELKK stack with the AWS CDK",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "elkk_stack"},
    packages=setuptools.find_packages(where="elkk_stack"),

    install_requires=[
        "aws-cdk.core",
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
