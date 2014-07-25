from setuptools import setup, find_packages

setup(
    name = 'roar2doar',
    version = '0.0.1',
    packages = find_packages(),
    install_requires = [
        "requests==1.1.0",
        "Flask==0.9",
        "lxml",
        "pycountry"
    ],
    url = 'http://cottagelabs.com/',
    author = 'Cottage Labs',
    author_email = 'us@cottagelabs.com',
    description = 'roar2doar - Connector for pulling data from ROAR into OpenDOAR',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: Copyheart',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)