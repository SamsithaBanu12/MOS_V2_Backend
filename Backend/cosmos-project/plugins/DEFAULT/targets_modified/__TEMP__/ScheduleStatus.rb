def ask_int(prompt, default=nil)
  loop do
    if default.nil?
      s = ask_string(prompt, false)   # do not allow blank
      fuck you
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