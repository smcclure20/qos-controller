#!/bin/bash

KEYPATH="../receiver_key.pem"
REMOTE_USER="azureuser"
REMOTE_IP="10.10.1.220"
TRIALS=10
#FILE_NAME="bpf_tput_"
FILE_NAME="default_tput_"

#ssh -i $KEYPATH $REMOTE_USER@$REMOTE_IP iperf3 -s -p 5021 -D

for i in {1..$TRIALS}
do
   iperf3 -c $REMOTE_IP -t 60 -S 0x04 -p 5021 --logfile perf_tests/$FILE_NAME$i.out
done


