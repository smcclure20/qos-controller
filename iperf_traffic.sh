#!/bin/bash

ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5021 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5022 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5023 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5024 -D
ssh -i ../receiver_key.pem azureuser@20.112.15.215 iperf3 -s -p 5025 -D

rm results/prio1.out
rm results/prio2.out
rm results/prio3.1.out
rm results/prio3.2.out
rm results/prio4.out

touch results/prio1.out
touch results/prio2.out
touch results/prio3.1.out
touch results/prio3.2.out
touch results/prio4.out

echo "Starting iperf traffic..."
# First few high priority flows
echo "10kbps to 5021 and 110kbps to 5022"
iperf3 -c 10.4.0.5  -t 100 -S 0x04 -b 10K --logfile results/prio1.out -p 5021 &
iperf3 -c 10.4.0.5  -t 100 -S 0x08 -b 110K --logfile results/prio2.out -p 5022 &

# Reach high priority limit (128K) [one of these should be admitted]
echo "3kbps to 5023"
iperf3 -c 10.4.0.5  -t 100 -S 0x0C -b 3K --logfile results/prio3.1.out -p 5023
echo "Sleep for 2"
sleep 2
echo "30kbps to 5024"
iperf3 -c 10.4.0.5  -t 100 -S 0x0C -b 30K --logfile results/prio3.2.out -p 5024 &

# Should be low priority
echo "50kbps to 5025"
iperf3 -c 10.4.0.5  -t 100 -S 0x10 -b 50K --logfile results/prio4.out -p 5025
echo "Test Complete"

echo "Killing remote server processes"
ssh -i ../receiver_key.pem azureuser@20.112.15.215 pkill iperf
