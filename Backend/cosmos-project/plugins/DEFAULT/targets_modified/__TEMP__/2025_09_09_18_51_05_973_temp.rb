schedulefilename = ask("Schedule name")
#ScheduleUpload
file = get_target_file("EMULATOR/#{schedulefilename}")


load 'EMULATOR/lib/schedular.rb'