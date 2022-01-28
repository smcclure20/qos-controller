from flask import Flask, request, Response, make_response
from waitress import serve
import time
import multiprocessing
import requests
import sys
import asyncio
app = Flask(__name__)

PRIO_BANDWIDTH = 5000000000
PRIORITY_FORMAT = "{}"
AGGREGATION_INTERVAL = 10
PRIORITIES_URL = 'http://{}/priorities'
DEBUG=False

def printd(to_print, to_print2=None):
    if DEBUG:
        print(to_print, to_print2) if to_print2 else print(to_print)

@app.post('/usage/')
def record_usage():
    host_name = request.form.get("name")
    printd("Received usage update from {}".format(host_name))
    host_usage = request.form.to_dict()
    host_usage.pop("name")
    usage_queue.put(host_usage)
    if usage_queue.qsize() % 50 == 0:
        print("[RECEIVER] Approximate queue length: ", usage_queue.qsize(), flush=True)
    return make_response(request.form.to_dict())


class AggregationProcess(multiprocessing.Process):
    def __init__(self, usage_queue):
        multiprocessing.Process.__init__(self)
        self.usage_queue = usage_queue
        self.total_usage = {}
        self.final_priorities = {}
        self.current_hosts = []
        self.split_class = None
        self.split_fraction = None

    def run(self):
        asyncio.run(self.run_async())

    async def run_async(self):
        printd("Starting aggregation process")
        while True:
            printd("Calculating priorities...")
            t1 = time.time()
            task = asyncio.create_task(self.process_reports())
            done, pending = await asyncio.wait([asyncio.sleep(AGGREGATION_INTERVAL), task], timeout=AGGREGATION_INTERVAL+1)
            print("[{}] Completed Interval".format(time.strftime("%m/%d/%y %H:%M:%S")), flush=True)
            t2 = time.time()
            if (t2 - t1 > AGGREGATION_INTERVAL + 2):
                print("[WARNING] Aggregation process lagging behind interval.", flush=True)
                print(len(pending), pending, flush=True)
            #print("Done: {} ({}), Pending: {} ({})".format(len(done),done,  len(pending), pending))
            if task in pending:
                print("[WARNING] Aggregation process lagging behind interval.", flush=True)
            printd("Updated priority traffic ratios:")
            printd("split class {}; bw fraction {}".format(self.split_class, self.split_fraction))

    async def process_reports(self):
        self.clear_totals()
        task = asyncio.create_task(self.aggregate_tenant())
        t1 = time.time()
        await asyncio.wait([task], timeout=AGGREGATION_INTERVAL)
        t2 = time.time()
        print("Aggregation time: ", t2-t1, flush=True)
        if (t2 - t1 > AGGREGATION_INTERVAL + 2):
            print("[WARNING] [2] Aggregation process lagging behind interval.", flush=True)
        self.calculate_priority()
        t1 = time.time()
        self.report_priorities()
        t2 = time.time()
        print("Reporting time:", t2-t1, flush=True)

    async def aggregate_tenant(self):
        printd("Checking queue")
        print("Approximate queue length: ", self.usage_queue.qsize(), flush=True)
        while not self.usage_queue.empty():
            update = self.usage_queue.get()
            self.current_hosts.append(update.pop("address"))
            for key in update.keys():
                priority = int(key)
                if priority in self.total_usage.keys():
                    self.total_usage[priority] += float(update[key])
                else:
                    self.total_usage[priority] = float(update[key])

    def clear_totals(self):
        self.total_usage.clear()
        self.current_hosts.clear()
        self.split_class = None
        self.split_fraction = None

    def calculate_priority(self):
        priority = 0
        remaining = PRIO_BANDWIDTH
        while priority in self.total_usage.keys() and remaining > 0:
            # self.final_priorities[PRIORITY_FORMAT.format(priority)] = min(int((remaining / float(self.total_usage[priority])) * 100), 100) if float(self.total_usage[priority]) > 0 else 100
            # self.final_priorities[PRIORITY_FORMAT.format(priority)] = int(float(self.total_usage[priority]) <= remaining)
            printd("Priority {}: usage {}. Remaining {}".format(priority, self.total_usage[priority], remaining))
            if float(self.total_usage[priority]) > remaining:
                self.split_class = priority
                self.split_fraction = remaining / float(self.total_usage[priority])
                printd("Set split class to {}".format(priority))
            remaining -= float(self.total_usage[priority])
            priority += 1

        # If not overusing the bandwidth, split traffic class is the lowest priority one
        if self.split_class is None:
            # self.split_fraction = 0
            priority = len(self.total_usage.keys()) - 1
            while priority > 0 and float(self.total_usage[priority]) == 0:
                priority -= 1
            self.split_class = priority if priority > 0 else 0
            self.split_fraction = remaining / float(self.total_usage[self.split_class]) if self.split_class in self.total_usage.keys() and float(self.total_usage[self.split_class]) > 0 else 0


    def report_priorities(self):  # Report to hosts new ratios
        print("[{}] Sending priorities to {} reporting hosts".format(time.strftime("%m/%d/%y %H:%M:%S"), len(self.current_hosts)), flush=True)
        for address in self.current_hosts:
            try:
                r = requests.post(PRIORITIES_URL.format(address), data={"split_class": self.split_class, "split_fraction": self.split_fraction})
                printd("Sending priorities to {}:".format(address))
                printd(r.text)
            except Exception as e:
                printd(e)
                printd("Skipping this report.")

    # def report_priorities(self):  # Report to hosts new ratios
    #     for address in self.current_hosts:
    #         try:
    #             r = requests.post(PRIORITIES_URL.format(address), data=self.final_priorities)
    #             print("Sending priorities to {}:".format(address))
    #             print(r.text)
    #         except Exception as e:
    #             print(e)
    #             print("Skipping this report.")


if __name__ == '__main__':
    print(sys.argv, flush=True)
    if len(sys.argv) < 2:
        print("Usage: ./tenant.py <host ip>")
        exit(1)
    if "-t" in sys.argv:
        threads = int(sys.argv[sys.argv.index("-t") + 1])
    else:
        threads = 4

    if "-i" in sys.argv:
        AGGREGATION_INTERVAL = int(sys.argv[sys.argv.index("-i") + 1])
    
    host_addr = sys.argv[1]
    host_usage = {}

    usage_queue = multiprocessing.Queue()
    aggregation_task = AggregationProcess(usage_queue)
    # asyncio.run(aggregation_task.run())
    aggregation_task.start()
    if DEBUG:
        app.run(port=5000, host=host_addr)
    else:
        serve(app, host=host_addr, port=5000, threads=threads)


