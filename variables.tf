variable "ami_id" {
  default = "ami-0607784b46cbe5816"
}

variable "project_name" {
  default = "python_app"
}

variable "instance_type" {
  default = "t2.micro"
}

variable "vpc_cidr" {
  default = "10.1.0.0/16"
  type    = string
}
