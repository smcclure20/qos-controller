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

bpf = BPF(src_file="filter.c", debug=0)
bpf2 = BPF(src_file="rate_limit.c", debug=0)

bpf_fn = bpf.load_func("filter", BPF.BPF_PROG_TYPE_SCHED_CLS)
bpf_fn2 = bpf2.load_func("filter", BPF.BPF_PROG_TYPE_SCHED_CLS)
iface = ipr.link_lookup(ifname=INTERFACE)

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
ipr.tc("add-filter", "bpf", iface, ":1", fd=bpf_fn.fd,
       name=bpf_fn.name, parent=0x10000, action="ok")

# Set up ingress classifier
ipr.tc("add", "ingress", iface, "ffff:")
ipr.tc("add-filter", "bpf", iface, ":1", fd=bpf_fn2.fd,
       name=bpf_fn2.name, parent="ffff:", action="ok", classid=1)

while True:
       time.sleep(OUTPUT_INTERVAL)

       packet_cnt = bpf2.get_table('counts')  # Take the counts and report
       with open(USAGE_FILE, "w") as file:
              file.write(packet_cnt.items())
              file.write(packet_cnt.values())
       packet_cnt.clear()

       # TODO: Should probably reorder these
       priority_table = bpf.get_table(
              'priorities')  # Set the priorities based on instructions from the controller -> how to do the x% thing here?
       with open(PRIORITIES_FILE, "r") as file:
              priorities = eval(file.read())
              # TODO: Make sure ordering of both lists is the same
              priority_table.items_update_batch(priorities.keys(), priorities.values())
