import sys
from scapy.all import Ether, IP, UDP, VXLAN, sendp
import time

packet = Ether()/IP(src="10.4.0.6", dst="10.4.0.5", tos=2)/UDP()


while True:
    time.sleep(1)
    if len(sys.argv) > 1 and sys.argv[1] == "-v":
        packet.show()
    sendp(packet, iface="eth0")
