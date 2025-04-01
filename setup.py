from setuptools import setup, find_packages

# 让setuptools使用pyproject.toml中的配置
setup(
    packages=find_packages(),
    include_package_data=True,
) 