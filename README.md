# Terraform-ALB-Python-Flask-app-with-REDIS-and-RDS
Application Load Balancer (ALB) and Auto Scaling Groups (ASG) together can be highly beneficial for managing high-traffic Python Flask applications with outdated and updated versions in two target groups, along with Redis server for session management and Amazon RDS for the database host.

**Here are some advantages of this setup:**

- **Load Balancing:** ALB distributes incoming traffic evenly across multiple instances within an ASG, ensuring that the load is balanced and no single instance is overwhelmed. This helps handle high traffic loads efficiently by automatically scaling resources as needed.

- **High Availability:** By utilizing ASG, you can ensure that your Python Flask application remains highly available even if individual instances fail. ASG automatically replaces failed instances and maintains the desired capacity to handle traffic. Combined with ALB, requests are intelligently routed to healthy instances, minimizing downtime.

- **Rolling Deployments:** With ALB and target groups, you can configure traffic routing to different versions of your Flask application. By launching instances with updated versions alongside instances running the outdated version, you can gradually phase out the outdated version and seamlessly deploy the updated version. This minimizes disruptions to the entire application.

- **Session Management with Redis:** Using Redis server for session management is a recommended approach for Python Flask applications. Redis is an in-memory data store that provides fast read and write operations. By integrating Redis with your application, you can efficiently handle session management, ensuring scalability and reliability across multiple instances.

- **Database Hosting with Amazon RDS:** Leveraging Amazon RDS for your database hosting provides scalability, high availability, and managed database services. You can choose a suitable database engine (e.g., MySQL, PostgreSQL) supported by Amazon RDS for your Python Flask application. Amazon RDS takes care of backups, patching, and automatic scaling, allowing you to focus on application development.

- **Amazon Route 53 private zones:** Create DNS names for the private IPs of your Redis and RDS instances and applying them in your configuration file  of applcation is a good practice. It offers several benefits.By leveraging Route 53 private zones, you can automate the process of updating the IP addresses of your DB and Redis hosts. When Terraform destroys and applies the infrastructure, it can update the DNS records in the private zone, allowing your Python application to fetch the new IP addresses automatically. This ensures that your application can adapt to changes without manual intervention.


**The following diagram illustrates the basic components.**

