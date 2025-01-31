#!/bin/env python3

import pulumi
import tb_pulumi
import tb_pulumi.ec2
import tb_pulumi.fargate
import tb_pulumi.network
import tb_pulumi.secrets


# Set up the project and convenient config access
project = tb_pulumi.ThunderbirdPulumiProject()
resources = project.config.get('resources')

# Build a VPC for private networking
vpc_opts = resources['tb:network:MultiCidrVpc']['vpc']
vpc = tb_pulumi.network.MultiCidrVpc(f'{project.name_prefix}-vpc', project, **vpc_opts)

# Copy select secrets from Pulumi into AWS Secrets Manager
pulumi_sm_opts = resources['tb:secrets:PulumiSecretsManager']['pulumi']
pulumi_sm = tb_pulumi.secrets.PulumiSecretsManager(f'{project.name_prefix}-secrets', project, **pulumi_sm_opts)

# Build a security group allowing access to the load balancer
sg_lb_opts = resources['tb:network:SecurityGroupWithRules']['accounts-lb']
sg_lb = tb_pulumi.network.SecurityGroupWithRules(
    name=f'{project.name_prefix}-lb-sg',
    project=project,
    vpc_id=vpc.resources['vpc'].id,
    opts=pulumi.ResourceOptions(depends_on=[vpc]),
    **sg_lb_opts,
)

# Build a security group allowing access from the load balancer to the container when we know its ID
opts = resources['tb:network:SecurityGroupWithRules']['accounts-container']
opts['rules']['ingress'][0]['source_security_group_id'] = sg_lb.resources['sg'].id
sg_container = tb_pulumi.network.SecurityGroupWithRules(
    name=f'{project.name_prefix}-container-sg',
    project=project,
    vpc_id=vpc.resources['vpc'].id,
    opts=pulumi.ResourceOptions(depends_on=[sg_lb, vpc]),
    **opts,
)

# Build a Fargate cluster to run our containers
fargate_opts = resources['tb:fargate:FargateClusterWithLogging']['accounts']
fargate = tb_pulumi.fargate.FargateClusterWithLogging(
    name=f'{project.name_prefix}-fargate',
    project=project,
    subnets=vpc.resources['subnets'],
    container_security_groups=[sg_container.resources['sg'].id],
    load_balancer_security_groups=[sg_lb.resources['sg'].id],
    opts=pulumi.ResourceOptions(depends_on=[sg_lb, sg_container, vpc]),
    **fargate_opts,
)

# For testing purposes only, build an SSH-accessible server on the same network space
# jumphost_opts = resources['tb:ec2:SshableInstance']['jumphost']
# jumphost = tb_pulumi.ec2.SshableInstance(
#     name=f'{project.name_prefix}-jumphost',
#     project=project,
#     subnet_id=vpc.resources['subnets'][0],
#     vpc_id=vpc.resources['vpc'].id,
#     opts=pulumi.ResourceOptions(depends_on=[vpc]),
#     **jumphost_opts,
# )
