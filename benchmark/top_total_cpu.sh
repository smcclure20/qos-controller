#!/bin/bash
LOG_FILE="$1"
PIDS="$2"

top -b -d 2 -n 30 -p $PIDS | awk \
    -v cpuLog="$LOG_FILE" -v pids="$PIDS" '
    /^top -/{FS=","; time = $1; time = substr(time, 7, 8); next}
    /Cpu/{FS=","; cpu = $4; split(cpu, a, " "); cpu = a[1];
    	printf "%s %s :: [%s] CPU Usage: %d%%\n", \
            strftime("%Y-%m-%d"), time, pids, 100-cpu > cpuLog
            fflush(cpuLog)}'
