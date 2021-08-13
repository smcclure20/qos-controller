from bcc import BPF
import ctypes as ct
from pyroute2 import IPRoute
import socket
import sys
import time

# function to read from the count table
# function to update tc

OUTPUT_INTERVAL = 10
USAGE_FILE = "./usage"
PRIORITIES_FILE = "./prios"
INTERFACE = "lo"

ipr = IPRoute()

bpf_filter = BPF(src_file="filter.c", debug=0)
bpf_rl = BPF(src_file="rate_limit.c", debug=0)

bpf_filter_fn = bpf_filter.load_func("filter", BPF.SCHED_CLS)
bpf_rl_fn = bpf_rl.load_func("filter", BPF.SCHED_CLS)
iface = ipr.link_lookup(ifname=INTERFACE)

try:
       # Set up egress classifier
       ipr.tc("add", "htb", iface, 0x10000)

       # Root class
       ipr.tc("add-class", "htb", iface, 0x10001,
              parent=0x10000,
              rate="256kbit",  # TODO: Make these variable - set by user reservation
              burst=1024 * 6)

       # Sub classes
       ipr.tc("add-class", "htb", iface, 0x10010,
              parent=0x10001,
              rate="192kbit",
              burst=1024 * 6,
              prio=1)
       ipr.tc("add-class", "htb", iface, 0x10020,
              parent=0x10001,
              rate="128kbit",
              burst=1024 * 6,
              prio=2)

       # Leaf queues
       ipr.tc("add", "pfifo_fast", iface, 0x100000,
              parent=0x10010)
       ipr.tc("add", "pfifo_fast", iface, 0x200000,
              parent=0x10020)

       # Add filter
       ipr.tc("add-filter", "bpf", iface, ":1", fd=bpf_filter_fn.fd,
              name=bpf_filter_fn.name, parent=0x10000, action="ok")

       # Set up ingress classifier
       ipr.tc("add", "ingress", iface, "ffff:")
       ipr.tc("add-filter", "bpf", iface, ":1", fd=bpf_rl_fn.fd,
              name=bpf_rl_fn.name, parent="ffff:", action="ok", classid=1)
except Exception as e:
     print(e)

while True:
       time.sleep(OUTPUT_INTERVAL)

       packet_cnt = bpf_filter.get_table('counts')  # Take the counts and report
       with open(USAGE_FILE, "w") as file:
              for item in packet_cnt.items():
                     print(type(item[0].value))
                     print(type(item[1].value))
                     break
              counts = [(x[0].value, x[1].value) for x in packet_cnt.items()]
              file.write(str(counts))
              # file.write(str(packet_cnt.values()))
       packet_cnt.clear()

       # TODO: Should probably reorder these
       priority_table = bpf_rl.get_table(
              'priorities')  # # Set the priorities based on instructions from the controller -> how to do the x% thing here?
       test = priority_table.items()
       for item in test:
              print(type(item[0].value))
              print(type(item[1].value))
              break
       with open(PRIORITIES_FILE, "r") as file:
              priorities = eval(file.read())
              print(priorities)
              print(type(list(priorities.keys())[0]))
              print(type(list(priorities.values())[0]))
              # TODO: Make sure ordering of both lists is the same
              priority_table.items_update_batch(priorities.keys(), priorities.values())
