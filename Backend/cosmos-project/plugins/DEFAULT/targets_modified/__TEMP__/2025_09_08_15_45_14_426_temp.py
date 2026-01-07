from openc3.script.suite import Suite, Group

# Group class name should indicate what the scripts are testing
class Power(Group):
  # Methods beginning with script_ are added to Script dropdown
  def script_power_on(self):
      # Using Group.print adds the output to the Test Report
      # This can be useful for requirements verification, QA notes, etc
      Group.print("Verifying requirement SR-1")
      self.configure()

  # Other methods are not added to Script dropdown
  def configure(self):
      pass

  def setup(self):
      # Run when Group Setup button is pressed
      # Run before all scripts when Group Start is pressed
      pass

  def teardown(self):
      # Run when Group Teardown button is pressed
      # Run after all scripts when Group Start is pressed
      pass

class TestSuite(Suite):
  def __init__(self):
      self.add_group(Power)

  def setup(self):
      # Run when Suite Setup button is pressed
      # Run before all groups when Suite Start is pressed
      pass

  def teardown(self):
      # Run when Suite Teardown button is pressed
      # Run after all groups when Suite Start is pressed
      pass
