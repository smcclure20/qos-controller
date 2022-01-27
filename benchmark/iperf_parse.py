import os

DIR = "../perf_tests/tput_15t/"
OUTPUT = "./benchmark/throughputs_10s_15t.csv"

def remove_empties(line):
    while len(line) > 10:
        line.remove("")
    return line


output_file = open(OUTPUT, "w")

files = os.listdir(DIR)
files.sort()
print(files)
for file in files:
    if "tput" in file:
        print(file)
        fh = open(DIR + file, "r")
        lines = fh.readlines()
        print(len(lines))
        if (len(lines) < 4):
            continue
        sender = lines[-4].split(" ")
        sender = remove_empties(sender)
        print(sender)
        rate = sender[6]
        fh.close()
        if "default" in file:
            output_file.write("default,{}\n".format(rate))
        elif "bpf" in file:
            output_file.write("bpf,{}\n".format(rate))

output_file.close()
