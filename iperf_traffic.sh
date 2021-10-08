#!/bin/bash
# TODO: Make this actually runable
# Server command: iperf3 -s -p <each port>

# First few high priority flows
iperf3 -c 10.4.0.5  -t 100 -S 0x04 -b 10K --logfile prio4.out -p 5021 &
iperf3 -c 10.4.0.5  -t 100 -S 0x05 -b 110K --logfile prio5.out -p 5022 &

# Reach high priority limit (128K) [one of these should be admitted]
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prio6.1.out -p 5023 &
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prio6.2.out -p 5024 &

# Should be low priority
iperf3 -c 10.4.0.5  -t 100 -S 0x07 -b 200K --logfile prio7.out -p 5025
