#!/usr/bin/env bash
# Notes and commands to upload to pypi
#
# https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56
# https://pypi.org/project/twine/
#
# https://python-packaging.readthedocs.io/en/latest/non-code-files.html
# edit setup.py
# to update the version

. venv37/bin/activate

# setup first

pip install setuptools
pip install wheel
pip install twine
pip install flask
pip install flask-sqlalchemy
pip install flask-wtf
pip install pytest-flask

# on each release

. venv3/bin/activate
python setup.py sdist bdist_wheel
twine check dist/flask_serialize-1.5.1*
twine upload dist/flask_serialize-1.5.1* -u martlark
