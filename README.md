#To Run:

`sudo python3 ./filter.py` for the BPF program

`python3 ./host.py` to collect and report usage

`python3 ./tenant.py` to aggregate and report limits

`sudo python ./test-traffic.py` for some small amount of traffic

`iperf3 -c <server> -t <time> -S <tos> -b <bw>` for a large volume of traffic. Note that iperf treats
-S as the dscp field, so the last two bits (ECN) are ignored.

https://linuxconfig.org/configuring-virtual-network-interfaces-in-linux