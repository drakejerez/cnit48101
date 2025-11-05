#!/bin/bash
echo "My name is client!"
#echo "here is my ip: "
#echo $(ip addr show)
mkdir /mnt/share
chmod 777 /mnt/share
sudo mount -v -t nfs 192.168.56.10:/mnt/share /mnt/share
cat /mnt/share/first.txt
touch /mnt/share/second.txt
echo "Hi Server! My name is Client!" >> /mnt/share/second.txt
cat /mnt/share/second.txt
