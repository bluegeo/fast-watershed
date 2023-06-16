# Fast Watershed infrastructure

Deploy an API for Fast Watershed with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Useful commands

- `npm run build` compile typescript to js
- `npm run watch` watch for changes and compile
- `npm run test` perform the jest unit tests
- `cdk deploy` deploy this stack to your default AWS account/region
- `cdk diff` compare deployed stack with current state
- `cdk synth` emits the synthesized CloudFormation template

## Deploy the API

2. Set the app name environment variable

```bash
export APP_NAME='your-app-name'
```

1. Set the required dataset constants in `deploy/aws/fast-watershed-api/resources/delineate-template.py`
and save as `delineate.py`. Paths should be Cloud Optimized Geotiffs in a http-accessible location,
and be prepended with `/vsicurl/` so GDAL can open them.

2. Build the package code from the root of the `fast-watershed` repository

```bash
docker build -t fastws -f deploy/aws/fast-watershed-api/resources/Dockerfile .
docker run --name fastws fastws /bin/true
docker cp fastws:/var/task/package.zip deploy/aws/fast-watershed-api/resources/package.zip
docker rm fastws
```

3. Deploy the infrastructure

```bash
cd deploy/aws/fast-watershed-api
cdk deploy
```

4. Destroy the infrastructure when not needed

```bash
cd deploy/aws/fast-watershed-api
cdk destory
```
