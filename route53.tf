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
