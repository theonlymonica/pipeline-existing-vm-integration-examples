#!/usr/bin/env python3
import os

import aws_cdk as cdk

from awscdk_codepipeline.awscdk_codepipeline_stack import AwscdkCodepipelineStack


app = cdk.App()
AwscdkCodepipelineStack(app, "AwscdkCodepipelineStack")

app.synth()