![alt text](https://i.ibb.co/rQG8FBc/Whats-App-Image-2023-05-20-at-9-22-23-PM-1.jpg)

**Use the following command to install Terraform**
```sh
wget https://releases.hashicorp.com/terraform/0.15.3/terraform_0.15.3_linux_amd64.zip
unzip terraform_0.15.3_linux_amd64.zip 
ls -l
-rwxr-xr-x 1 root root 79991413 May  6 18:03 terraform  <<=======
-rw-r--r-- 1 root root 32743141 May  6 18:50 terraform_0.15.3_linux_amd64.zip
mv terraform /usr/bin/
which terraform 
/usr/bin/terraform
```
**Let's get started:**

### Step 1 - Create a private VPC

>By deploying your resources within a private VPC, you can isolate them from the public internet and establish stricter control over network access. This helps protect your applications and data from unauthorized access and potential security threats.

<b>Create provider.tf</b>
```
provider "aws" {
  access_key = "<your-access-key>"
  secret_key = "<your-secret-key>"
  region     = "ap-south-1"
}

```
<b>Create datasources.tf to fetch number of AZ and public hosted zone</b>
```
data "aws_availability_zones" "azs" {
  state = "available"
}

data "aws_route53_zone" "myzone" {
  name         = "ashna.online"
  private_zone = false
}
```
<b>Create variables.tf</b>
```
variable "ami_id" {
  default = "ami-0607784b46cbe5816"
}

variable "project_name" {
  default = "blog_app"
}

variable "instance_type" {
  default = "t2.micro"
}

variable "vpc_cidr" {
  default = "10.1.0.0/16"
  type    = string
}
```
<b>Create vpc.tf for setup the private vpc and it's assosiates</b>
```
#creating VPC

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  instance_tenancy     = "default"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "${var.project_name}"
  }
}

#creating igw

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}"
  }
}

#creating public subnets

resource "aws_subnet" "publicsubnets" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 3, count.index)
  availability_zone       = data.aws_availability_zones.azs.names["${count.index}"]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public${count.index + 1}"
  }

}



#creating private subnets
resource "aws_subnet" "privatesubnets" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 3, "${count.index + 2}")
  availability_zone       = data.aws_availability_zones.azs.names["${count.index}"]
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-private${count.index + 1}"
  }

}


#creating public route table

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }


  tags = {
    Name = "${var.project_name}-public"
  }
}



#public route table assosiation

resource "aws_route_table_association" "publics" {
  count          = 2
  subnet_id      = aws_subnet.publicsubnets["${count.index}"].id
  route_table_id = aws_route_table.public.id
}


#creating private routetable

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }


  tags = {
    Name = "${var.project_name}-private"
  }
}


#private route table assosiation

resource "aws_route_table_association" "privates" {
  count          = 2
  subnet_id      = aws_subnet.privatesubnets["${count.index}"].id
  route_table_id = aws_route_table.private.id
}

#eip for nat gw

resource "aws_eip" "nat" {
  vpc = true
  tags = {
    Name = "${var.project_name}-nat"
  }

}


#creating nat gateway

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.publicsubnets[0].id

  tags = {
    Name = "${var.project_name}"
  }
  depends_on = [aws_internet_gateway.igw]
}
```
### Step 2 - Setting up REDIS & RDS Resources

> Below code is for creating security groups and resources for a Redis server and an RDS (Relational Database Service) instance. It sets up the necessary security group rules and configurations for allowing access to the Redis and RDS services. Here's a breakdown of the code:

  1. Redis Security Group:
        Creates an AWS security group named "redis" with ingress rules allowing TCP traffic on port 6379 from all IP addresses (0.0.0.0/0 and ::/0).
        Specifies egress rules that allow all traffic (from port 0 to port 0) to all IP addresses.
        Tags the security group with a name based on the project_name variable.

  2. Redis Instance:
        Creates an AWS EC2 instance for the Redis server using the specified AMI, instance type, key name, and user data (the redis.sh script).
        Associates the Redis security group with the instance.
        Places the instance in the specified subnet.
        Tags the instance with a name based on the project_name variable.

   3. RDS Security Group:
        Creates an AWS security group named "rds" with an ingress rule allowing TCP traffic on port 3306 from all IP addresses (0.0.0.0/0 and ::/0).
        Specifies egress rules that allow all traffic (from port 0 to port 0) to all IP addresses.
        Tags the security group with a name based on the project_name variable.

   4. RDS Subnet Group:
        Creates an AWS RDS subnet group named "rds_subnet" and associates it with the specified private subnets.

   5. RDS Instance:
        Creates an AWS RDS instance with the specified engine, storage, version, instance class, credentials, subnet group, security group, and other configurations.
        
```
## create sg for redis server

resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-"
  description = "Allow access to port"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port        = 6379
    to_port          = 6379
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }


  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "${var.project_name}"

  }
}


# create redis server

resource "aws_instance" "redis" {

  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = "mumbai-region"
  vpc_security_group_ids = [aws_security_group.redis.id]
  user_data              = file("redis.sh")
  subnet_id              = aws_subnet.privatesubnets[0].id
  tags = {
    Name = "${var.project_name}-redis"
  }
}

# create sg for rds

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port        = 3306
    to_port          = 3306
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]

    # security_groups = [aws_security_group.frontend.id]
  }


  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "${var.project_name}-rds"

  }
}

# create subnet group & rds

resource "aws_db_subnet_group" "subnet_rds" {
  name = "rds_subnet"
  subnet_ids = [
    aws_subnet.privatesubnets[0].id,
    aws_subnet.privatesubnets[1].id
  ]
}

resource "aws_db_instance" "rds" {
  engine                 = "mysql"
  identifier             = "myrdsinstance"
  allocated_storage      = 20
  engine_version         = "5.7"
  instance_class         = "db.t2.micro"
  username               = "myrdsuser"
  password               = "myrdspassword"
  parameter_group_name   = "default.mysql5.7"
  db_subnet_group_name   = aws_db_subnet_group.subnet_rds.name
  vpc_security_group_ids = ["${aws_security_group.rds.id}"]
  skip_final_snapshot    = true
  publicly_accessible    = true
```
><b>Userdata for redis server redis.sh</b>

```
#/bin/bash

sudo hostnamectl set-hostname blogapp-redis.server
sudo yum install docker -y
sudo systemctl restart docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
sudo docker container run --name redis -d -p 6379:6379 --restart always redis:latest
```
### Step 3 - Create ALB,ASG and it's assosiated resources

 I created AMI of my application server for the launch configuration in the Terraform code. My application runs on 8080 port with REDIS for session management and RDS for DB Host. I have an updated and outdated version of my application which I planed to configure using two target group. I named it as blog and wiki. Let's see the detailed setup.
 
  -  ALB Security Group for ALB & TG:
        Creates an AWS security group named "alb" with ingress rules allowing TCP traffic on ports 80 and 8080 from all IP addresses (0.0.0.0/0 and ::/0).
        Specifies egress rules that allow all traffic (from port 0 to port 0) to all IP addresses.
        Tags the security group with a name based on the project_name variable.
        Includes a lifecycle block with the create_before_destroy set to true, ensuring that the security group is created before any existing one is destroyed.

 -  Target Groups:
        Creates two AWS target groups, "blog" and "wiki," with the specified port, protocol, VPC ID, and health check configurations.
        Each target group includes a lifecycle block with create_before_destroy set to true.

 - ALB:
        Creates an AWS Application Load Balancer (ALB) with the specified name, internal/external accessibility, load balancer type, security groups, subnets, and deletion protection.
        Tags the ALB with a name based on the project_name variable.
        Includes an output block that exposes the DNS name of the ALB.

 -  ALB Listener:
        Creates an ALB listener for HTTP traffic on port 80 with a default fixed response when no matching rule is found.
        Depends on the ALB resource being created before the listener.

 -  ALB Listener Rules:
        Creates two ALB listener rules, one for the "wiki" target group and one for the "blog" target group.
        The rules are based on the host header values and forward traffic to the respective target groups.
        Each rule includes a condition block specifying the host header values.

 -  Launch Configurations:
        Creates AWS launch configurations for the "blog" and "wiki" instances.
        Specifies the instance image ID, type, key name, and security group (ALB security group).
        Image ID I used is my applicaton sever's AMI.

- Auto Scaling Groups:
        Creates AWS Auto Scaling Groups (ASGs) for the "blog" and "wiki" instances.
        Specifies the minimum, maximum, and desired capacity, launch configuration, subnet IDs, target group ARNs, health check type, and grace period.
        Tags the ASGs with names and sets the propagate_at_launch attribute to true.
        
```
#Create a security group for load balancer

resource "aws_security_group" "alb" {
  name   = "sg_alb_blog"
  vpc_id = aws_vpc.main.id

  ingress {
    description      = "HTTPS"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]

  }

  ingress {
    description      = "HTTPS"
    from_port        = 8080
    to_port          = 8080
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]

  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "${var.project_name}"
  }
  lifecycle {
    create_before_destroy = true
  }
}

## create target group blog

resource "aws_lb_target_group" "blog" {
  name     = "blog-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id


  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    enabled             = true
    protocol            = "HTTP"
    path                = "/"
    matcher             = "200"

  }
  lifecycle {
    create_before_destroy = true
  }

}

## create target group wiki

resource "aws_lb_target_group" "wiki" {
  name     = "wiki-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id


  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    enabled             = true
    protocol            = "HTTP"
    path                = "/"
    matcher             = "200"



  }
  lifecycle {
    create_before_destroy = true
  }

}

# Create an ALB

resource "aws_lb" "alb" {
  name                       = "blog-app-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = [aws_subnet.publicsubnets[0].id, aws_subnet.publicsubnets[1].id]
  enable_deletion_protection = false
  tags = {
    Name = "${var.project_name}-alb"
  }
}

output "alb-endpoint" {
  value = aws_lb.alb.dns_name
}


# Create Listener for ALB

resource "aws_lb_listener" "listener_http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"



  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = " No such Site Found"
      status_code  = "200"
    }

  }
  depends_on = [aws_lb.alb]

}

# Create Listener rules for ALB

resource "aws_lb_listener_rule" "wiki" {
  listener_arn = aws_lb_listener.listener_http.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.wiki.arn
  }

  condition {
    host_header {
      values = ["wiki.ashna.online"]
    }
  }
}


resource "aws_lb_listener_rule" "blog" {
  listener_arn = aws_lb_listener.listener_http.arn
  priority     = 2

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blog.arn
  }

  condition {
    host_header {
      values = ["blog.ashna.online"]
    }
  }
}


# Create the launch configuration for blog instances

resource "aws_launch_configuration" "blog_lc" {
  name            = "launch-config-blog"
  image_id        = "ami-06a68dc98621ff494" # Replace with your AMI ID for blog instances
  instance_type   = "t2.micro"              # Replace with your desired instance type
  key_name        = "mumbai-region"
  security_groups = [aws_security_group.alb.id] # Replace with your security group IDs
}

# Create the launch configuration for wiki instances

resource "aws_launch_configuration" "wiki_lc" {
  name            = "launch-config-wiki"
  image_id        = "ami-06a68dc98621ff494" # Replace with your AMI ID for wiki instances
  instance_type   = "t2.micro"              # Replace with your desired instance type
  key_name        = "mumbai-region"
  security_groups = [aws_security_group.alb.id] # Replace with your security group IDs
}

# Create the Auto Scaling Group for blog instances

resource "aws_autoscaling_group" "asg_blog" {
  name                      = "asg-blog"
  min_size                  = 2
  max_size                  = 2
  desired_capacity          = 2
  launch_configuration      = aws_launch_configuration.blog_lc.name
  vpc_zone_identifier       = [aws_subnet.publicsubnets[0].id, aws_subnet.publicsubnets[1].id] # Replace with your subnet IDs
  target_group_arns         = [aws_lb_target_group.blog.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 300

  tag {
    key                 = "Name"
    value               = "blog-asg"
    propagate_at_launch = true
  }

}

# Create the Auto Scaling Group for wiki instances

resource "aws_autoscaling_group" "asg_wiki" {
  name                      = "asg-wiki"
  min_size                  = 2
  max_size                  = 2
  desired_capacity          = 2
  launch_configuration      = aws_launch_configuration.wiki_lc.name
  vpc_zone_identifier       = [aws_subnet.publicsubnets[0].id, aws_subnet.publicsubnets[1].id] # Replace with your subnet IDs
  target_group_arns         = [aws_lb_target_group.wiki.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 300
  tag {
    key                 = "Name"
    value               = "wiki-asg"
    propagate_at_launch = true
  }

}
```
### Step 4 - Configuring Route53 records

> Here, I have set up a private hosted zone to configure private IP addresses for your Redis and RDS instances with a private domain name is a good practice.

> Create CNAME records for wiki.ashna.online and blog.ashna.online that point to load balancer's DNS name. By setting up these CNAME records, incoming requests to wiki.ashna.online and blog.ashna.online will be directed to load balancer.

> In our code, we have defined listener rules for load balancer. The listener rule for wiki.ashna.online specifies the target group aws_lb_target_group.wiki for forwarding the traffic. Similarly, the listener rule for blog.ashna.online specifies the target group aws_lb_target_group.blog for forwarding the traffic.

> Therefore, requests coming to wiki.ashna.online will be forwarded to the target group aws_lb_target_group.wiki, and requests coming to blog.ashna.online will be forwarded to the target group aws_lb_target_group.blog.

This setup allows to route traffic based on the host header, enabling us to direct requests to the appropriate target group based on the subdomain.

```
resource "aws_route53_zone" "private" {
  name = "ashna.local"

  vpc {
    vpc_id = aws_vpc.main.id
  }
}

resource "aws_route53_record" "wiki" {
  zone_id = data.aws_route53_zone.myzone.id
  name    = "wiki"
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.alb.dns_name]
}

resource "aws_route53_record" "blog" {
  zone_id = data.aws_route53_zone.myzone.id
  name    = "blog"
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.alb.dns_name]
}
resource "aws_route53_record" "redis" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "redis"
  type    = "A"
  ttl     = 300
  records = [aws_instance.redis.private_ip]
}

resource "aws_route53_record" "rds" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "rds"
  type    = "CNAME"
  ttl     = 300
  records = [aws_db_instance.rds.address]
}
```

Overall, the project demonstrates a well-structured architecture for managing high traffic applications using ALB, ASGs, and other AWS services. It provides scalability, traffic routing, and simplification of resource access through the use of DNS-based configurations.
