import os
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
# Get the long description from the README file
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name='skafos',
    version='0.0.1',
    description='Reads custom objects from Kubernetes event stream',
    keywords='kubernetes event stream custom object',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ing-bank/skafos',
    author='ING',
    author_email='itt@ing.com',
    setup_requires=[],
    packages=['skafos'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    tests_require=['pytest', 'timeout-decorator'],
    test_suite='test'
)
