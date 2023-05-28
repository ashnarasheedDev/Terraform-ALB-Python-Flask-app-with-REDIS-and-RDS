##Create a security group for load balancer

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

# Create the Auto Scaling Group for outdated instances
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

# Create the Auto Scaling Group for updated instances
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
