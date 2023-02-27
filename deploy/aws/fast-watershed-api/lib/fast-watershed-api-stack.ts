import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { PassthroughBehavior } from "aws-cdk-lib/aws-apigateway";

export class FastWatershedApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const delineatorCode = lambda.Code.fromAsset("resources/package.zip");

    const handler = new lambda.Function(this, "Delineator", {
      runtime: lambda.Runtime.PYTHON_3_8,
      description: "Watershed delineator open demo",
      code: delineatorCode,
      handler: "delineate.handler",
      memorySize: 10240,
      timeout: cdk.Duration.seconds(29),
    });

    new apigateway.LambdaRestApi(this, "fast-watershed-api", {
      description: "An interface for watershed delineation demonstration",
      handler: handler,
      cloudWatchRole: true,
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS
      }
    })
  }
}
