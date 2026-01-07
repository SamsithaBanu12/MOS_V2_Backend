#Time Syncronization procedure
now = Time.now.getutc.to_i
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

