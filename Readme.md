# Project
Amazon Cost Analysis

# Description
This lambda function fetches cost for specific services from cost explorer service and then it generates a bar graph for last two months with services vise stacked chart. 

# AWS seevices Used
- AWS Lambda
- AWS Cost Explorer
- AWS Simple Email Service
- AWS Eventbridge Services

# Steps for development
- Develop python project
- Create virtual environment, install dependencies, download and zip the dependencies and create lambda layer
- Create Lambda function with custom role (AmazonBasicLambdaExecution, AmazonCeFullAccess, AmazonSesFullAccess)
- Create and verify the identity
- Set up Eventbridge scheduler and set it as trigger to lambda function