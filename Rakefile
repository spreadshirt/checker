require 'rake'
require 'rspec/core/rake_task'

task :smoketest do
  system("vagrant ssh -c 'sudo su -c /opt/smoketests/run'")
end

RSpec::Core::RakeTask.new(:spec) do |t|
    t.pattern = 'spec/*/*_spec.rb'
end
#task :spec => :smoketest