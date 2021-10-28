#!/bin/bash

ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5021 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5022 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5023 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5024 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5025 -D

rm prios/prio1.out
rm prios/prio2.out
rm prios/prio3.1.out
rm prios/prio3.2.out
rm prios/prio4.out

echo "Starting iperf traffic..."
# First few high priority flows
iperf3 -c 10.4.0.5  -t 100 -S 0x04 -b 10K --logfile prios/prio1.out -p 5021 &
iperf3 -c 10.4.0.5  -t 100 -S 0x05 -b 110K --logfile prios/prio2.out -p 5022 &

# Reach high priority limit (128K) [one of these should be admitted]
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prios/prio3.1.out -p 5023
sleep 2
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prios/prio3.2.out -p 5024 &

# Should be low priority
iperf3 -c 10.4.0.5  -t 100 -S 0x07 -b 200K --logfile prios/prio4.out -p 5025
echo "Test Complete"

echo "Killing remote server processes"
ssh -i ../receiver_key.pem azureuser@20.112.15.215 pkill iperf
