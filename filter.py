from bcc import BPF
import ctypes as ct
from pyroute2 import IPRoute
import socket
import sys
import time
from ctypes import c_int, c_ulong, Array, c_float
from host import USAGE_FILE, PRIORITIES_FILE, SPLIT_CLASS_BW_CAP_FILE

# function to read from the count table
# function to update tc

OUTPUT_INTERVAL = 10
INTERFACE = "lo"
TOTAL_RATE = 256
STARTING_HI_PRI = 128
RATE_FORMAT = "{}kbit"
SPLIT_CLASS_PRIO = 3


def reset_tc(hi_pr_bw):
    try:
        # Set up egress classifier
        ipr.tc("del", "htb", iface, 0x10000)

    except Exception as e:
        print("Failed to remove htb from interface.")
        print(e)

    try:
        # Set up egress classifier
        ipr.tc("add", "htb", iface, 0x10000)

    except Exception as e:
        print("Failed at adding HTB to interface.")
        print(e)

    try:
        # Root class
        ipr.tc("add-class", "htb", iface, 0x10001,
            parent=0x10000,
            rate=RATE_FORMAT.format(TOTAL_RATE),
            burst=1024 * 6)

        # Sub classes
        ipr.tc("add-class", "htb", iface, 0x10010,
            parent=0x10001,
            rate=RATE_FORMAT.format(hi_pr_bw),
            burst=1024 * 6,
            prio=1)
        ipr.tc("add-class", "htb", iface, 0x10020,
            parent=0x10001,
            rate=RATE_FORMAT.format(TOTAL_RATE-hi_pr_bw),
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

    except Exception as e:
        print("Failed at creating the subclasses.")
        print(e)

    try:
        # Set up ingress classifier
        # ipr.tc("add", "egress", iface, "ffff:")
        ipr.tc("add-filter", "bpf", iface, ":1", fd=bpf_rl_fn.fd,
                     name=bpf_rl_fn.name, parent=0x10000, action="ok")
    except Exception as e:
        print("Failed at creating the tracing classifer.")
        print(e)


ipr = IPRoute()

bpf_filter = BPF(src_file="filter.c", debug=0)
bpf_rl = BPF(src_file="rate_limit.c", debug=0)

bpf_filter_fn = bpf_filter.load_func("filter", BPF.SCHED_CLS)
bpf_rl_fn = bpf_rl.load_func("filter", BPF.SCHED_CLS)
iface = ipr.link_lookup(ifname=INTERFACE)

high_prio_bw = 0
reset_tc(STARTING_HI_PRI)

while True:
    time.sleep(OUTPUT_INTERVAL)
    print("Updating local data")

    hits = bpf_rl.get_table('hits')
    hit_counts = [(x[0].value, x[1].value) for x in hits.items()]
    print("Hits (vni, # of packets classified in rate limiter on TOS): ", hit_counts)

    bandwidths = []
    counts = []
    packet_cnt = bpf_filter.get_table('counts')  # Take the counts and report
    with open(USAGE_FILE, "w") as file:
        for count in packet_cnt.items():
            bandwidths.append(count[1].value/OUTPUT_INTERVAL)
            counts.append((count[0].value, count[1].value/OUTPUT_INTERVAL))
        file.write(str(counts))
        # file.write(str(packet_cnt.values()))
    packet_cnt.clear()

    # TODO: Should probably reorder these
    old_high_prio_bw = high_prio_bw
    priority_table = bpf_rl.get_table(
        'priorities')  #
    bw_table = bpf_rl.get_table('split_bw')
    split_flows_table = bpf_rl.get_table('split_flows')
    elig_bytes_table = bpf_rl.get_table('eligible_flows_bytes')
    elig_timestamp_table = bpf_rl.get_table('eligible_flows_timestamp')

    with open(SPLIT_CLASS_BW_CAP_FILE, "r") as file:
        bandwidth = float(file.read())
        bw_table[SPLIT_CLASS_PRIO] = c_float(bandwidth)

    # Set the priorities based on instructions from the controller
    with open(PRIORITIES_FILE, "r") as file: # TODO: can do this all with tc filter updates if desperate
        priorities = eval(file.read())
        keys = [c_int(int(x)) for x in priorities.keys()]
        values = [c_ulong(int(x)) for x in priorities.values()]

        # TODO: Make sure ordering of both lists is the same
        high_prio_bw = 0
        for key in priorities.keys():
            priority_table[key] = values[key]
            if values[key] == 1:
                high_prio_bw += bandwidths[key]
            # priority_table.items_update_batch(ckeys, cvalues) TODO: this requires kernel version 5.6

    elig_bytes_table.clear()
    split_flows_table.clear()
    elig_timestamp_table.clear()

   # if the high priority bandwidth changed, rerun the TC commands
    if high_prio_bw != old_high_prio_bw: # TODO: I don't think this is actually necessary - just overprovision?
        reset_tc(high_prio_bw) #TODO: this might be really really slow