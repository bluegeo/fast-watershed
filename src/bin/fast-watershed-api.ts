#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FastWatershedApiStack, FastWatershedApiStackProps } from '../lib/fast-watershed-api-stack';

const props: FastWatershedApiStackProps = {
  appName: "abws",
  streamsPath: "https://ab-watersheds.s3.us-west-2.amazonaws.com/v1/geo-logic_streams_{}.tif",
  directionPath: "https://ab-watersheds.s3.us-west-2.amazonaws.com/v1/geo-logic_fd_{}.tif",
  accumulationPath: "https://ab-watersheds.s3.us-west-2.amazonaws.com/v1/geo-logic_fa_streams_{}.tif",
  resolutions: "[15, 25, 50, 100, 200]",
  areaThresh: "[180000000, 500000000, 2000000000, 8000000000]"
}

const app = new cdk.App();
new FastWatershedApiStack(app, `${props.appName}-FastWatershedApiStack`, props);

app.synth();