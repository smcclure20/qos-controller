import sys
from scapy.all import Ether, IP, UDP, VXLAN, sendp
import time

packet = Ether()/IP(dst="10.4.0.6")/UDP(dport=4789)/VXLAN(vni=2)


while True:
    time.sleep(1)
    sendp(packet, iface="lo")
