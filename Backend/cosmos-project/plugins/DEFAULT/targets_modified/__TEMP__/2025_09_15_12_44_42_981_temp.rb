
now = Time.now.getutc.to_i
#2 Check the S-Band Health data
choice = message_box("Is S-band health nominal?", "Yes", "No")

if choice == "Yes"
  operator = ask_string("Enter operator name")
  puts "Operator confirmed healthy → continuing script..."
else
  puts "Operator confirmed NOT healthy → stopping script."
  return
end


#3 Sync the current time with the satellite
t0 = Time.now.getutc
year  = t0.year
month = t0.month
date  = t0.day
hours = t0.hour
minutes = t0.min
# MILLISECONDS encodes (sec*1000 + ms)
milliseconds = (t0.sec * 1000) + (t0.usec / 1000)

puts "Sending time set: #{year}-#{format('%02d',month)}-#{format('%02d',date)} " \
     "#{format('%02d',hours)}:#{format('%02d',minutes)} ms=#{milliseconds}"

cmd("EMULATOR 550_OBC_TC_SET_CUR_TIME with " \
    "DA_ID 0x8180, RM_ID 4, TC_ID 0xA602, " \
    "HOURS #{hours}, MINUTES #{minutes}, MILLISECONDS #{milliseconds}, " \
    "DATE #{date}, MONTH #{month}, YEAR #{year}")

# 2) Wait for telemetry to reflect the new date fields
cmd("EMULATOR 581_OBC_TC_GET_CURRENT_TIME with DA_ID 0x8180, RM_ID 4, TC_ID 0xC502")
wait_check("EMULATOR TM_GET_CURRENT_TIME RECEIVED_TIMESECONDS > #{now}", 5)
wait_check("EMULATOR TM_GET_CURRENT_TIME YEAR == #{year}", 5)
wait_check("EMULATOR TM_GET_CURRENT_TIME MONTH == #{month}", 5)
wait_check("EMULATOR TM_GET_CURRENT_TIME DATE == #{date}", 5)
# (Optional) If you have an ack bit/field:
# wait_check("EMULATOR TM_GET_CURRENT_TIME RESPONCE == 1", 5)

# 3) Read back the time items (use 3-arg form to get values, not packet Hash)
yr  = Integer(tlm("EMULATOR", "TM_GET_CURRENT_TIME", "YEAR"))
mon = Integer(tlm("EMULATOR", "TM_GET_CURRENT_TIME", "MONTH"))
day = Integer(tlm("EMULATOR", "TM_GET_CURRENT_TIME", "DATE"))
hr  = Integer(tlm("EMULATOR", "TM_GET_CURRENT_TIME", "HOURS"))
min = Integer(tlm("EMULATOR", "TM_GET_CURRENT_TIME", "MINUTE"))        # singular
ms  = Integer(tlm("EMULATOR", "TM_GET_CURRENT_TIME", "MILLISECONDS"))  # sec*1000 + ms

# 4) Reconstruct satellite UTC: split milliseconds into seconds + remainder
sec = ms / 1000
mss = ms % 1000
sat_time = Time.utc(yr, mon, day, hr, min, sec) + (mss / 1000.0)

# 5) Compare to ground UTC with tolerance
t1 = Time.now.getutc
offset = (sat_time - t1).abs

tolerance_sec = 4.0  # emulator/lab: 0.5–1.0s; RF/real link: 1–2s

puts "Satellite time: #{sat_time.utc.iso8601(3)} | Ground now: #{t1.utc.iso8601(3)}"
puts "Offset: #{offset.round(3)} s (tolerance #{tolerance_sec} s)"
if offset > tolerance_sec
  raise "Time sync failed: offset #{offset.round(3)}s > #{tolerance_sec}s"
else
  puts "Time sync OK: offset #{offset.round(3)}s ≤ #{tolerance_sec}s"
end


choice = message_box("Time Synchronised with satellite", "Ok")


#Get the health buffer dump

cmd("EMULATOR 581_OBC_TC_GET_CURRENT_TIME with DA_ID 0x8180, RM_ID 4, TC_ID 0xC502")

choice = message_box("Health dump done", "Ok")


#Check Schedule Status

def ask_int(prompt, default=nil)
  loop do
    if default.nil?
      s = ask_string(prompt, false)   # do not allow blank
    else
      s = ask_string("#{prompt} (default #{default})", default.to_s)
    end
    begin
      return Integer(s)
    rescue
      message_box("Please enter a valid integer.", "OK")
    end
  end
