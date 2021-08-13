#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

#define IP_TCP 	6
#define IP_UDP 17
#define IP_ICMP 1
/*
  In 802.3, both the source and destination addresses are 48 bits (4 bytes) MAC address.
  6 bytes (src) + 6 bytes (dst) + 2 bytes (type) = 14 bytes
*/
#define ETH_HLEN 14

BPF_ARRAY(counts, u64, 32);

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
	        switch (ip->nextp){
			case 17: goto UDP;
			default: goto DROP;
		}

	UDP: ;
		struct udp_t *udp = cursor_advance(cursor, sizeof(*udp));
		switch (udp->dport) {
    			case 4789: goto RECORD;
    			default: goto DROP;
  		}

  	RECORD: ;
		struct vxlan_t *vxlan = cursor_advance(cursor, sizeof(*vxlan));
		counts.increment(31, vxlan->key);
		counts.increment(vxlan->key, ip->tlen);
		goto KEEP;

    KEEP:
        return TC_ACT_OK;
    DROP:
        return TC_ACT_OK;
//    END:
//        return TC_ACT_OK;
}