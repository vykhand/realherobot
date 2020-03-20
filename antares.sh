#!/usr/bin/env bash

sudo apt update
sudo apt install build-essential -y
pip install --upgrade pip
pip install -r requirements.txt
python app.py