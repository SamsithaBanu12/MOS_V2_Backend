# File Transfer Procedure using FTM Library and OpenC3

This document provides the step-by-step procedure to perform a file transfer between the Ground Station and Payload Server using the FTM library integrated with OpenC3.

---

## Prerequisites

Ensure the following components are set up and running before starting the procedure:

- OpenC3 is running.
- Local MQTT Broker is active on port 2147.
- Gsite is connected with Flatsat.
- Payload Server is powered on.
  Verify using Command ID 212.

---

## Step 1: Configure Sender Parameters

Edit and configure the sender parameters inside the `upload_image.c` file as follows:

```
ft_config_app_id(APP_ID);
ft_config_sender_filename_filepath(filename);
ft_config_mtusize(512);
ft_config_ack_unack_mode(0);
ft_config_ftds_delay(10);
```

These parameters define the file transfer configurations such as application ID, file path, MTU size, acknowledgment mode, and transfer delay.

---

## Step 2: Compile and Run the Sender Controller

Open a terminal and execute the following commands to compile and run the sender controller C code:

```
gcc -pthread upload_image.c -o upload_image -L./lib -lftm_gs
export LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH
```

This will compile the sender program and ensure the shared library path is correctly set.

---

## Step 3: Run the Connector Bridge

The Connector Bridge serves as an interface between the FTM Library and OpenC3, responsible for exchanging Telecommands (TC) and Telemetry (TM).

Run the connector using:

```
python3 new_sender_Connector.py
```

---

## Step 4: Start the Sender Application

Execute the sender application using the following command:

```
./upload_image
```

This will initiate the file transfer process.

---

## Step 5: Monitor File Transfer

If you have SSH access to payload server

To monitor the file transfer progress from the payload server, run:

```
cd /
watch ls -l "<file name>"
```

This continuously updates the file listing to confirm that data is being received.

---

## Step 6: Validate File Transfer

- In Acknowledgment Mode, the sender library will notify successful file transfer completion.
- You can also verify the received file manually on the payload server:

```
cd /opt/antaris/inbound
ls
```

Alternatively, you can validate the transfer by sending the same data as a payload with Command ID 117.

---

End of Document

