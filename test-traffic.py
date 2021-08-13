import sys
from scapy.all import Ether, IP, UDP, VXLAN, sendp
import time

packet = Ether()/IP(src="127.0.0.1", dst="10.4.0.6")/UDP(dport=4789)/VXLAN(vni=2)


while True:
    time.sleep(1)
    packet.show()
    sendp(packet, iface="lo")
