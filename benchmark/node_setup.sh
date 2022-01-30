#!/bin/bash

sudo apt-get update

sudo apt-get -y install pip

pip install flask waitress pyroute2 aiohttp

cd /home/ubuntu

git clone https://github.com/smcclure20/qos-controller.git

cd qos-controller

git checkout master