import sys
from scapy.all import Ether, IP, UDP, VXLAN, sendp
import time

packet = Ether()/IP(dst="127.0.0.1")/UDP(dport=4789)/VXLAN(vni=2)


while True:
    time.sleep(1)
    sendp(packet, iface="lo")
