#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <pthread.h>
#include "file_transfer.h"

#define MAX_PAYLOAD_LEN 1400
#define APP_ID 137
#define PORT 8129
#define SERVER_IP "127.0.0.1"

int packet_counter = 1;
int socket_fd;

typedef enum {
    FT_ACK_MODE,
    FT_UNACK_MODE
} ack_mode_e;

uint8_t ft_config_ack_unack_mode(ack_mode_e mode);

/* ---------- Helpers for pretty prints ---------- */
static void hexdump(const char *label, const uint8_t *buf, size_t len) {
    printf("%s (%zu bytes):\n", label, len);
    for (size_t i = 0; i < len; i++) {
        printf("%02X ", buf[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }
    if (len % 16 != 0) printf("\n");
}

static void hexdump_compact(const char *label, const uint8_t *buf, size_t len, size_t max_show) {
    printf("%s (%zu bytes): ", label, len);
    size_t n = len < max_show ? len : max_show;
    for (size_t i = 0; i < n; i++) printf("%02X", buf[i]);
    if (len > max_show) printf("..."); 
    printf("\n");
}
/* ------------------------------------------------ */

/* Global synchronization for transfer completion */
pthread_mutex_t transfer_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t transfer_cond = PTHREAD_COND_INITIALIZER;
int transfer_complete = 0;
int transfer_status = -1;

/*
 * Upload callback
 */
void upload_app_notificataion_cblk(ft_notification_info *ft_sts) {
    time_t tm; time(&tm);
    printf("\n[UPLOAD] Notification received at %s", ctime(&tm));
    
    pthread_mutex_lock(&transfer_lock);
    switch (ft_sts->status) {
        case transfer_upload_ready: 
            printf("Receiver ready for download\n"); 
            break;
        case transfer_upload_success: 
            printf("Upload success\n");
            transfer_status = 0;
            transfer_complete = 1;
            pthread_cond_signal(&transfer_cond);
            break;
        case crc_error: 
        case invalid_receiver_app_id: 
        case transfer_upload_rejected: 
        case transmission_terminated_receiver_not_responsive: 
        case transmission_terminated_by_rx_node: 
        case transmission_terminated_by_tx_node: 
        default:
            printf("Upload failed with status: %d\n", ft_sts->status);
            transfer_status = 1;
            transfer_complete = 1;
            pthread_cond_signal(&transfer_cond);
            break;
    }
    printf("--------------------------\n");
    pthread_mutex_unlock(&transfer_lock);
}

/*
 * Receiver callback (optional)
 */
void download_app_notificataion_cblk(ft_notification_info *ft_sts) {
    printf("\n[DOWNLOAD] Notification received!\n");
    if (ft_sts->status == transfer_download_ready) {
        printf("Download request received. File size: %d\n", ft_sts->dwld_info.size);
    } else if (ft_sts->status == transfer_download_success) {
        printf("Download success. File saved as: ");
        for (int i = 0; i < ft_sts->dwld_info.path_filename_buf_length; i++)
            printf("%c", ft_sts->dwld_info.storage_path_and_File_name[i]);
        printf("\nSize: %u bytes\n", ft_sts->dwld_info.size);
    } else if (ft_sts->status == crc_error) {
        printf("Download failed / CRC error\n");
    }
    printf("--------------------------\n");
}

uint8_t ft_payload_transmitt_cblk(uint16_t tc_tm_id, uint16_t src_dst_id, uint8_t *payload_ptr, uint16_t payload_len) {
    uint8_t buffer[MAX_PAYLOAD_LEN];
    if (payload_len + 25 > MAX_PAYLOAD_LEN) return 1;
    memset(buffer, 0, sizeof(buffer));

    // SatOS Header
    buffer[0]  = 0x98;
    buffer[1]  = 0xBA;
    buffer[2]  = 0x76;
    buffer[3]  = 0x00;
    buffer[4]  = 0xA5;
    buffer[5]  = 0xAA;
    buffer[6]  = 0xB0;   // changed from 0x40 to 0xB0

    uint32_t epoch_time = (uint32_t)time(NULL);
    buffer[7]  = (epoch_time >> 0) & 0xFF;
    buffer[8]  = (epoch_time >> 8) & 0xFF;
    buffer[9]  = (epoch_time >> 16) & 0xFF;
    buffer[10] = (epoch_time >> 24) & 0xFF;

    buffer[11] = 0x27;
    buffer[12] = 0x01;
    buffer[13] = 0x00;
    buffer[14] = 0x00;
    buffer[15] = 0x03;
    buffer[16] = 0x01;
    buffer[17] = 0x89;   // src/dst id (APP_ID)

    // buffer[18] removed earlier
    buffer[18] = 0x04;

    buffer[19] = (uint8_t)tc_tm_id;  // tc_tm_id (1 byte)

    // NEW BYTE you requested
    buffer[20] = 0x00;

    // Existing 2 bytes
    buffer[21] = 0x01;
    buffer[22] = 0x00;

    // Payload length (shifted by +1)
    buffer[23] = payload_len & 0xFF;        // LSB
    buffer[24] = (payload_len >> 8) & 0xFF; // MSB

    // Payload starts at index 25 now
    memcpy(&buffer[25], payload_ptr, payload_len);

    // Total = header (25 bytes) + payload
    int total_len = payload_len + 25;

    printf("\n[FTM TX] Packet #%d | Total: %d bytes | tc_tm_id=%u src_dst_id=%u payload_len=%u\n",
        packet_counter, total_len, (unsigned)buffer[19], (unsigned)buffer[17], (unsigned)payload_len);

    // Updated dumps
    hexdump("TX Header (first 25 bytes)", buffer, 25);
    hexdump_compact("TX Payload (first 64B hex)", &buffer[25], payload_len, 64);

    packet_counter++;

    if (send(socket_fd, buffer, total_len, 0) < 0) {
        perror("Send failed");
        return 1;
    }
    return 0;
}


/*
 * Receive Thread: bytes from bridge -> unpack -> print EVERYTHING -> feed library
 */
void *receive_thread(void *arg) {
    uint8_t buffer[MAX_PAYLOAD_LEN];

    while (1) {
        int valread = read(socket_fd, buffer, MAX_PAYLOAD_LEN);
        if (valread <= 0) {
            printf("Connection closed.\n");
            exit(0);
        }

        printf("\n[FTM RX] Received %d bytes from bridge\n", valread);
        hexdump("RX Raw", buffer, (size_t)valread);

        if (valread < 23) {
            printf("[FTM RX] ERROR: too small (<23 header)\n");
            continue;
        }

        uint8_t  tc_tm_id    = buffer[18];
        uint8_t  src_dst_id  = buffer[15];
        uint16_t payload_len = (buffer[25] << 8) | buffer[24]; // Little Endian
        uint8_t *payload     = &buffer[26];

        printf("[FTM RX] Parsed header -> tc_tm_id=%u src_dst_id=%u payload_len=%u\n",
               (unsigned)tc_tm_id, (unsigned)src_dst_id, (unsigned)payload_len);
        hexdump_compact("RX Payload (first 128B hex)", payload, payload_len, 128);

        if ((payload_len >= 1 && payload_len <= 1350)) {
            printf("[FTM RX] Forwarding to library: ft_payload_parser(...)\n");
            ft_payload_parser(tc_tm_id, src_dst_id, payload, payload_len);
        } else {
            printf("[FTM RX] Dropped: invalid length or src_dst_id mismatch\n");
        }
        printf("-----------------------------\n");
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    printf("==== FTM Sender with Python Bridge (OpenC3) ====\n");

    if (argc < 5) {
        printf("Usage: %s <filename> <mtu_size> <ftds_delay> <ack_unack_mode>\n", argv[0]);
        return -1;
    }

    char *filename = argv[1];
    int mtu_size = atoi(argv[2]);
    int ftds_delay = atoi(argv[3]);
    int ack_mode = atoi(argv[4]);

    printf("Configuration:\nFilename: %s\nMTU Size: %d\nDelay: %d\nACK Mode: %d\n", 
           filename, mtu_size, ftds_delay, ack_mode);

    struct sockaddr_in serv_addr;
    socket_fd = socket(AF_INET, SOCK_STREAM, 0);
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    serv_addr.sin_addr.s_addr = inet_addr(SERVER_IP);

    if (connect(socket_fd, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("Connection to Python bridge failed");
        return -1;
    }
    printf("Connected to bridge at %s:%d\n", SERVER_IP, PORT);

    // Initialize FTM
    ftm_init();
    ft_register_pld_transmitter_cblk(ft_payload_transmitt_cblk);
    ft_register_sender_app(APP_ID, upload_app_notificataion_cblk);
    ft_register_receiver_app(APP_ID, download_app_notificataion_cblk);

    // Start Receive Thread
    pthread_t rx_thread;
    pthread_create(&rx_thread, NULL, receive_thread, NULL);
    pthread_detach(rx_thread);

    // Check file
    struct stat st;
    if (stat(filename, &st) != 0) {
        perror("File error");
        close(socket_fd);
        return 1;
    }
    if (st.st_size == 0) {
        printf("Error: File exists but size is 0 bytes\n");
        close(socket_fd);
        return 1;
    }
    printf("File %s is ready for transfer (%ld bytes)\n", filename, st.st_size);

    // Configure and start transfer
    ft_config_app_id(APP_ID);
    ft_config_sender_filename_filepath(filename);
    ft_config_mtusize(mtu_size);
    ft_config_ack_unack_mode(ack_mode);
    ft_config_ftds_delay(ftds_delay);
    
    printf("Starting transfer request...\n");
    ft_transfer_request(Start_Transmission_rqst, 0U);

    // Wait for transfer completion
    pthread_mutex_lock(&transfer_lock);
    while (!transfer_complete) {
        pthread_cond_wait(&transfer_cond, &transfer_lock);
    }
    pthread_mutex_unlock(&transfer_lock);

    printf("Exiting with status: %d\n", transfer_status);
    close(socket_fd);
    return transfer_status;
}