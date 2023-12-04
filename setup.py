
from setuptools import setup, find_packages

setup(
    name='apyengine',
    version='1.0.0',
    description='A lightweight, embeddable Python interpreter',
    long_description='file: README.md',
    author='Mark Anacker',
    author_email='closecrowd@pm.me',
    url='https://github.com/closecrowd/apyengine/',
    license='MIT',
    packages=find_packages(include=['apyengine', 'apyengine.*']),
    install_requires=[
        'importlib'
    ]
)
