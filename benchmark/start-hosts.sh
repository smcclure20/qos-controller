#!/bin/bash
PER_NODE_HOSTS="750 900"
INTERVAL=10
SERVER=10.10.1.36
#SERVER_PIDS=""
SERVER_THREADS=8
BENCH_DIR="./cpu_bench_con6/"

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
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.100 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.100 -s $hpn -i $INTERVAL &>/dev/null" &
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.57 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.57 -s $hpn -i $INTERVAL &>/dev/null" &
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.90 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.90 -s $hpn -i $INTERVAL &>/dev/null" &
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.38 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.38 -s $hpn -i $INTERVAL &>/dev/null" &
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.83 "cd qos-controller && python3 host.py $SERVER:5000 10.10.1.83 -s $hpn -i $INTERVAL &>/dev/null" &

        python3 ./host.py $SERVER:5000 10.10.1.12 -s $hpn -i $INTERVAL &> log.out &
        
        sleep $INTERVAL
        echo "Beginning data collection..."

        ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER "cd qos-controller/benchmark && ./top_total_cpu.sh "$BENCH_DIR"cpu_10n_"$hpn"hpn_"$INTERVAL"i_"$SERVER_THREADS"t.txt $pids"
        
        echo "done."

        pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.51 pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.123 pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.236 pkill python
        ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.107 pkill python
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.100 pkill python
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.57 pkill python
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.90 pkill python
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.38 pkill python
	ssh -i ~/bpf-tester-key-aws.pem ubuntu@10.10.1.83 pkill python

        sleep $INTERVAL
	sleep $INTERVAL
done
fi

ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER pkill python
