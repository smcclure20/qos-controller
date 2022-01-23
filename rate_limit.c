#include <linux/jhash.h>
#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

#define IP_TCP 	6
#define IP_UDP 17
#define IP_ICMP 1
#define SPLIT_PRIO 3
#define LOW_PRI 0x10020
#define HI_PRI 0x10010
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
BPF_ARRAY(split_bw, u32, 1); // bandwidth available in the split class
BPF_HASH(eligible_flows_bytes, u32, u32); //track bytes sent for eligible flows
BPF_HASH(eligible_flows_timestamp, u32, u64); // track timestamps of when eligible flows arrived
BPF_HASH(split_flows, u32, u8); // track which flows have been seen and which have not
BPF_ARRAY(hits, u64, 32); // debugging
BPF_ARRAY(portflows, u32, 10); // debugging
BPF_ARRAY(portflows_split_flows, u32, 10); // debugging

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

    // Parse the five tuple and hash for storing info about the flow
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

	// Debugging stuff
    u32 tc_class = 0;
    skb->tc_classid = (__u32) 4;
	tc_class = (u32)4;
	u64* prio = priorities.lookup(&tos_int);

	// Priorities are 1, 2, or 3. Should never be null
	if (prio != NULL){

	    // If in split class, check if it has already been seen
	    if (*prio == SPLIT_PRIO){
		    u8* permitted = split_flows.lookup(&tuple_hash);

            if (permitted != NULL){
                // If the flow has already been permitted, classify accordingly
                if (*permitted == 1){
                    int test = 6;
                    int port_index = tuple.dport - 5020;
                    portflows_split_flows.update(&port_index, &test);
                    tc_class = (u32) HI_PRI;
                    skb->tc_classid = (__u32) tc_class;
                    //ip->tos = (u8) 4;
                }
                // If the flow has been seen before but has not been promoted, it is still eligible
                else{  // should not be doing this per-packet, need some threshold
                    // Calculate the bandwidth consumption of this flow over since seen TODO: Make this since the last timestamp?? <- this might get cleared by the python process
                    eligible_flows_bytes.increment(tuple_hash, tlen);
                    u64 *ts = eligible_flows_timestamp.lookup(&tuple_hash);
//                    u64 now = 0;

//                    u64 now = bpf_ktime_get_ns();
//                    u32 now_bs = (u32) now;
                    u64 time_diff = 0;
                    if (ts != NULL){
//                        u32 ts_bs = (u32) *ts;
                        time_diff = bpf_ktime_get_ns() - *ts;
                        u64 now = bpf_ktime_get_ns();
                        eligible_flows_timestamp.update(&tuple_hash, &now);
                        u32 *bytes = eligible_flows_bytes.lookup(&tuple_hash);
                        u32 flow_bw = 0;
                        if (bytes != NULL){
                            flow_bw = (u32) *bytes / (time_diff / 1000000000);
                            // Find the split class bandwidth
                            int bw_lk = 0;
                            u32* bw = split_bw.lookup(&bw_lk);
                            if (bw != NULL){
                                if ((*bw > flow_bw) && time_diff > 1000000000){
                                    u8 updated_permission = 1;
                                    int port_index = tuple.dport - 5020;
                                    portflows_split_flows.update(&port_index, &updated_permission);
                                    u32 updated_bw = *bw - flow_bw;
                                    split_bw.update(&bw_lk, &updated_bw);
                                    split_flows.update(&tuple_hash, &updated_permission);

                                    tc_class = (u32) HI_PRI;
                                    skb->tc_classid = (__u32) HI_PRI;
                                }
                                else if (time_diff > 1000000000){
                                    u64 now_ts = bpf_ktime_get_ns();
                                    eligible_flows_timestamp.update(&tuple_hash, &now_ts);
                                    u32 bytes_update = (u32) tlen;
                                    eligible_flows_bytes.update(&tuple_hash, &bytes_update);

                                    int test = 7;
                                    int port_index = tuple.dport - 5020;
                                    portflows_split_flows.update(&port_index, &test);

                                    tc_class = (u32) LOW_PRI;
                                    skb->tc_classid = (__u32) tc_class;
                                }
                                // If not currently eligible for promotion, keep in lower class
                                else {
                                    tc_class = (u32) LOW_PRI;
                                    skb->tc_classid = (__u32) tc_class;
                                    u32 bytes_update = (u32) tlen;
                                    eligible_flows_bytes.increment(tuple_hash, bytes_update);
                                }
                            }

                        }
                    }

                }
            }

		    // If the flow is completely new, add to eligible
		    else{ // TODO: how to add bw >0 without breaking things
			    u8 default_permit = 0;
			    split_flows.insert(&tuple_hash, &default_permit);
			    int port_index = tuple.dport - 5020;
			    int test = 5;
	            portflows_split_flows.update(&port_index, &test);
		        u32 bytes_update = (u32) tlen;
		        eligible_flows_bytes.insert(&tuple_hash, &bytes_update);
		        u64 now_ts = bpf_ktime_get_ns();
                eligible_flows_timestamp.insert(&tuple_hash, &now_ts);

                tc_class = (u32) LOW_PRI;
		        skb->tc_classid = (__u32) tc_class;
		    }
		}
		// If not in split priority, put in the class according to its priority in the table
		else{
		    skb->tc_classid = (__u32) (*prio * 16) + 65536;
		    tc_class = (u32)(*prio * 16) + 65536;
		    //ip->tos = (u8) (*prio + 3); // priority 1 -> DSCP 4 (2 -> 5)
		}
	}

	// Logging for debugging
	int port_index = tuple.dport - 5020;
	portflows.update(&port_index, &tc_class);
	hits.increment(skb->tc_classid);
	goto KEEP;

    KEEP:
        //return tc_class;
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
