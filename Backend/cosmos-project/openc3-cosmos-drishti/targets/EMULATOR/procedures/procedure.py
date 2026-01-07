# Script Runner test script
cmd("EMULATOR EXAMPLE")
wait_check("EMULATOR STATUS BOOL == 'FALSE'", 5)
