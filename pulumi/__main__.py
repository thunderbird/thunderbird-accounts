#!/bin/env python3

import pulumi
import pulumi_cloudflare as cloudflare
import tb_pulumi
import tb_pulumi.ci
import tb_pulumi.ec2
import tb_pulumi.elasticache
import tb_pulumi.fargate
import tb_pulumi.iam
import tb_pulumi.network
import tb_pulumi.secrets


MSG_LB_MATCHING_CONTAINER = 'In this stack, container security groups must have matching load balancer security groups.'
MSG_LB_MATCHING_CLUSTER = 'In this stack, Fargate clusters must have matching load balancer security groups.'
MSG_CONTAINER_MATCHING_CLUSTER = 'In this stack, Fargate clusters must have matching container security groups.'

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

# Build security groups for load balancers
lb_sgs = {
    service: tb_pulumi.network.SecurityGroupWithRules(
        name=f'{project.name_prefix}-sg-lb-{service}',
        project=project,
        vpc_id=vpc.resources['vpc'].id,
        opts=pulumi.ResourceOptions(depends_on=[vpc]),
        **sg,
    )
    if sg
    else None
    for service, sg in resources['tb:network:SecurityGroupWithRules']['load_balancers'].items()
}

# Build security groups for containers
container_sgs = {}
for service, sg in resources['tb:network:SecurityGroupWithRules']['containers'].items():
    if service not in lb_sgs:
        raise ValueError(f'{MSG_LB_MATCHING_CONTAINER} Create a matching load_balancers entry for "{service}".')
    # Allow access from each load balancer to its respective container
    for rule in sg['rules']['ingress']:
        rule['source_security_group_id'] = lb_sgs[service].resources['sg'].id
    depends_on = [lb_sgs[service].resources['sg'], vpc] if lb_sgs[service] else []
    container_sgs[service] = tb_pulumi.network.SecurityGroupWithRules(
        name=f'{project.name_prefix}-sg-cont-{service}',
        project=project,
        vpc_id=vpc.resources['vpc'].id,
        opts=pulumi.ResourceOptions(depends_on=depends_on),
        **sg,
    )

instances = {}
for instance in resources['tb:ec2:SshableInstance'].keys():
    instance_opts = resources['tb:ec2:SshableInstance'][instance]
    instances[instance] = tb_pulumi.ec2.SshableInstance(
        f'{project.name_prefix}-{instance}',
        project=project,
        subnet_id=vpc.resources['subnets'][0].id,
        vpc_id=vpc.resources['vpc'].id,
        opts=pulumi.ResourceOptions(depends_on=[vpc]),
        **instance_opts,
    )

# Build an ElastiCache Redis cluster allowing access from the Accounts containers
redis_opts = resources['tb:elasticache:ElastiCacheReplicaGroup']['accounts']
redis = tb_pulumi.elasticache.ElastiCacheReplicationGroup(
    name=f'{project.name_prefix}-redis',
    project=project,
    source_sgids=[container_sgs['accounts'].resources['sg'].id, container_sgs['accounts-celery'].resources['sg'].id],
    subnets=vpc.resources['subnets'],
    opts=pulumi.ResourceOptions(depends_on=[vpc, container_sgs['accounts']]),
    **redis_opts,
)

# Build Fargate clusters to run our containers
fargate_clusters = {}
for service, opts in resources['tb:fargate:FargateClusterWithLogging'].items():
    if service not in lb_sgs:
        raise ValueError(f'{MSG_LB_MATCHING_CLUSTER} Create a matching load_balancers entry for "{service}".')
    if service not in container_sgs:
        raise ValueError(f'{MSG_CONTAINER_MATCHING_CLUSTER} Create a matching load_balancers entry for "{service}".')
    lb_sg_ids = [lb_sgs[service].resources['sg'].id] if lb_sgs[service] else []
    depends_on = [
        container_sgs[service].resources['sg'],
        *vpc.resources['subnets'],
    ]
    if lb_sgs[service]:
        depends_on.append(lb_sgs[service].resources['sg'])
    fargate_clusters[service] = tb_pulumi.fargate.FargateClusterWithLogging(
        name=f'{project.name_prefix}-fargate-{service}',
        project=project,
        subnets=vpc.resources['subnets'],
        container_security_groups=[container_sgs[service].resources['sg'].id],
        load_balancer_security_groups=lb_sg_ids,
        opts=pulumi.ResourceOptions(depends_on=depends_on),
        **opts,
    )

cloudflare_backend_record = cloudflare.Record(
    f'{project.name_prefix}-dns-backend',
    zone_id=cloudflare_zone_id,
    name=resources['domains']['accounts'],
    type='CNAME',
    content=fargate_clusters['accounts'].resources['fargate_service_alb'].resources['albs']['accounts'].dns_name,
    proxied=False,
    ttl=1,  # ttl units are *minutes*
    opts=pulumi.ResourceOptions(depends_on=[*fargate_clusters.values()]),
)

stack_access_policies = tb_pulumi.iam.StackAccessPolicies(
    name=f'{project.name_prefix}-sap',
    project=project,
    opts=pulumi.ResourceOptions(
        depends_on=[
            vpc,
            pulumi_sm,
            *[sg for sg in lb_sgs.values() if sg is not None],
            *[sg for sg in container_sgs.values() if sg is not None],
            *instances.values(),
            redis,
            *fargate_clusters.values(),
        ]
    ),
)

# This is only managed by a single stack, so a configuration may not exist for it
if 'tb:ci:AwsAutomationUser' in resources and 'ci' in resources['tb:ci:AwsAutomationUser']:
    ci_opts = resources['tb:ci:AwsAutomationUser']['ci']
    ci_iam = tb_pulumi.ci.AwsAutomationUser(name=f'{project.project}-ci', project=project, **ci_opts)
