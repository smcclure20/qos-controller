import os

DIR = "../../perf_tests/"
OUTPUT = "./throughputs.csv"

output_file = open(OUTPUT, "w")

files = os.listdir()

for file in files:
    if file.contains("tput"):
        fh = open(file, "r")
        lines = fh.readlines()
        sender = lines[-4].split(" ")
        rate = sender[6]
        fh.close()
        if file.contains("default"):
            output_file.write("default,{}".format(rate))
        elif file.contains("bpf"):
            output_file.write("bpf,{}".format(rate))

output_file.close()