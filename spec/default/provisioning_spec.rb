#PROVISIONING INVARIANCE TEST:
#this test runs 'vagrant provision' two additional times after the initial provisioning triggered by vagrant is completed.
#the output of the two runs is then compared and assumed to be equal.
#if this test fails, the provisioning is not 'stable' meaning one run is not enough to put the system in the desired state.

require 'spec_helper'

def trim_changing_stuff(str) 
    str.gsub!(/version '.*'/, "version 'xyz'")
    str.gsub!(/\/tmp\/vagrant-.*$/, "/tmp/vagrant-shell")
    str.gsub!(/ in (\d*.\d\d) seconds/," in some_amount_of seconds")
    str
end

describe "provisioning" do
    it "should be the same for run 2 and 3" do
        output1 = trim_changing_stuff(%x{vagrant provision})
        output2 = trim_changing_stuff(%x{vagrant provision})
        output1.should eq output2
    end
end