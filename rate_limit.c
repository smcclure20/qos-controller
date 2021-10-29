#include <linux/jhash.h>
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
BPF_HASH(eligible_flows_bytes, u32, u64);
BPF_HASH(eligible_flows_timestamp, u32, u64);
BPF_HASH(split_flows, u32, int);
BPF_ARRAY(hits, u64, 32);
BPF_ARRAY(portflows, u32, 10);

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
	struct ip_t *ip = cursor_advance(cursor, sizeof(*ip));

	struct five_tuple tuple;
	tuple.src = ip->src;
	tuple.dst = ip->dst;
	u8 tos = (u8) ip->tos;
    int tos_int = (int) ip->tos;
    unsigned short tlen = ip->tlen;

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
	u32 tuple_hash = (u32)jhash(&tuple, sizeof(tuple),(u32)0);
    u32 tc_class = 0;
    skb->tc_classid = (__u32) 3;
	tc_class = (u32)3;
	u64* prio = priorities.lookup(&tos_int);
	if (prio != NULL){
	    if (*prio == SPLIT_PRIO){
		    // if in the split table, let through
		    int bw_lk = 0;
		    float* bw = split_bw.lookup(&bw_lk);
		    if (bw == NULL){
			    float default_bw = 0.0;
		        bw = &default_bw;
		    }
		    int* permitted = split_flows.lookup(&tuple_hash);
		    if (permitted != NULL && *permitted == 1){
		        // If the flow has already been permitted, classify accordingly
		        skb->tc_classid = (__u32) 1;
		        tc_class = (u32)*prio;
		        //ip->tos = (u8) 4;
		    }
		    else if (permitted != NULL && permitted == 0 && *bw > 0){  // TODO: THIS IS NOT WORKING!!!!!!
		        // If the flow has been seen before but has not been promoted, it is still eligible
		        eligible_flows_bytes.increment(tuple_hash, tlen);
		        u64 *ts = eligible_flows_timestamp.lookup(&tuple_hash);
		        u64 now = bpf_ktime_get_ns();
		        u64 *bytes = eligible_flows_bytes.lookup(&tuple_hash);
		        float flow_bw = (float) *bytes / (float)((*ts - now) / 1000000000);
		        if (*bw - flow_bw > 0){
		            int updated_permission = 1;
		            float updated_bw = *bw - flow_bw;
		            split_flows.insert(&tuple_hash, &updated_permission);
		            split_bw.update(&bw_lk, &updated_bw);

		            skb->tc_classid = (__u32)1;
		            tc_class = (u32)*prio;
		            //ip->tos = (u8) 4;
		        }
		        else {
		            skb->tc_classid = (__u32) 2;
		            tc_class = (u32)*prio;
		        }
		    }
		    else if(permitted == NULL){ // TODO: how to add bw >0 without breaking things
		        // If the flow is completely new, add to eligible
			    int default_permit = 0;
			    split_flows.insert(&tuple_hash, &default_permit);
		        u64 bytes_update = (u64) tlen;
		        eligible_flows_bytes.insert(&tuple_hash, &bytes_update);
		        u64 now_ts = bpf_ktime_get_ns();
                eligible_flows_timestamp.insert(&tuple_hash, &now_ts);

                skb->tc_classid = (__u32) 2;
                tc_class = (u32)*prio;
		    }
		    else{
		        skb->tc_classid = (__u32) 2;
		        tc_class = (u32)*prio;
		    }
		}
		else{
		    skb->tc_classid = (__u32) *prio;
		    tc_class = (u32)*prio;
		    //ip->tos = (u8) (*prio + 3); // priority 1 -> DSCP 4 (2 -> 5)
		}
	}
	int port_index = tuple.dport - 5020;
//	u32 tc_class = (u32)skb->tc_classid;
	portflows.update(&port_index, &tc_class);
	hits.increment(skb->tc_classid);
	goto KEEP;

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
