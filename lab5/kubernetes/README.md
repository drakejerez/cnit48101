# Vagrant Kubernetes Cluster

## Getting Started
To get started:

### Clone the repository
```shell
git clone https://github.com/purduecyan/vagrant.git
```

### Create the VMs
Navigate to the desired folder to create the necessary VMs. For example:
```shell
cd vagrant/kubernetes
```
Allow the network `172.16.16.0/24` for your VirtualBox machines
```shell
sudo mkdir /etc/vbox
sudo echo "* 172.16.16.0/24" >> /etc/vbox/networks.conf
```

Create a shared folder to save the `joincluster.sh` file.
```shell
mkdir src
```


Bring up the VMs using
```shell
vagrant up
```
Once the VMs are created, you can login to a VM using `vagrant ssh`. 
For example, after creating the kubernetes cluster, you can login to the master node using
```shell
vagrant ssh master
```
You can also stop all running VMs withing a project using 
```shell
vagrant halt
```

### Teardown
To delete all the VMs created, run
```shell
vagrant destroy
```

## Additional resources
You can find more information about Vagrant at https://www.vagrantup.com.
