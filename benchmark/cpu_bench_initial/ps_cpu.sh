#!/bin/bash

PID="$1"
LOG_FILE="$2"

while true ; do
    echo "$(date) :: [$PID] $(ps -p $PID -o %cpu | tail -1)%" >> $LOG_FILE
    sleep 2
done
