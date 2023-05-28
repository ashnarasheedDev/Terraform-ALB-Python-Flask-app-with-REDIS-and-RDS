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


## create redis server

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

## create sg for rds

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

## create rds
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
}
