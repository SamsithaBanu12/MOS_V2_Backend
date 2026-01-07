
#Check Beacon
now = Time.now.getutc.to_i
wait_check("EMULATOR 411_BEACON_DATA RECEIVED_TIMESECONDS < #{now}", 5)
wait_check("EMULATOR 411_BEACON_DATA GNSS_FIXSTATUS ==3", 5)
#write all the beacon checks



wait_check("EMULATOR 411_BEACON_DATA GNSS_FIXSTATUS ==3", 5)

value = combo_box("Is S band Health Nominal", 'true', 'false')

#Sync Time
# Get current UTC time
now = Time.now.getutc
year = now.year
month = now.month
date = now.day
hours = now.hour
minutes = now.min
milliseconds = (now.sec * 1000) + (now.usec / 1000)
# Send command with formatted time values
cmd("EMULATOR 550_OBC_TC_SET_CUR_TIME with DA_ID 0x8180, RM_ID 4, TC_ID 0xA602, HOURS #{hours}, MINUTES #{minutes}, MILLISECONDS #{milliseconds}, DATE #{date}, MONTH #{month}, YEAR #{year}")

#Check Time again
wait_check("EMULATOR TM_GET_CURRENT_TIME YEAR == #{year}", 1)
wait_check("EMULATOR TM_GET_CURRENT_TIME MONTH == #{month}", 1)
wait_check("EMULATOR TM_GET_CURRENT_TIME DATE == #{date}", 1)
check_tolerance("EMULATOR TM_GET_CURRENT_TIME HOURS < #{hours}", 1)
check_tolerance("EMULATOR TM_GET_CURRENT_TIME MINUTES < #{minutes}", 1)
check_tolerance("EMULATOR TM_GET_CURRENT_TIME MINUTES < #{seconds}", 1)


#Check Schedule Status
cmd("EMULATOR 581_OBC_TC_GET_CURRENT_TIME with CSPHEADER 2562356736, SOF1 165, SOF2 170, TC_CTRL 0, TIMESTAMP 1745917446, SEQ_NO 9985, SAT_ID 0, GND_ID 0, QOS 3, SA_ID 1, DA_ID 0x8180, RM_ID 4, TC_ID 0xC502, TC_LEN 0")

event = ask("Tutal number of Events")
check("EMULATOR 549_TM EVENTS_IN_LUT_1 == #{event}")

currentsegment = ask("ID of current Segment")
check("EMULATOR 549_TM ID_OF_SEGMENTS_EXPECTED_1 == #{currentsegment}")

wait(5)


#Scheduleupload
schedulefilename = ask("Schedule name")
file = get_target_file("EMULATOR/#{schedulefilename}")

def parse_schedule_file(file_path)
  variables = {}

  File.readlines(file_path).each do |line|
    line.strip!
    next if line.empty? || line.start_with?("#") # skip comments and empty lines

    # Match variable assignment like: schedulefilename = ask("Schedule name")
    if line =~ /^(\w+)\s*=\s*(.+)$/
      var_name = $1
      expression = $2

      # Handle ask("...") → ask operator for input
      if expression =~ /^ask\("(.*)"\)/
        prompt = $1
        value = ask(prompt)
        variables[var_name] = value

      # Handle get_target_file("...") → resolve with interpolation
      elsif expression =~ /^get_target_file\("(.*)"\)/
        raw = $1
        # interpolate #{var} inside string
        interpolated = raw.gsub(/\#\{(\w+)\}/) { variables[$1] }
        value = get_target_file(interpolated)
        variables[var_name] = value
      else
        # literal or unknown expression
        variables[var_name] = expression
      end
    end
  end

  variables
end

vars = parse_schedule_file("schedule.txt")



