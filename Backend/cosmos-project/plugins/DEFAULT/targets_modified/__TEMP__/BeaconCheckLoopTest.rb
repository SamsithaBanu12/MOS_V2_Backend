require 'openc3/script/suite.rb'
# Group class name should indicate what the scripts are testing
class Power < OpenC3::Group
  # Methods beginning with script_ are added to Script dropdown
  def script_power_on
    # Using OpenC3::Group.puts adds the output to the Test Report
    # This can be useful for requirements verification, QA notes, etc
    now = Time.now.getutc.to_i
    wait_check("EMULATOR 411_BEACON_DATA RECEIVED_TIMESECONDS < #{now}", 10)
    wait_check("EMULATOR 411_BEACON_DATA GNSS_FIXSTATUS ==0", 5)
    gnss_status = tlm("EMULATOR 411_BEACON_DATA GNSS_FIXSTATUS")
    adcs_op_mode = tlm("EMULATOR 411_BEACON_DATA ADCS_OP_MODE")
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
class TestSuite < OpenC3::Suite
  def initialize
    add_group('Power')
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