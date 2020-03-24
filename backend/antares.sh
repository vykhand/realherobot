#!/usr/bin/env bash

apt update
apt install build-essential -y

pip install --upgrade pip
pip install -r requirements.txt

python app.py