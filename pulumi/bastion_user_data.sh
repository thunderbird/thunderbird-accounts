#!/bin/bash

#
# Cloud-init script for SshableInstance (bastion) instances.
#
# Our bastions run AL2023's "minimal" AMI variant, which does not ship with amazon-ssm-agent
# preinstalled like the standard AL2023 AMI does. Without this, the instance can't be reached
# via AWS Systems Manager Session Manager, only direct SSH.
#
# Install command per AWS docs:
# https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-al2.html
#

set -eux

dnf install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
