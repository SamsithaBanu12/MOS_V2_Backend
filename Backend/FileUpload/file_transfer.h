/*
 * @file file_transfer.h
 * @brief File Transfer Module (FTM) API Header
 *
 * This header provides API declarations for initializing and managing
 * file transfer operations between applications using the FTM.
 *
 * @copyright Copyright 2023 Antaris, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
*/


#ifndef FTM_H_
#define FTM_H_

#include <stdint.h>


/* enumeration for transfer control request */
typedef enum ft_request
{
	Start_Transmission_rqst, 		  // a.	Start File transfer process
	Suspend_Timeout_Mode_rqst, 		// b.	Suspend ongoing transfer process with timeout value
	Resume_Timeout_Mode_rqst, 		// c.	Resume ongoing transfer process
	Terminate_Transmission_rqst, 	// d.	Terminate ongoing transfer process
	Suspend_Savecontext_Mode_rqst, 	// e.	Suspend & Save context of ongoing transfer process
	Suspend_Savecontext_ack_rqst, 	// f.	Suspend & Save context acknowledged
	Suspend_Savecontext_nack_rqst, 	// g.	Suspend & Save context not acknowledged
	Resume_Savecontext_nack_rqst, 	// h.	Resume & Save context not acknowledged
	T_SuspendTimeout, 				      // i.	Not applicable for App usage
	T_Txnode, 						          // j.	Not applicable for App usage
	T_Rxnode, 						          // k.	Not applicable for App usage
	Suspend_Savecontext_Auto_rqst   // l.   Suspend & Save context mode enabled by FTM during SBAND failure

}ft_request;




/* enumeration for notification type */
typedef enum ft_status
{
	transfer_ignore_notification,       // don't care
	transfer_upload_ready,              // receiver has accepted the file upload request (
	transfer_download_ready,            // file download request has been received 
	transfer_otsu,                      // dont't care
	transfer_upload_success, 					  // File upload success status
	transfer_download_success, 					// File download success status
	transfer_suspended, 						    // dont't care, File transfer suspended 
	transfer_suspend_accepted, 				  // dont't care, File transfer suspend accepeted by other node
	transfer_resumed, 							    // dont't care, File transfer resumed
	transfer_resume_accepted, 					// dont't care, File transfer resume accepetd by other node
	transfer_suspended_savecontext, 	  // dont't care, File transfer suspend context save mode
	transfer_suspended_auto_savecontext, 			// dont't care, File transfer suspend context save mode
	transfer_suspend_savecontext_accepeted, 	// dont't care, File transfer suspend context save mode accepetd
	transfer_resumed_restorecontext, 			    // dont't care, File transfer resumed context save mode
	transfer_resume_savecontext_accepeted,		// dont't care, File transfer resumed context save mode accepeted
	transfer_suspend_savecontext_failed, 		  // dont't care, File transfer suspend context save failed
	transfer_resume_restorecontext_failed, 		// dont't care, File transfer resumed context save failed
	storage_not_available, 						        // dont't care, Storage memory unavailable on the receiver side
	transmission_terminated_by_rx_node, 		  // File transfer terminated by the receiver
	transmission_terminated_by_tx_node, 		  // File transfer terminated by the sender
	transmission_terminated_receiver_not_responsive, 	// File transfer terminated by the sender
	tranmission_cancelled_segment_loss_error,	        // dont't care, File transfer cancelled due to continuous segment loss
	crc_error, 									                      // File transfer completed with CRC error
	tx_terminated_suspend_timeout_expired,    	      // dont't care, File transfer cancelled due to suspender timeout expire
	invalid_receiver_app_id,                  	      // FIle upload rejected since Receiver app not registered with FT framework
	transfer_upload_rejected,                         // File upload rejected
	transfer_suspend_tout_not_accepted,               // dont care
	transfer_rseume_tout_not_accepted,                // dont care
	transfer_suspended_savecontext_etended_sts        // dont care
}ft_status_type;


/* file/ data transfer download details */
typedef struct _ft_download_info
{
	uint8_t tx_mode;   		        			    // Reserved
	uint8_t rx_file_id;                     // File ID assigned by sender
	uint8_t *storage_path_and_File_name;		// Downloaded storage path and file name ; valid if tx_mode = FILE
	uint16_t path_filename_buf_length;		  // Size of downloaded file name ; valid if tx_mode = FILE
	uint32_t size;					                // Size of downloaded file 
	uint32_t checksum;                      // Checksum value of downloaded content
	uint8_t *memory_transfer_ptr;           // Reserved
	uint8_t retranmission_status;
}ft_download_info;


