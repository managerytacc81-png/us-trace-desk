from setuptools import setup, find_packages

setup(
    name="us-trace-desk",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "reportlab>=3.6.0",
        "pypdf>=3.0.0",
        "requests>=2.28.0",
        "dnspython>=2.3.0"
    ],
    entry_points={
        "console_scripts": [
            "trace-desk = trace_desk.cli:main",
        ],
    },
)
