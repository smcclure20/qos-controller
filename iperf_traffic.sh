#!/bin/bash
# TODO: Make this actually runable
# Server command: iperf3 -s

# First few high priority flows
iperf3 -c 10.4.0.5  -t 100 -S 0x04 -b 10K --logfile prio4.out &
iperf3 -c 10.4.0.5  -t 100 -S 0x05 -b 110K --logfile prio5.out &

# Reach high priority limit (128K) [one of these should be admitted]
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prio6.1.out &
iperf3 -c 10.4.0.5  -t 100 -S 0x06 -b 3K --logfile prio6.2.out &

# Should be low priority
iperf3 -c 10.4.0.5  -t 100 -S 0x07 -b 200K --logfile prio7.out