/* Context saving information details */
typedef struct 
{
    uint32_t sct_instance_key;
    uint8_t *context_info_buf_ptr;        // context information to be stored in app
    uint16_t context_info_size;           // size of context information available in buffer
}ft_contextsave_info;

 

/* App notification details */
typedef struct ft_app_notificataion_info
{
	uint16_t app_id;                          // application id
	ft_status_type status;   		          // ft status type
	ft_download_info dwld_info;               // only valid if status type is transfer_success
	ft_contextsave_info context_info;         // only valid if status type is transfer_suspended_savecontext
}ft_notification_info;



/** @typedef notify_api
 *  @brief Function pointer type for application notifications.
 */
typedef void    (*notify_api)(ft_notification_info*);


/** @typedef ft_payload_tx_type
 *  @brief Function pointer type for transmitting payload.
 */
typedef uint8_t (*ft_payload_tx_type)(uint16_t tc_tm_id, uint16_t src_dct_id, uint8_t *payload_ptr, uint16_t payload_len);




/**
 * @brief Initializes the FTM service thread.
 */
void ftm_init(void);




/**
 * @brief Thread handler function for FTM when ftm_init() is not used.
 *
 */
void* ft_handler(void*);




/**
 * @brief Registers the payload transmitter callback used by FTM to send data to TCTM manager.
 *
 * @param fp Function pointer to the payload transmit callback.
 *
 */
uint8_t ft_register_pld_transmitter_cblk(ft_payload_tx_type fp);



/**
 * @brief Passes received payload to the FTM service for processing.
 *
 * @param tc_tm_id    - Telecommand/telemetry ID.
 * @param src_dst_id  - Application identifier.
 * @param payload_ptr - Pointer to the FTM payload data.
 * @param payload_len - Length of the payload.
 */
void    ft_payload_parser(uint16_t tc_tm_id, uint8_t src_dst_id, uint8_t *payload_ptr, uint16_t payload_len);



/**
 * @brief Registers sender-side application notification callback.
 *
 * @param app_id - Application identifier.
 * @param app_notify_api - Callback function pointer for notification.
 */
uint8_t ft_register_sender_app(uint16_t app_id, notify_api app_notify_api);



/**
 * @brief Registers receiver-side application notification callback.
 *
 * @param app_id - Application identifier.
 * @param app_notify_api - Callback function pointer for notification.
 */
uint8_t ft_register_receiver_app(uint16_t app_id, notify_api app_notify_api);



/**
 * @brief Sets the sender's file name and path for upload.
 *
 * @param name_and_path File name with full path.
 */
uint8_t ft_config_sender_filename_filepath(char name_and_path[]);



/**
 * @brief Sets the receiver's storage directory for downloads.
 *
 * @param name_and_path Folder path for storing received files.
 */
uint8_t ft_config_receiver_storage_path(char name_and_path[]);



/**
 * @brief Configures delay between sending packets, in milliseconds.
 *
 * @param set Delay duration.
 */
void ft_config_ftds_delay(uint16_t set);



/**
 * @brief Configures the MTU size for segmenting transfer data.
 *
 * @param size MTU size in bytes.
 */
uint8_t ft_config_mtusize(uint16_t size);



/**
 * @brief Sets the application ID for the transfer session.
 *
 * @param app_id Application identifier.
 * @return 0 on success, error code otherwise.
 */
uint8_t ft_config_app_id(uint16_t app_id);



/**
 * @brief Assigns a unique file ID to each transferred file.
 *
 * @param f_id File ID.
 */
void ft_config_file_id(uint8_t f_id);


/**
 * @brief Configures timeout for receiver node in case of connection failure.
 *
 * @param conn_fail_time Timeout value (minimum 45s, must be multiple of 15).
 */
void ft_config_rx_node_conn_failure_time(uint16_t conn_fail_time);



/**
 * @brief Sets the activity check window size.
 *
 * Configures how often to check receiver activity, based on the number of packets sent.
 *
 * @param window_size Number of packets per window.
 */
void ft_config_activity_check_window_size(uint8_t window_size);




/**
 * @brief Initiates file transfer based on configured parameters.
 *
 * @param request Transfer request configuration.
 * @param suspend_timeout_r_sct_db_key Session control or timeout key.
 */
uint8_t ft_transfer_request(ft_request, uint32_t suspend_timeout_r_sct_db_key);




#endif /* FTM_H_ */