end

segments_expected = ask_int("Enter SEGMENTS_IN_LUT_1 (expected)")
events_expected   = ask_int("Enter EVENTS_IN_LUT_1 (expected)")

puts "Operator expects: SEGMENTS=#{segments_expected}, EVENTS=#{events_expected}"


cmd("EMULATOR TC_549 with DA_ID 0x8180, RM_ID 4, TC_ID 0xA502, STATUS 1")

timeout_sec = 20


wait_check("EMULATOR 549_TM UL_STATUS_1 == 0", timeout_sec)

wait_check("EMULATOR 549_TM SEGMENTS_IN_LUT_1 == #{segments_expected}", timeout_sec)
wait_check("EMULATOR 549_TM EVENTS_IN_LUT_1 == #{events_expected}", timeout_sec)


ul   = Integer(tlm("EMULATOR", "549_TM", "UL_STATUS_1"))
segs = Integer(tlm("EMULATOR", "549_TM", "SEGMENTS_IN_LUT_1"))
evts = Integer(tlm("EMULATOR", "549_TM", "EVENTS_IN_LUT_1"))

puts "Schedule status confirmed"
puts "    UL_STATUS_1        = #{ul}"
puts "    SEGMENTS_IN_LUT_1  = #{segs} (expected #{segments_expected})"
puts "    EVENTS_IN_LUT_1    = #{evts} (expected #{events_expected})"

display_screen("EMULATOR", "schedule_549.txt" )
wait(5)
clear_screen("EMULATOR", "schedule_549.txt" )
choice = message_box("Is schedule status updated?", "Yes", "No")

if choice == "Yes"
  puts "Operator confirmed"
else
  puts "Operator confirmed NOT updated"
  return
end

#get files in the databse
cmd("EMULATOR 619_TC_GET_FILES_IN_DATABASE with DA_ID 0x8680, RM_ID 4, TC_ID 0xEB02, CRITERIA 5, STATE_PRIORITY 5")
display_screen("EMULATOR", "619.txt" )
wait(8)
clear_screen("EMULATOR", "619.txt" )
choice = message_box("Wanted the highest priority file to be downlinked?", "Yes", "No")

if choice == "Yes"
  puts "Operator confirmed"
else
  puts "Operator confirmed NOT updated"
  return
end

#Downlinking the X-band data
cmd("EMULATOR 615_TC_FTM_START_CMD with DA_ID 0x8680, RM_ID 4, TC_ID 0x4382, FTDS_DELAY 5, MTU 5, RX_CONNECTION_FAILURE 5, SEQUENCE_LOSS_ENABLE_DISABLE 5, ACTIVITY_CHECK 5")

display_screen("EMULATOR", "615.txt" )
wait(5)
clear_screen("EMULATOR", "615.txt" )
choice = message_box("Are the frame counter increasing in X-Band data?", "Yes", "No")

choice = message_box("Downlinking of data started", "Ok")

choice = message_box("Start uploading the schedule file?", "Yes", "No")
#Uploading the schedule file
require 'openc3'
require 'open3'

# Prompt operator for schedule file name (relative to __TEMP__)
schedule_file = ask("Enter schedule file name:")

# Get the schedule file
inp = get_target_file("__TEMP__/#{schedule_file}")
inp_path = inp.path  

# Get the Python script
py  = get_target_file("EMULATOR/lib/schedular_script.py")
py_path = py.path

# Run Python with the schedule file
cmd = ["python3", py_path, inp_path]
puts "Running: #{cmd.join(' ')}"

status = nil
Open3.popen3(*cmd) do |stdin, stdout, stderr, wait_thr|
  stdin.close
  stdout.each_line { |l| puts "[PY] #{l.rstrip}" }
  stderr.each_line { |l| puts "[PY-ERR] #{l.rstrip}" }
  status = wait_thr.value
end

raise "Python failed (exit #{status&.exitstatus})" unless status&.success?

puts "Python exited 0"

# Clean up
py.unlink
inp.unlink

choice = message_box("Schedule file uploaded", "Ok")


choice = message_box("Start uploading the DTC file?", "Yes", "No")

# Clean up
py.unlink
inp.unlink

choice = message_box("DTC file uploaded", "Ok")