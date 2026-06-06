#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.salacious_agent_stack import SalaciousAgentStack

app = cdk.App()
SalaciousAgentStack(
    app,
    "SalaciousAgentStack",
    env=cdk.Environment(account="281897100938", region="us-east-1"),
)
app.synth()
