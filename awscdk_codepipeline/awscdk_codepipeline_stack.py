from aws_cdk import (
    Duration,
    Stack,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_stepfunctions as _aws_stepfunctions,
    aws_stepfunctions_tasks as _aws_stepfunctions_tasks
)
from constructs import Construct
import yaml

class AwscdkCodepipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # CodeCommit Repo
        
        repo = codecommit.Repository(self, "pipe-sfn-ec2Repo",
            repository_name="pipe-sfn-ec2-repo"
        )
        
        # SSM Document
        
        with open("ssm/windows.yml") as openFile:
            documentContent = yaml.load(openFile, Loader=yaml.FullLoader)
            cfn_document = ssm.CfnDocument(self, "MyCfnDocument",
                content=documentContent,
                document_format="YAML",
                document_type="Command",
                name="pipe-sfn-ec2Win2S3",
                target_type="/AWS::EC2::Instance"
            )
        
        # Lambda Handlers Definitions
        
        output_bucket = s3.Bucket(self, 'ExecutionOutputBucket')

        submit_lambda = _lambda.Function(self, 'submitLambda',
                                         handler='lambda_function.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambdas/submit'),
                                         environment={
                                             "OUTPUT_BUCKET": output_bucket.bucket_name,
                                             "SSM_DOCUMENT": cfn_document.name
                                             })

        status_lambda = _lambda.Function(self, 'statusLambda',
                                         handler='lambda_function.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambdas/status'))

        ec2_arn = Stack.of(self).format_arn(
            service="ec2",
            resource="instance",
            resource_name="*"
        )
        
        cfn_document_arn = Stack.of(self).format_arn(
            service="ssm",
            resource="document",
            resource_name=cfn_document.name
        )
        
        ssm_arn = Stack.of(self).format_arn(
            service="ssm",
            resource="*"
        )
            
        submit_lambda.add_to_role_policy(iam.PolicyStatement(
            resources=[cfn_document_arn, ec2_arn],
            actions=["ssm:SendCommand"]
        ))
        
        status_lambda.add_to_role_policy(iam.PolicyStatement(
            resources=[ssm_arn],
            actions=["ssm:GetCommandInvocation"]
        ))
        
        # Step functions Definition

        submit_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Submit Job",
            lambda_function=submit_lambda
        )

        wait_job = _aws_stepfunctions.Wait(
            self, "Wait 3 Seconds",
            time=_aws_stepfunctions.WaitTime.duration(
                Duration.seconds(3))
        )

        status_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Get Status",
            lambda_function=status_lambda
        )

        fail_job = _aws_stepfunctions.Fail(
            self, "Fail",
            cause='AWS SSM Job Failed',
            error='Statud Job returned FAILED'
        )

        succeed_job = _aws_stepfunctions.Succeed(
            self, "Succeeded",
            comment='AWS SSM Job succeeded'
        )

        definition = submit_job.next(wait_job)\
            .next(status_job)\
            .next(_aws_stepfunctions.Choice(self, 'Job Complete?')
                  .when(_aws_stepfunctions.Condition.string_equals('$.Payload.status', 'FAILED'), fail_job)
                  .when(_aws_stepfunctions.Condition.string_equals('$.Payload.status', 'SUCCEEDED'), succeed_job)
                  .otherwise(wait_job))

        sfn = _aws_stepfunctions.StateMachine(
            self, "StateMachine",
            definition=definition,
            timeout=Duration.minutes(5)
        )
        
        # CodePipeline
        
        pipeline = codepipeline.Pipeline(self, "pipe-sfn-ec2Pipeline",
            pipeline_name="pipe-sfn-ec2Pipeline",
            cross_account_keys=False
        )
        
        source_output = codepipeline.Artifact("SourceArtifact")
        
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit",
            repository=repo,
            branch="main",
            output=source_output
        )
        
        step_function_action = codepipeline_actions.StepFunctionInvokeAction(
            action_name="Invoke",
            state_machine=sfn,
            state_machine_input=codepipeline_actions.StateMachineInput.file_path(source_output.at_path("abc.json"))
        )
        
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )
        
        pipeline.add_stage(
            stage_name="StepFunctions",
            actions=[step_function_action]
        )