# -*- coding: utf-8 -*-

from setuptools import setup

project = "camus"

setup(
    name=project,
    version='0.1',
    url='https://github.com/kindly/camus',
    description='camus, The exestential CMS',
    author='David Raznick',
    author_email='kindly@gmail.com',
    packages=["camus"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Flask',
        'Flask-Script',
        'Flask-Babel',
        'Flask-Testing',
        'Flask-Mail',
        'Flask-Cache',
        'Flask-Login',
        'nose',
    ],
    test_suite='tests',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries'
    ]
)
