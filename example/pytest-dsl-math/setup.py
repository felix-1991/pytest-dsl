from setuptools import setup, find_packages

setup(
    name="pytest-dsl-math",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=6.0.0",
    ],
    entry_points={
        "pytest_dsl.keywords": [
            "math_keywords = pytest_dsl_math.keywords",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A pytest-dsl plugin for mathematical operations",
    long_description="This plugin provides mathematical operation keywords for pytest-dsl",
    keywords="pytest-dsl, testing, mathematics",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 