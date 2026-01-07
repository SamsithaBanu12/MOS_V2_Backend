#### Step 1

## In terminal compile and run the receiver controller C code first with the following commands.

1. gcc -pthread receiver_downlink.c -o receiver_downlink -L./lib -lftm_gs

2. export LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH

3. ./receiver_downlink


### Step 2

## Run the connector bridge between FTM Library and OpenC3 , which is responsible for forwarding the TC/TM's.

1. python3 receiver_connector.py


