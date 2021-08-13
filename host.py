import requests
import time
from flask import Flask, request, Response, make_response
import multiprocessing
from filter import USAGE_FILE, PRIORITIES_FILE
from tenant import PRIORITY_FORMAT

app = Flask(__name__)

REPORTING_INTERVAL = 10
ADDRESS = "127.0.0.1"
PORT = 5001
ADDRESS_FORMAT = "{}:{}"

@app.post('/priorities/')
def set_priorities():
    print("Received priority update")
    priorities = request.form.to_dict()

    with open(PRIORITIES_FILE, "w") as file:
        file.write(str(priorities))

    return make_response(request.form.to_dict())


class ReportProcess(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.current_usage = {}

    def run(self):
        print("Starting reporting process")
        while True:
            time.sleep(REPORTING_INTERVAL)
            self.collect_usage()
            self.send_usage()

    def collect_usage(self):
        # Read BPF usage stats from file
        with open(USAGE_FILE, "r") as file:
            usage_stats = eval(file.read())

        print(usage_stats)
        usage = {}
        for stat in usage_stats:
            usage[PRIORITY_FORMAT.format(stat[0])] = stat[1]
        # usage = {"name": "host1", "address": ADDRESS_FORMAT.format(ADDRESS_FORMA, PORT), "prio_0": 2.5, "prio_1": 15} # Index is priority level, data is gbps
        usage["name"] = "host1"
        usage["address"] = ADDRESS_FORMAT.format(ADDRESS_FORMAT, PORT)
        self.current_usage = usage

    def send_usage(self):
        r = requests.post('http://127.0.0.1:5000/usage', data=self.current_usage)
        print("Sending usage:")
        print(r.text)


if __name__ == "__main__":
    report_task = ReportProcess()
    report_task.start()
    app.run(port=PORT, host=ADDRESS)