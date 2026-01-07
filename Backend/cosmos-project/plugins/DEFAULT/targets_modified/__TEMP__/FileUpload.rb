require 'openc3'
require 'open3'

# Ask operator for the schedule file name
filename = ask_string("Enter DTC file name (e.g. ftm_tx_log.json):")
raise "No filename entered" if filename.nil? || filename.strip.empty?

# Get the schedule file from __TEMP__
inp = get_target_file("__TEMP__/#{filename.strip}")
inp_path = inp.path
py  = get_target_file("EMULATOR/lib/ftm_script.py")
py_path = py.path
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
puts  "Python exited 0"
py.unlink
inp.unlink



