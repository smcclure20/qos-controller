from flask import Flask, request, Response, make_response
import time
import multiprocessing
import requests
app = Flask(__name__)

PRIO_BANDWIDTH = 128000
PRIORITY_FORMAT = "prio_{}"
PRIORITY_NAME_FORMAT = "{}_prio_{}"
AGGREGATION_INTERVAL = 10
PRIORITIES_URL = 'http://{}/priorities'



@app.post('/usage/')
def record_usage():
    host_name = request.form.get("name")
    print("Received usage update from {}".format(host_name))
    host_usage = request.form.to_dict()
    host_usage.pop("name")
    usage_queue.put(host_usage)
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
        print("Starting aggregation process")
        while True:
            time.sleep(AGGREGATION_INTERVAL)
            print("Calculating priorities...")
            self.clear_totals()
            self.aggregate_tenant()
            self.calculate_priority()
            self.report_priorities()
            print("Updated priority traffic ratios:")
            print("split class {}; bw fraction {}".format(self.split_class, self.split_fraction))

    def aggregate_tenant(self):
        print("Checking queue")
        while not self.usage_queue.empty():
            update = self.usage_queue.get()
            self.current_hosts.append(update.pop("address"))
            for key in update.keys():
                priority = int(key.split("_")[-1])
                if priority in self.total_usage.keys():
                    self.total_usage[priority] += update[key]
                else:
                    self.total_usage[priority] = update[key]

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
            print("Priority {}: usage {}. Remaining {}".format(priority, self.total_usage[priority], remaining))
            if float(self.total_usage[priority]) > remaining:
                self.split_class = priority
                self.split_fraction = remaining / float(self.total_usage[priority])
            remaining -= float(self.total_usage[priority])
            priority += 1

        # If not overusing the bandwidth, split traffic class is the lowest priority one
        if self.split_class is None:
            priority = len(self.total_usage.keys()) - 1
            while priority > 0 and float(self.total_usage[priority]) == 0:
                priority -= 1
            self.split_class = priority if priority > 0 else 0
            self.split_fraction = remaining / float(self.total_usage[self.split_class]) if self.split_class in self.total_usage.keys() else 0


    def report_priorities(self):  # Report to hosts new ratios
        for address in self.current_hosts:
            try:
                r = requests.post(PRIORITIES_URL.format(address), data={"split_class": self.split_class, "split_fraction": self.split_fraction})
                print("Sending priorities to {}:".format(address))
                print(r.text)
            except Exception as e:
                print(e)
                print("Skipping this report.")

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
    host_usage = {}
    usage_queue = multiprocessing.Queue()
    aggregation_task = AggregationProcess(usage_queue)
    aggregation_task.start()
    app.run(port=5000)


