import requests
import time
from flask import Flask, request, Response, make_response
import multiprocessing
from tenant import PRIORITY_FORMAT
import sys
from waitress import serve
import asyncio

app = Flask(__name__)

REPORTING_INTERVAL = 10
PORT = 5001
ADDRESS_FORMAT = "{}:{}"
USAGE_FILE = "./usage"
PRIORITIES_FILE = "./prios"
SPLIT_CLASS_BW_CAP_FILE = "./bw_cap"

# TODO: create consistent parsing functions for format of the reports

DEBUG=False
STRESS_TEST=False
HOSTS=1000

def printd(to_print, to_print2=None):
    if DEBUG:
        print(to_print, to_print2) if to_print2 else print(to_print)


@app.post('/priorities/')
def set_priorities():
    printd("Received priority update")
    update = request.form.to_dict()
    priorities = dict.fromkeys(range(0, 32), 1)
    if "split_class" in update:
        priorities[int(update["split_class"])] = 3
        priorities.update(dict.fromkeys(range(int(update["split_class"]) + 1, 32), 2))

        bws = {}
        while not usage_queue.empty():
            bws = usage_queue.get()

        with open(SPLIT_CLASS_BW_CAP_FILE, "w") as file:
            if len(bws.keys()) > 0:
                file.write(str(float(update["split_fraction"]) * float(bws[PRIORITY_FORMAT.format(int(update["split_class"]))])))
                printd("Split bandwidth: ", float(update["split_fraction"]) * float(bws[PRIORITY_FORMAT.format(int(update["split_class"]))]))
    printd("Current priorities:", priorities)

    with open(PRIORITIES_FILE, "w") as file:
        file.write(str(priorities))

    return make_response(request.form.to_dict())

# @app.post('/priorities/')
# def set_priorities():
#     print("Received priority update")
#     priorities = request.form.to_dict()
#     keys = list(priorities.keys())
#     for key in keys:
#         priority_number = int(key.split("_")[-1])
#         priorities[priority_number] = priorities[key]
#         priorities.pop(key)
#
#     with open(PRIORITIES_FILE, "w") as file:
#         file.write(str(priorities))
#
#     return make_response(request.form.to_dict())


class ReportProcess(multiprocessing.Process):
    def __init__(self, usage_queue, aggregator, local_address):
        multiprocessing.Process.__init__(self)
        self.current_usage = {}
        self.usage_queue = usage_queue
        self.aggregator = aggregator
        self.local_addr = local_address

    def run(self):
        asyncio.run(self.run_async())

    async def run_async(self):
        printd("Starting reporting process")
        while True:
            task = asyncio.create_task(self.report())
            done, pending = await asyncio.wait([asyncio.sleep(REPORTING_INTERVAL), task],
                                               timeout=REPORTING_INTERVAL + 1)
            if task in pending:
                print("[WARNING] Reporting process lagging behind interval.", flush=True)

    async def report(self):
        self.collect_usage()
        self.send_usage()

    def collect_usage(self):
        # Read BPF usage stats from file
        with open(USAGE_FILE, "r") as file:
            usage_stats = eval(file.read())

        printd(usage_stats)
        usage = {}
        for stat in usage_stats:
            usage[PRIORITY_FORMAT.format(stat[0])] = stat[1]
        # usage = {"name": "host1", "address": ADDRESS_FORMAT.format(ADDRESS_FORMA, PORT), "prio_0": 2.5, "prio_1": 15} # Index is priority level, data is gbps
        usage["name"] = "host1"
        usage["address"] = self.local_addr
        usage["port"] = PORT
        self.current_usage = usage

    def send_usage(self):
        self.usage_queue.put(self.current_usage)
        try:
            r = requests.post('http://{}/usage'.format(self.aggregator), data=self.current_usage)
            printd("Sending usage:")
            printd(r.text)
        except Exception as e:
            printd("Failed connection.")
            printd(e)

        if STRESS_TEST:
            sent_count = 0
            for i in range(HOSTS - 1):
                sent_count += 1
                self.current_usage["name"] = "host" + str(i+1)
                self.current_usage["address"] = self.local_addr
                self.current_usage["port"] = PORT
                try:
                    r = requests.post('http://{}/usage'.format(self.aggregator), data=self.current_usage)
                    printd("Sending usage:")
                    printd(r.text)
                except Exception as e:
                    printd("Failed connection.")
                    printd(e)
            print("[{}] Sent {} reports".format(time.strftime("%m/%d/%y %H:%M:%S"),
                                                                         sent_count), flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ./host.py <aggregator address> <local address>")
        exit(1)
    if "-s" in sys.argv:
        STRESS_TEST=True
        HOSTS = int(sys.argv[sys.argv.index("-s") + 1])
    if "-i" in sys.argv:
        REPORTING_INTERVAL = int(sys.argv[sys.argv.index("-i") + 1])

    aggregator_addr = sys.argv[1]
    local_addr = sys.argv[2]
    usage_queue = multiprocessing.Queue()
    report_task = ReportProcess(usage_queue, aggregator_addr, local_addr)
    report_task.start()

    if DEBUG:
        app.run(port=PORT, host=local_addr)
    else:
        serve(app, host=local_addr, port=PORT)

