#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

#define IP_TCP 	6
#define IP_UDP 17
#define IP_ICMP 1
#define SPLIT_PRIO 3
/*
  In 802.3, both the source and destination addresses are 48 bits (4 bytes) MAC address.
  6 bytes (src) + 6 bytes (dst) + 2 bytes (type) = 14 bytes
*/
#define ETH_HLEN 14

struct five_tuple {
    unsigned int src;
    unsigned int dst;
    unsigned char protocol;
    unsigned short sport;
    unsigned short dport;
};

BPF_ARRAY(priorities, u64, 32);
BPF_ARRAY(split_bw, float, 1);
BPF_HASH(eligible_flows_bytes, struct five_tuple);
BPF_HASH(eligible_flows_timestamp, struct five_tuple, u64);
BPF_HASH(split_flows, struct five_tuple, int);
BPF_ARRAY(hits, u64, 32);


struct five_tuple parse_tuple(struct __sk_buff *skb){
    struct five_tuple tuple;

    u8 *cursor = 0;

	struct ethernet_t *ethernet = cursor_advance(cursor, sizeof(*ethernet));
	struct ip_t *ip = cursor_advance(cursor, sizeof(*ip));
	tuple.src = ip->src;
	tuple.dst = ip->dst;

	if (ip->nextp == IP_UDP){
	    struct udp_t *udp = cursor_advance(cursor, sizeof(*udp));
	    tuple.protocol = IP_UDP;
	    tuple.sport = udp->sport;
	    tuple.dport = udp->dport;
	}
	else if (ip->nextp == IP_TCP){
	    struct tcp_t *tcp = cursor_advance(cursor, sizeof(*tcp));
	    tuple.protocol = IP_TCP;
	    tuple.sport = tcp->src_port;
	    tuple.dport = tcp->dst_port;
	}
	else{ // must be icmp or invalid

	}

	return tuple;
}

/*eBPF program.
  Filter TCP/UDP/ICMP packets, having payload not empty
  if the program is loaded as PROG_TYPE_SOCKET_FILTER
  and attached to a socket
  return  0 -> DROP the packet
  return -1 -> KEEP the packet and return it to user space (userspace can read it from the socket_fd )
*/
int filter(struct __sk_buff *skb) {

	u8 *cursor = 0;

	struct ethernet_t *ethernet = cursor_advance(cursor, sizeof(*ethernet));

	//filter IP packets (ethernet type = 0x0800) 0x0800 is IPv4 packet
	switch(ethernet->type){
		case 0x0800: goto IP;
	    	default: goto DROP;
	}


	IP: ;
		struct ip_t *ip = cursor_advance(cursor, sizeof(*ip));  // IP header (datagram)
	        u8 tos = (u8) ip->tos;
	        hits.increment(tos);
	        int tos_int = (int) ip->tos;
	        u64* prio = priorities.lookup(&tos_int);
		    if (prio != NULL){
		        if (*prio == SPLIT_PRIO){
		            // if in the split table, let through
		            float* bw = split_bw.lookup((int*)prio);
		            struct five_tuple tuple = parse_tuple(skb);
		            u64* permitted = split_flows.lookup(tuple);
		            if (permitted != NULL && *permitted == 1){
		                // If the flow has already been permitted, classify accordingly
		                skb->tc_classid = 1;
		            }
		            else if (permitted != NULL && permitted == 0 && *bw > 0){
		                // If the flow has been seen before but has not been promoted, it is still eligible
		                eligible_flows_bytes.increment(&tuple, (ip->tlen));
		                u64 *ts = eligible_flows_timestamp.lookup(&tuple);
		                u64 now = bpf_ktime_get_ns(void);
		                u64 *bytes = eligible_flows_bytes.lookup(&tuple);
		                float flow_bw = (float) *bytes / (float)((*ts - now) / 1000000000);
		                if (*bw - flow_bw > 0){
		                    int updated_permission = 1;
		                    float updated_bw = *bw - flow_bw;
		                    split_flows.update(&tuple, &updated_permission);
		                    split_bw.update(&prio, &updated_bw);
		                    skb->tc_classid = 1;
		                }
		            }
		            else if (permitted == NULL && *bw > 0){
		                // If the flow is completely new, add to eligible
		                eligible_flows_bytes.update(tuple, &(ip->tlen));
		                u64 now = bpf_ktime_get_ns(void);
                        eligible_flows_timestamp.update(tuple, &now);
		            }
		        }
		        else{
		            skb->tc_classid = (__u32)*prio;
		        }
		    }
		    goto KEEP;
		}

    KEEP:
        return TC_ACT_OK;
    DROP:
        return TC_ACT_OK;
//    END:
//        return TC_ACT_OK;
//	//keep the packet and send it to userspace returning -1
//	KEEP:
//		return -1;
//
//	//drop the packet returning 0
//	DROP:
//		return 0;
}