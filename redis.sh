#/bin/bash

sudo hostnamectl set-hostname blogapp-redis.server
sudo yum install docker -y
sudo systemctl restart docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
sudo docker container run --name redis -d -p 6379:6379 --restart always redis:latest
