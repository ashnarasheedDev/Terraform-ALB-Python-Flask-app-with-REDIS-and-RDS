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
