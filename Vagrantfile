FileUtils.mkdir_p "./modules"

module_name = "checker"
## Please update the following stuff:
facts       = {
    :example_fact => "foo"
}

## set this this if you need a static ip - could collide with something!
#ip_address  = "192.168.13.87"

## uncomment hostname if you really need it
#hostname = "#{module_name.gsub(/_/, '-')}-vagrant"

Vagrant.configure("2") do |config|
  config.vm.box = 'precise64'
  config.vm.box_url = 'http://files.vagrantup.com/precise64.box'
  config.vm.provision :shell, inline: "cd /vagrant && r10k -v info puppetfile install 2>&1"
  config.vm.synced_folder ".", "/etc/puppet/modules/#{module_name}"
  config.vm.synced_folder ".", "/vagrant"
  
  config.vm.hostname = hostname if defined? hostname
  config.vm.network :private_network, ip: ip_address if defined? ip_address
  config.vm.network :forwarded_port, host: 8080, guest: 8080

  # forward ssh agent DEV-77020
  config.ssh.forward_agent = true

  config.vm.provision :shell do |shell|
    shell.inline = "touch $1 && chmod 0440 $1 && echo $2 > $1"
    shell.args = %q{/etc/sudoers.d/root_ssh_agent "Defaults    env_keep += \"SSH_AUTH_SOCK\""}
  end

  config.vm.provision :puppet do |puppet|
    puppet.manifests_path = "."
    puppet.manifest_file  = "vagrant.pp"
    puppet.options        = ["--verbose", "--hiera_config=/vagrant/hiera.yaml", "--modulepath=/etc/puppet/modules:/vagrant/modules"]
    puppet.facter         = facts
 end

  config.vm.provider "virtualbox" do |vbox|
    vbox.gui = false
    vbox.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
  end

end
