import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { DockerImageAsset } from "aws-cdk-lib/aws-ecr-assets";
import { HttpLambdaIntegration } from "@aws-cdk/aws-apigatewayv2-integrations-alpha";
import * as apigwv2 from "@aws-cdk/aws-apigatewayv2-alpha";

export interface FastWatershedApiStackProps extends cdk.StackProps {
  appName: string;
  streamsPath: string;
  directionPath: string;
  accumulationPath: string;
  resolutions: string;
  areaThresh: string;
}

export class FastWatershedApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: FastWatershedApiStackProps) {
    super(scope, id, props);

    const asset = new DockerImageAsset(this, `${props.appName}-dockerimage`, {
      directory: path.join(__dirname, "../resources"),
      platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
    });

    const lambdaFunction = new lambda.Function(this, `${props.appName}-WatershedDelineator`, {
      runtime: lambda.Runtime.FROM_IMAGE,
      memorySize: 10240,
      timeout: cdk.Duration.seconds(29),
      handler: lambda.Handler.FROM_IMAGE,
      code: lambda.Code.fromEcrImage(asset.repository, {
        tagOrDigest: asset.imageTag,
      }),
      logRetention: cdk.aws_logs.RetentionDays.ONE_WEEK,
      environment: {
        STREAMS_PATH: props.streamsPath,
        DIRECTION_PATH: props.directionPath,
        ACCUMULATION_PATH: props.accumulationPath,
        RESOLUTIONS: props.resolutions,
        AREA_THRESH: props.areaThresh,
      }
    });

    const lambdaIntegration = new HttpLambdaIntegration(
      `${props.appName}-integration`,
      lambdaFunction
    );

    const api = new apigwv2.HttpApi(
      this,
      `${props.appName}-api`,
      {
        apiName: `${props.appName} Watershed Delineator`,
        corsPreflight: {
          allowHeaders: ["Authorization", "Content-Type"],
          allowMethods: [apigwv2.CorsHttpMethod.ANY],
          allowOrigins: ["*"],
          maxAge: cdk.Duration.days(10),
        },
      }
    );

    new apigwv2.HttpRoute(
      this,
      `${props.appName}-api-post`,
      {
        httpApi: api,
        integration: lambdaIntegration,
        routeKey: apigwv2.HttpRouteKey.with(
          "/{proxy+}",
          apigwv2.HttpMethod.POST
        ),
      }
    );
  }
}
