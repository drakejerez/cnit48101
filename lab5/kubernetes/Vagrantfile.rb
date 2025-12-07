# -*- mode: ruby -*-
# vi: set ft=ruby :

ENV['VAGRANT_NO_PARALLEL'] = 'yes'

VAGRANT_BOX         = "ubuntu/jammy64"
VAGRANT_BOX_VERSION = "20240207.0.0"
CPUS_MASTER_NODE    = 2
CPUS_WORKER_NODE    = 2
MEMORY_MASTER_NODE  = 8192
MEMORY_WORKER_NODE  = 6144
WORKER_NODES_COUNT  = 2

# Optional MetalLB toggle via an environment variable:
# Enable by running: ENABLE_METALLB=true vagrant up master
# Optional interface (if your script uses it): METALLB_L2_INTERFACE=eth1
ENABLE_METALLB       = ENV.fetch('ENABLE_METALLB', 'false').downcase == 'true'
METALLB_L2_INTERFACE = ENV['METALLB_L2_INTERFACE'] # optional; may be empty

# Optional OpenEBS toggle via an environment variable: 
# Enable by running:
#     ENABLE_OPENEBS=true vagrant up master
#     ENABLE_OPENEBS=true OPENEBS_ENGINE=localpv vagrant up master
# Optional: OPENEBS_ENGINE=localpv|zfs|mayastor (your script can decide defaults)
ENABLE_OPENEBS = ENV.fetch('ENABLE_OPENEBS', 'false').downcase == 'true'
OPENEBS_ENGINE = ENV['OPENEBS_ENGINE'] # # optional; may be empty


Vagrant.configure(2) do |config|

  config.vm.synced_folder "src/", "/srv/join"
  
  # Kubernetes Master Server
  config.vm.define "master" do |node|
    node.trigger.after :up do |mScripts|
        mScripts.run_remote = {inline: "sudo /opt/bootstrap.sh -v && sudo KUBECONFIG=/etc/kubernetes/admin.conf /opt/bootstrap_master.sh -v && sudo KUBECONFIG=/etc/kubernetes/admin.conf /opt/bootstrap_metallb.sh -v"}
    end
    node.vm.box               = VAGRANT_BOX
    node.vm.box_check_update  = false
    node.vm.box_version       = VAGRANT_BOX_VERSION
    node.vm.hostname          = "master.example.com"

    node.vm.network "private_network", ip: "172.16.16.100"

    node.vm.provider :virtualbox do |v|
        v.name    = "master"
        v.memory  = MEMORY_MASTER_NODE
        v.cpus    = CPUS_MASTER_NODE
    end

    node.vm.provider :libvirt do |v|
        v.memory  = MEMORY_MASTER_NODE
        v.nested  = true
        v.cpus    = CPUS_MASTER_NODE
    end

    #  node.vm.provision "shell", path: "bootstrap_master.sh"
    config.vm.cloud_init :user_data do |cloud_init|
        cloud_init.content_type = "text/cloud-config"
        cloud_init.path = "master.yaml"
    end
    
    # Optional MetalLB provisioning on master
    if ENABLE_METALLB
        metallb_env = {}
        metallb_env["METALLB_L2_INTERFACE"] = METALLB_L2_INTERFACE unless METALLB_L2_INTERFACE.to_s.empty?
    #    node.vm.provision "shell", path: "bootstrap_metallb.sh", env: metallb_env
    end
    # End MetalLB provisioning block

    # # Optional OpenEBS provisioning on master
    # if ENABLE_OPENEBS
    #   openebs_env = {}
    #   openebs_env["OPENEBS_ENGINE"] = OPENEBS_ENGINE unless OPENEBS_ENGINE.to_s.empty?
    #   node.vm.provision "shell", path: "bootstrap_openebs.sh", env: openebs_env
    # end
    # # End OpenEBS provisioning block

    end

  # Kubernetes Worker Nodes
  (1..WORKER_NODES_COUNT).each do |i|
    config.vm.synced_folder "src/", "/srv/join"
    config.vm.define "worker#{i}" do |node|
      node.trigger.after :up do |wScripts|
        wScripts.run_remote = {inline: "sudo /opt/bootstrap.sh -v && sudo /opt/bootstrap_worker.sh -v"}
      end
      node.vm.box               = VAGRANT_BOX
      node.vm.box_check_update  = false
      node.vm.box_version       = VAGRANT_BOX_VERSION
      node.vm.hostname          = "worker#{i}.example.com"

      node.vm.network "private_network", ip: "172.16.16.10#{i}"

      node.vm.provider :virtualbox do |v|
        v.name    = "worker#{i}"
        v.memory  = MEMORY_WORKER_NODE
        v.cpus    = CPUS_WORKER_NODE
      end

      node.vm.provider :libvirt do |v|
        v.memory  = MEMORY_WORKER_NODE
        v.nested  = true
        v.cpus    = CPUS_WORKER_NODE
      end

      node.vm.cloud_init do |cloud_initw|
        cloud_initw.content_type = "text/cloud-config"
        cloud_initw.path = "worker.yaml"
      end
     
    end
  end

end
