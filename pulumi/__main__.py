#!/bin/env python3

import pulumi
import pulumi_cloudflare as cloudflare
import tb_pulumi
import tb_pulumi.ec2
import tb_pulumi.elasticache
import tb_pulumi.fargate
import tb_pulumi.network
import tb_pulumi.secrets

# Set up the project and convenient config access
project = tb_pulumi.ThunderbirdPulumiProject()
resources = project.config.get('resources')
cloudflare_zone_id = project.pulumi_config.require_secret('cloudflare_zone_id')


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
sg_opts = resources['tb:network:SecurityGroupWithRules']['accounts-container']
sg_opts['rules']['ingress'][0]['source_security_group_id'] = sg_lb.resources['sg'].id
sg_container = tb_pulumi.network.SecurityGroupWithRules(
    name=f'{project.name_prefix}-container-sg',
    project=project,
    vpc_id=vpc.resources['vpc'].id,
    opts=pulumi.ResourceOptions(depends_on=[sg_lb, vpc]),
    **sg_opts,
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

# Build an ElastiCache Redis cluster
redis_opts = resources['tb:elasticache:ElastiCacheReplicaGroup']['accounts']
redis = tb_pulumi.elasticache.ElastiCacheReplicationGroup(
    name=f'{project.name_prefix}-redis',
    project=project,
    source_sgids=[sg_container.resources['sg'].id],
    # Swap above line with below if you build a jumphost
    # source_sgids=[sg_container.resources['sg'].id, jumphost.resources['security_group'].resources['sg'].id],
    subnets=vpc.resources['subnets'],
    opts=pulumi.ResourceOptions(depends_on=[vpc, sg_container]),
    # Swap above line with below if you build a jumphost
    #opts=pulumi.ResourceOptions(depends_on=[jumphost, vpc, sg_container]),
    **redis_opts,
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

cloudflare_backend_record = cloudflare.Record(
    f'{project.name_prefix}-dns-backend',
    zone_id=cloudflare_zone_id,
    name=resources['domains']['accounts'],
    type='CNAME',
    content=fargate.resources['fargate_service_alb'].resources['albs']['accounts'].dns_name,
    proxied=False,
    ttl=1,  # ttl units are *minutes*
    opts=pulumi.ResourceOptions(depends_on=[fargate])
)
