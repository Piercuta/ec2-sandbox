from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct


class Ec2SandboxStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Recherche du VPC existant
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id=vpc_id)

        # Récupération d'un subnet public
        subnet = vpc.public_subnets[0]  # simplification : on en prend un seul

        # Création d'un Security Group
        sg = ec2.SecurityGroup(
            self, "SandboxSG",
            vpc=vpc,
            description="Security group pour EC2 de test",
            allow_all_outbound=True
        )
        # Ouverture du port SSH uniquement depuis l'IP de l'utilisateur
        sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),  # à remplacer par ec2.Peer.ipv4("xx.xx.xx.xx/32") pour limiter à ton IP
            ec2.Port.tcp(22),
            "Autoriser SSH"
        )

        # IAM role pour EC2 (avec accès SSM et CloudWatch par défaut)
        role = iam.Role(
            self, "SandboxInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"))

        # Instance Profile pour EC2
        # probalbly useless...
        # instance_profile = iam.CfnInstanceProfile(
        #     self, "SandboxInstanceProfile",
        #     roles=[role.role_name]
        # )

        # AMI Ubuntu 22.04 (dans la région actuelle)
        ami = ec2.MachineImage.lookup(
            name="ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*",
            owners=["099720109477"]  # Canonical's AWS account ID
        )

        # EC2 Instance
        instance = ec2.Instance(
            self, "SandboxInstance",
            instance_type=ec2.InstanceType("m5.large"),
            machine_image=ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
            security_group=sg,
            role=role,
            key_name=None,  # Aucune clé SSH, on utilise SSM
        )

        # Associer manuellement l'instance profile à l'instance via l'override
        # instance.node.default_child.add_property_override("IamInstanceProfile", instance_profile.ref)

        # Script User Data optionnel (ex : installer curl, jq, mysql-client)
        instance.add_user_data(
            "#!/bin/bash -xe",
            "apt update -y",
            # Installation de l'agent SSM
            "snap install amazon-ssm-agent --classic",
            "systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service",
            "systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service",
            # Outils de base
            "apt install -y curl jq wget unzip git",
            # Clients de base de données
            "apt install -y mysql-client postgresql-client redis-tools",
            # Outils de monitoring et debugging
            "apt install -y htop iotop iftop net-tools dnsutils",
            "apt install -y telnet netcat-openbsd",
            # Outils de développement
            "apt install -y python3-pip python3-venv",
            "pip3 install awscli",
            # Installation de hey (outil de test de charge)
            "curl -L https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64 -o /usr/local/bin/hey",
            "chmod +x /usr/local/bin/hey",
            # Outils de monitoring des services
            "apt install -y sysstat procps",
            # Outils de sécurité
            "apt install -y openssh-client",
            # Nettoyage
            "apt clean",
            "apt autoremove -y",
            # Vérification du statut de l'agent SSM
            "systemctl status snap.amazon-ssm-agent.amazon-ssm-agent.service",
            # Télécharge rampup.sh
            "aws s3 cp s3://piercuta-dev-stats/rampup_test.sh /tmp/rampup_test.sh",
            "aws s3 cp s3://piercuta-dev-stats/cmd_utils.txt /tmp/cmd_utils.txt",
            "chmod +x /tmp/rampup_test.sh",
        )

        self.instance = instance
