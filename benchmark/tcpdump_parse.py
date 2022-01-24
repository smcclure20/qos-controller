FILE = "../perf_tests/tcpdump_5.out"

fd = open(FILE, "r")

total = 0
for line in fd.readlines():
    words = line.split(" ")
    if "IP" in words:
        length = int(words[16].strip().strip(")"))
        total += length
print(total)

fd.close()
