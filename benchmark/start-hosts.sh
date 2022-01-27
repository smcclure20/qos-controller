#!/bin/bash

ssh -i <keyfile> ubuntu@<remote_ip> (python3 ./host.py <remote_ip>:5000 10.10.1.12 )

python3 ./host.py 10.10.1.220:5000 10.10.1.12

ssh -i <keyfile> ubuntu@<remote_ip> pkill python3
