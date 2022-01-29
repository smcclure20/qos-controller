#!/bin/bash
PER_NODE_HOSTS="1 400"
INTERVAL=10
SERVER=10.10.1.36
#SERVER_PIDS=""
SERVER_THREADS=8

echo "Starting server with interval $INTERVAL"
ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER "cd qos-controller && python3 tenant.py $SERVER -i $INTERVAL -t $SERVER_THREADS &>./log.out" &
sleep 5
pids=$(ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER pgrep -u ubuntu python3 -d ",")
echo "Server pids: $pids"
echo $pids
        
if [[ "$pids" == "" ]]; then
        exit
else

for hpn in $PER_NODE_HOSTS
do
        echo "Benchmarking $hpn hosts per node..."

        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.51 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.51 -s $hpn -i $INTERVAL &>/dev/null" &
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.123 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.123 -s $hpn -i $INTERVAL &>/dev/null" &
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.236 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.236 -s $hpn -i $INTERVAL &>/dev/null" &
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.107 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.107 -s $hpn -i $INTERVAL &>/dev/null" &

        python3 ./host.py $SERVER:5000 10.10.1.12 -s $hpn -i $INTERVAL &> log.out &
        
        sleep $INTERVAL
        echo "Beginning data collection..."

        ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER "cd qos-controller/benchmark && ./top_total_cpu.sh ./cpu_bench_con4/cpu_5n_"$hpn"hpn_"$INTERVAL"i_"$SERVER_THREADS"t.txt $pids"
        
        echo "done."

        pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.51 pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.123 pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.236 pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.107 pkill python

        sleep $INTERVAL
done
fi

ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER pkill python
