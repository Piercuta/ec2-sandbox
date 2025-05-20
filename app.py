#!/usr/bin/env python3
import os
from dotenv import load_dotenv

import aws_cdk as cdk
from ec2_sandbox.ec2_sandbox_stack import Ec2SandboxStack

# Charger le .env
load_dotenv()

app = cdk.App()

# Lire la variable d'environnement
vpc_id = os.getenv("VPC_ID")
if not vpc_id:
    raise ValueError("VPC_ID est manquant dans le fichier .env")

# Passer la valeur à la stack via des paramètres (ou context si tu préfères)
Ec2SandboxStack(
    app, "Ec2SandboxStack",
    stack_name="ec2-sandbox-stack",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")),
    vpc_id=vpc_id
)

app.synth()
