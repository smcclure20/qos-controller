#!/bin/bash
PER_NODE_HOSTS="1 2 5 10 20 50 75"
INTERVAL=10
SERVER=10.10.1.36
#SERVER_PIDS=""
SERVER_THREADS=8
BENCH_DIR="./cpu_bench_con7/"
HELPER_NODES="10.10.1.182 10.10.1.46 10.10.1.254 10.10.1.229 10.10.1.152 10.10.1.249 10.10.1.130 10.10.1.121 10.10.1.215 10.10.1.106 10.10.1.83 10.10.1.105 10.10.1.218 10.10.1.115 
10.10.1.222 10.10.1.221 10.10.1.203 10.10.1.33 10.10.1.61 10.10.1.42 10.10.1.179 10.10.1.174 10.10.1.13 10.10.1.117 10.10.1.58 10.10.1.253 10.10.1.10 10.10.1.214 
10.10.1.247 10.10.1.51 10.10.1.208 10.10.1.49 10.10.1.184 10.10.1.157 10.10.1.173 10.10.1.9 10.10.1.74 10.10.1.103 10.10.1.231 10.10.1.211 10.10.1.41 10.10.1.79 10.10.1.227 
10.10.1.185 10.10.1.26 10.10.1.98 10.10.1.205 10.10.1.94 10.10.1.45 10.10.1.35 10.10.1.75 10.10.1.68 10.10.1.148 10.10.1.127 10.10.1.161 10.10.1.199 10.10.1.146 10.10.1.156 
10.10.1.191 10.10.1.88 10.10.1.217 10.10.1.25 10.10.1.72 10.10.1.104 10.10.1.101 10.10.1.108 10.10.1.143 10.10.1.113 10.10.1.81 10.10.1.21 10.10.1.133 10.10.1.186 
10.10.1.70 10.10.1.140 10.10.1.197 10.10.1.47 10.10.1.69 10.10.1.102 10.10.1.147 10.10.1.180 10.10.1.224 10.10.1.171 10.10.1.155 10.10.1.149 10.10.1.206 10.10.1.145 10.10.1.168
10.10.1.176 10.10.1.37 10.10.1.216 10.10.1.159 10.10.1.190 10.10.1.144 10.10.1.48 10.10.1.237 10.10.1.232 10.10.1.65 10.10.1.150 10.10.1.40"
DRAIN=""

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

	for ip in $HELPER_NODES
	do
        	ssh -i ~/bpf-tester-key-aws.pem ubuntu@$ip "cd qos-controller && python3 host.py $SERVER:5000 $ip -s $hpn -i $INTERVAL &>/dev/null" &
	done

        python3 ./host.py $SERVER:5000 10.10.1.12 -s $hpn -i $INTERVAL &> log.out &
        
        sleep $INTERVAL
        echo "Beginning data collection..."

        ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER "cd qos-controller/benchmark && ./top_total_cpu.sh "$BENCH_DIR"cpu_100n_"$hpn"hpn_"$INTERVAL"i_"$SERVER_THREADS"t.txt $pids"
        
        echo "done."

        pkill python

	for ip in $HELPER_NODES
	do 
		ssh -i ~/bpf-tester-key-aws.pem ubuntu@$ip pkill python
	done

        sleep $INTERVAL
	sleep $INTERVAL
done
fi

ssh -i ~/bpf-tester-key-aws.pem ubuntu@$SERVER pkill python
