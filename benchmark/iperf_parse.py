import os

DIR = "../perf_tests/tput_10s/"
OUTPUT = "./benchmark/throughputs_10s.csv"

def remove_empties(line):
    while len(line) > 10:
        line.remove("")
    return line


output_file = open(OUTPUT, "w")

files = os.listdir(DIR)
files.sort()
print(files)
for file in files:
    if "tput" in file and not "10" in file:
        fh = open(DIR + file, "r")
        lines = fh.readlines()
        sender = lines[-4].split(" ")
        sender = remove_empties(sender)
        print(sender)
        rate = sender[4]
        fh.close()
        if "default" in file:
            output_file.write("default,{}\n".format(rate))
        elif "bpf" in file:
            output_file.write("bpf,{}\n".format(rate))

output_file.close()
