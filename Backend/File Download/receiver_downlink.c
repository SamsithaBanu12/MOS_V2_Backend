#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>

#include "file_transfer.h"

#define PORT 8129
#define MAX_PAYLOAD_LEN 1400
#define APP_ID 134

typedef enum {
    FT_ACK_MODE,
    FT_UNACK_MODE
} ack_mode_e;

uint8_t ft_config_ack_unack_mode(ack_mode_e mode);


int socket_fd;

/*
 * Callback: Uplink status
 */
void upload_app_notificataion_cblk(ft_notification_info *ft_sts) {
    time_t now;
    time(&now);
    printf("\n[UPLOAD STATUS] %s", ctime(&now));

    switch (ft_sts->status) {
        case transfer_upload_ready:  printf("Receiver ready for download\n"); break;
        case transfer_upload_success: printf("Upload success\n"); break;
        case crc_error: printf("Upload failed / CRC error\n"); break;
        case invalid_receiver_app_id: printf("Receiver App ID not registered\n"); break;
        case transfer_upload_rejected: printf("Upload rejected due to FTCI decode issue\n"); break;
        case transmission_terminated_receiver_not_responsive: printf("Receiver not responsive\n"); break;
        case transmission_terminated_by_rx_node: printf("Upload terminated by receiver\n"); break;
        case transmission_terminated_by_tx_node: printf("Upload terminated by sender\n"); break;
        default: printf("Unknown upload status: %d\n", ft_sts->status); break;
    }

    printf("----------------------------\n");
}

/*
 * Callback: Downlink (Receiver side)
 */
void download_app_notificataion_cblk(ft_notification_info *ft_sts) {
    time_t now;
    time(&now);
    printf("\n[DOWNLOAD STATUS] %s", ctime(&now));

    switch (ft_sts->status) {
        case transfer_download_ready:
            printf("Download ready. File size: %d\n", ft_sts->dwld_info.size);
            break;
        case transfer_download_success:
            printf("Download success! Saved to: ");
            for (int i = 0; i < ft_sts->dwld_info.path_filename_buf_length; i++)
                printf("%c", ft_sts->dwld_info.storage_path_and_File_name[i]);
            printf("\nFile size: %u bytes\n", ft_sts->dwld_info.size);
            break;
        case crc_error:
            printf("Download failed / CRC error\n");
            break;
        case transmission_terminated_by_rx_node:
            printf("Download terminated by receiver\n");
            break;
        case transmission_terminated_by_tx_node:
            printf("Download terminated by sender\n");
            break;
        default:
            printf("Unknown download status: %d\n", ft_sts->status); break;
    }

    printf("----------------------------\n");
}

/*
 * Transmit callback (used by FTM to send ACKs etc.)
 */
uint8_t ft_payload_transmitt_cblk(uint16_t tc_tm_id, uint16_t src_dst_id,
                                  uint8_t *payload_ptr, uint16_t payload_len) {
    uint8_t tx_buffer[MAX_PAYLOAD_LEN];
    if (payload_len + 24 > MAX_PAYLOAD_LEN) return 1;

    tx_buffer[0]  = 0x98;
    tx_buffer[1]  = 0xBA;
    tx_buffer[2]  = 0x76;
    tx_buffer[3]  = 0x00;

    // 2. SOF1
    tx_buffer[4]  = 0xA5;

    // 3. SOF2
    tx_buffer[5]  = 0xAA;

    // 4. TC_CTRL
    tx_buffer[6]  = 0x40;

    // 5. Timestamp (4 bytes, little endian)
    uint32_t epoch_time = (uint32_t)time(NULL);
    tx_buffer[7]  = (epoch_time >> 0) & 0xFF;
    tx_buffer[8]  = (epoch_time >> 8) & 0xFF;
    tx_buffer[9]  = (epoch_time >> 16) & 0xFF;
    tx_buffer[10] = (epoch_time >> 24) & 0xFF;

    // 6. Sequence Number (0x2701, little endian)
    tx_buffer[11] = 0x27;
    tx_buffer[12] = 0x01;

    // 7. Satellite ID
    tx_buffer[13] = 0x00;

    // 8. Ground ID
    tx_buffer[14] = 0x00;

    // 9. QoS
    tx_buffer[15] = 0x03;

    // 10. Source ID
    tx_buffer[16] = 0x01;

    // 11. Destination ID (0x8180, little endian)
    tx_buffer[17] = 0x86;
    tx_buffer[18] = 0x80;

    // 12. RM ID
    tx_buffer[19] = 0x04;
    tx_buffer[20] = (uint8_t)tc_tm_id;  // 1 byte tc_tm_id

    // Little Endian payload length (LSB first)
    tx_buffer[21] = payload_len & 0xFF;          // LSB
    tx_buffer[22] = (payload_len >> 8) & 0xFF;   // MSB
    memcpy(&tx_buffer[23], payload_ptr, payload_len);

    send(socket_fd, tx_buffer, payload_len + 24, 0);
    return 0;
}

/*
 * Thread to handle incoming FTM packets
 */
void *receive_thread(void *arg) {
    uint8_t buffer[MAX_PAYLOAD_LEN];

    while (1) {
        int bytes = read(socket_fd, buffer, MAX_PAYLOAD_LEN);
        if (bytes <= 0) {
            printf("Connection closed or error.\n");
            exit(1);
        }

        if (bytes < 5) {
            printf("[WARN] Incomplete packet received (%d bytes)\n", bytes);
            continue;
        }

        uint8_t  tc_tm_id    = buffer[19];
        uint8_t  src_dst_id  = buffer[15];
        uint16_t payload_len = (buffer[23] << 8) | buffer[22]; // Little Endian
        uint8_t *payload     = &buffer[24];
        printf("\n[RECEIVED] ID: %u | From: %u | Length: %u\n", tc_tm_id, src_dst_id, payload_len);

        if (payload_len >= 8 && payload_len <= 1350 &&
            src_dst_id == APP_ID && tc_tm_id >= 100 && tc_tm_id <= 107) {
            ft_payload_parser(tc_tm_id, src_dst_id, payload, payload_len);
        } else {
            printf("[ERROR] Corrupted or unexpected packet\n");
        }
    }

    return NULL;
}

/*
 * Main entry point
 */
int main() {
    struct sockaddr_in addr;
    socklen_t addrlen = sizeof(addr);

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(PORT);

    bind(server_fd, (struct sockaddr *)&addr, sizeof(addr));
    listen(server_fd, 1);

    printf("=== Ground Station Receiver (FTM) ===\nWaiting for sender on port %d...\n", PORT);
    socket_fd = accept(server_fd, (struct sockaddr *)&addr, &addrlen);
    printf("Sender connected.\n");

    // 1. Initialize FTM
    ftm_init();

    // 2. Register all callbacks
    ft_register_pld_transmitter_cblk(ft_payload_transmitt_cblk);
    ft_register_sender_app(APP_ID, upload_app_notificataion_cblk);
    ft_register_receiver_app(APP_ID, download_app_notificataion_cblk);
    ft_config_ack_unack_mode(1);

    // 3. Start listening thread
    pthread_t tid;
    pthread_create(&tid, NULL, receive_thread, NULL);
    pthread_join(tid, NULL);

    return 0;
}
