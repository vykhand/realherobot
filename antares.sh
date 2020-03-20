#!/usr/bin/env bash

pip install --upgrade pip
pip install https://files.pythonhosted.org/packages/c6/54/d042e60e3be64dcf1637596ef862b67ffa312dc2173d5cb209d18537ac2b/opencensus_ext_azure-1.0.2-py2.py3-none-any.whl
pip install -r requirements.txt

python app.py