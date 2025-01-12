import json

import pulumi
import pulumi_aws as aws

# Get some configuration values or set default values.
config = pulumi.Config()
instance_type = config.get("instanceType")

if instance_type is None:
    exit(1)
    
vpc_network_cidr = config.get("vpcNetworkCidr")

if vpc_network_cidr is None:
    exit(1)


# User data to start a HTTP server in the EC2 instance
with open('user_data.sh', 'r') as f:
	user_data = f.read()

# Create VPC.
vpc = aws.ec2.Vpc("vpc",
    cidr_block=vpc_network_cidr,
    enable_dns_hostnames=True,
    enable_dns_support=True)

# Create an internet gateway.
gateway = aws.ec2.InternetGateway("gateway", vpc_id=vpc.id)

# Create a subnet that automatically assigns new instances a public IP address.
subnet = aws.ec2.Subnet("subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True)

# Create a route table.
route_table = aws.ec2.RouteTable("routeTable",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        gateway_id=gateway.id,
    )])

# Associate the route table with the public subnet.
route_table_association = aws.ec2.RouteTableAssociation("routeTableAssociation",
    subnet_id=subnet.id,
    route_table_id=route_table.id)
    
instance_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Sid": "",
            "Principal": {
                "Service": "ec2.amazonaws.com",
            },
        }
    ],
}
    
'''role = aws.iam.Role(
        'custom-ec2-instance-role',
        assume_role_policy = json.dumps(instance_policy),
        path = '/'
)

role_attachment = aws.iam.RolePolicyAttachment(
    'attach_me',
    policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    role = role
)

instance_profile = aws.iam.InstanceProfile(
    'custom-instance-profile',
    role = role
)'''

# Create a security group allowing inbound access over port 80 and outbound
# access to anywhere.
sec_group = aws.ec2.SecurityGroup("secGroup",
    description="Enable HTTP access",
    vpc_id=vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        from_port=80,
        to_port=80,
        protocol="tcp",
        cidr_blocks=["0.0.0.0/0"],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
    )])
    
    

# Look up the latest Amazon Linux 2 AMI.
ami = aws.ec2.get_ami(
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name="name",
            values=["amzn2-ami-hvm-*"],
        )
    ],
    owners=["amazon"],
    most_recent=True).id


# Create and launch an EC2 instance into the public subnet.
server = aws.ec2.Instance("server",
    instance_type=instance_type,
    subnet_id=subnet.id,
    vpc_security_group_ids=[sec_group.id],
    user_data=user_data,
    ami=ami,
    tags={
        "Name": "webserver",
        'aws_nuke': 'yes'
    },
    #iam_instance_profile=instance_profile
)

# Export the instance's publicly accessible IP address and hostname.
pulumi.export("ip", server.public_ip)
pulumi.export("hostname", server.public_dns)
pulumi.export("url", server.public_dns.apply(lambda public_dns: f"http://{public_dns}"))
