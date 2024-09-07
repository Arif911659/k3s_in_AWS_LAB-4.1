""" AWS Python Pulumi Program """

import pulumi
import pulumi_aws as aws
import pulumi_aws.ec2 as ec2
from pulumi_aws.ec2 import SecurityGroupRuleArgs
import os

# Configuration
config = pulumi.Config()
instance_type = 't2.micro' 
ami = "ami-0497a974f8d5dcef8"
vpc_cidr_block = "10.0.0.0/16"
public_subnet_cidr_block = "10.0.1.0/24"
private_subnet_cidr_block = "10.0.2.0/24"
availability_zone = "ap-southeast-1a"

# Create a VPC
vpc = ec2.Vpc("my-vpc",
    cidr_block=vpc_cidr_block,
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={
        "Name": "my-vpc"
    }
)

# Create a Public Subnet
public_subnet = ec2.Subnet("public-subnet",
    vpc_id=vpc.id,
    cidr_block=public_subnet_cidr_block,
    map_public_ip_on_launch=True,
    availability_zone=availability_zone,
    tags={
        "Name": "public-subnet",
    }
)

# Create a Private Subnet
private_subnet = ec2.Subnet("private-subnet",
    vpc_id=vpc.id,
    cidr_block=private_subnet_cidr_block,
    map_public_ip_on_launch=False,
    availability_zone=availability_zone,
    tags={
        "Name": "private-subnet",
    }
)

# Create an Internet Gateway
igw = ec2.InternetGateway("internet-gateway",
    vpc_id=vpc.id,
    tags={
        "Name": "my-igw"
    }
)

# Create a Route Table for the Public Subnet
public_route_table = ec2.RouteTable("public-route-table",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0", 
        "gateway_id": igw.id,
    }],
    tags={
        "Name": "public-route-table"
    }
)

# Associate the Route Table with the Public Subnet
public_route_table_association = ec2.RouteTableAssociation("public-route-table-association",
    subnet_id=public_subnet.id,
    route_table_id=public_route_table.id
)

# Create an Elastic IP for the NAT Gateway
eip = ec2.Eip("nat-eip", vpc=True)

# Create a NAT Gateway in the Public Subnet
nat_gateway = ec2.NatGateway("nat-gateway",
    subnet_id=public_subnet.id,
    allocation_id=eip.id,
    tags={
        "Name": "my-nat-gateway"
    }
)

# Create a Route Table for the Private Subnet
private_route_table = ec2.RouteTable("private-route-table",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0", 
        "nat_gateway_id": nat_gateway.id,
    }],
    tags={
        "Name": "private-route-table"
    }
)

# Associate the Route Table with the Private Subnet
private_route_table_association = ec2.RouteTableAssociation("private-route-table-association",
    subnet_id=private_subnet.id,
    route_table_id=private_route_table.id
)
# Create Security Group
security_group = aws.ec2.SecurityGroup("k3s-secgrp",
    description='Enable SSH and K3s access',
    vpc_id=vpc.id,
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 22,
            "to_port": 22,
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "protocol": "tcp",
            "from_port": 6443,
            "to_port": 6443,
            "cidr_blocks": ["0.0.0.0/0"],
        },
    ],
    egress=[
        {
        "protocol": "-1",
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"],
        }],
    tags={
        "Name": "k3s-secgrp"
    }
)
# collect the public key from github workspace 
public_key = os.getenv("PUBLIC_KEY")

# Create the EC2 KeyPair using the public key 
key_pair = aws.ec2.KeyPair("my-key-pair",
    key_name="my-key-pair", 
    public_key=public_key
)

#EC2 instances for Git Runner
git_runner_instance = ec2.Instance('git-runner-instance', 
    instance_type=instance_type,
    ami=ami,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[security_group.id],
    key_name=key_pair.key_name,

    tags={
        'Name': 'Git-Runner-Dev',
        }
)

# EC2 instances for Master & Worker
master_instance = ec2.Instance('master-instance',
    instance_type=instance_type,
    ami=ami,
    subnet_id=private_subnet.id,
    vpc_security_group_ids=[security_group.id],
    key_name=key_pair.key_name,
    tags={
        'Name': 'k3s-Master',
        }
)

worker_instance_1 = ec2.Instance('worker-instance-1', 
    instance_type=instance_type,
    ami=ami,
    subnet_id=private_subnet.id,
    vpc_security_group_ids=[security_group.id],
    key_name=key_pair.key_name,
    tags={
        'Name': 'k3s-worker-1',
})

worker_instance_2 = ec2.Instance('worker-instance-2', 
    instance_type=instance_type,
    ami=ami,
    subnet_id=private_subnet.id,
    vpc_security_group_ids=[security_group.id],
    key_name=key_pair.key_name,
    tags={
        'Name': 'k3s-worker-2',
        }
)

# Output the IDs of the created resources
pulumi.export('vpc_id', vpc.id)
pulumi.export('public_subnet_id', public_subnet.id)
pulumi.export('private_subnet_id', private_subnet.id)
pulumi.export('internet_gateway_id', igw.id)
pulumi.export('nat_gateway_id', nat_gateway.id)
#Output the instance IP addresses
pulumi.export('git_runner_public_ip', git_runner_instance.public_ip) 
pulumi.export('master_private_ip', master_instance.private_ip) 
pulumi.export('worker1_private_ip', worker_instance_1.private_ip)
pulumi.export('worker2_private_ip', worker_instance_2.private_ip)

