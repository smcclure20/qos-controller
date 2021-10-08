#!/bin/bash

ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5021 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5022 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5023 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5024 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5025 -D

rm prio1.out
rm prio2.out
rm prio3.1.out
rm prio3.2.out
rm prio4.out

# First few high priority flows
iperf3 -c 10.4.0.5  -t 100 -S 0x04 -b 10K --logfile prio1.out -p 5021 &
iperf3 -c 10.4.0.5  -t 100 -S 0x05 -b 110K --logfile prio2.out -p 5022 &

# Reach high priority limit (128K) [one of these should be admitted]
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prio3.1.out -p 5023
sleep(2)
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prio3.2.out -p 5024 &

# Should be low priority
iperf3 -c 10.4.0.5  -t 100 -S 0x07 -b 200K --logfile prio4.out -p 5025

ssh -i ../receiver_key.pem azureuser@20.112.15.215 pkill iperf
