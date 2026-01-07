require 'openc3/script/suite.rb'

# Group class name should indicate what the scripts are testing
class Power < OpenC3::Group
  # Methods beginning with script_ are added to Script dropdown
  def script_power_on
    # Using OpenC3::Group.puts adds the output to the Test Report
    # This can be useful for requirements verification, QA notes, etc
    OpenC3::Group.puts "Verifying requirement SR-1"
    configure()
  end

  # Other methods are not added to Script dropdown
  def configure
  end

  def setup
    # Run when Group Setup button is pressed
    # Run before all scripts when Group Start is pressed
  end

  def teardown
    # Run when Group Teardown button is pressed
    # Run after all scripts when Group Start is pressed
  end
end

class TimeSync < OpenC3::Suite
  def initialize
    add_group('Power')
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
  end
  def setup
    # Run when Suite Setup button is pressed
    # Run before all groups when Suite Start is pressed
  end
  def teardown
    # Run when Suite Teardown button is pressed
    # Run after all groups when Suite Start is pressed
  end
end
