# importing all required modules
import os
import sys
import boto3
import xlsxwriter
import json
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Variables
RESULT_FOR_LAST_DAYS = 6
GROUP_BY = [
    {"Type": "DIMENSION", "Key": "SERVICE"}
]
METRICS = [
    'UnblendedCost',
]
FILTER = {
    'Or': [
        {
            "Dimensions": {
                'Key': 'SERVICE',
                'Values': [
                    'Amazon Elastic Compute Cloud - Compute',
                    'AWS Lambda',
                    'EC2 - Other',
                    'Amazon Elastic Container Service for Kubernetes'
                ]
            }
        },
        {
            "Tags": {
                'Key': 'app',
                'Values': ['cost_collection']
            }
        }
    ]
}
GRANULARITY = 'DAILY'
EMAIL_ADDRESS = 'shubhpatel4799@gmail.com'

# Class for fetching daily cost using cost explorer and generating excel


class AwsDailCostAnalysis():

    # constructor for setting up aws services object
    def __init__(self,
                 granularity,
                 group_by,
                 metrics,
                 filter,
                 email
                 ) -> None:
        self.ses = boto3.client('ses', region_name='us-east-1')
        self.ce = boto3.client('ce')
        self.granularity = granularity
        self.group_by = group_by
        self.metrics = metrics
        self.filter = filter
        self.email_address = email

    # function for getting aws daily cost for specific services
    def getCostByServicesAndGenerateChart(self):
        # getting the today and previous day for gettig cost
        end_date, start_date = getDate()
        # getting Aws cost for specific resources
        response = self.ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=self.granularity,
            Metrics=self.metrics,
            GroupBy=self.group_by,
            Filter=self.filter
        )
        # Fetching response data
        dates = []
        services = set()
        costs_by_service = {}
        os.chdir("/tmp")
        # print(response)
        for result in response["ResultsByTime"]:
            start = result['TimePeriod']['Start']
            end = result['TimePeriod']['End']
            dates.append(start)
            groups = result['Groups']

            for group in groups:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                services.add(service)

                if service not in costs_by_service:
                    costs_by_service[service] = []
                costs_by_service[service].append(cost)

        # Create Excel file and worksheet
        workbook = xlsxwriter.Workbook('cost_analysis.xlsx')
        worksheet = workbook.add_worksheet()

        # Write data to worksheet
        row = 0
        col = 0
        worksheet.write(row, col, 'Date')
        for service in services:
            worksheet.write(row, col + 1, service)
            col += 1

        for i, date in enumerate(dates):
            row = i + 1
            col = 0
            worksheet.write(row, col, date)

            for service in services:
                col += 1
                cost = 0
                if i >= len(costs_by_service[service]):
                    cost = 0
                else:
                    cost = costs_by_service[service][i]
                worksheet.write(row, col, cost)

        # Create stack graph
        col = 0
        chart = workbook.add_chart({'type': 'column', 'subtype': 'stacked'})
        for service in services:
            col += 1
            print(col)
            print(service)
            #     [sheetname, first_row, first_col, last_row, last_col]
            chart.add_series({
                'name': service,
                'categories': ['Sheet1', 1, 0, len(dates), 0],
                'values': ['Sheet1', 1, col, len(dates), col]
            })
        chart.set_x_axis({'name': 'Date'})
        chart.set_y_axis({'name': 'Cost'})
        chart.set_title({'name': 'Cost Distribution by Service Over Time'})

        worksheet.insert_chart('E2', chart)

        # Close the workbook
        workbook.close()

    # this function sends the generated email to user
    def send_email(self, filename="cost_analysis.xlsx"):
        msg = MIMEMultipart()
        # Metadata for Email
        msg['From'] = self.email_address
        msg['To'] = self.email_address
        msg['Subject'] = "AWS Daily Cost Analysis"
        text = "Find your Cost Analysis report below\n\n"
        # Adding Email Body (Text and File)
        msg.attach(MIMEText(text))
        with open(filename, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=filename
            )
        # Adding file data to email
        part['Content-Disposition'] = 'attachment; filename="%s"' % filename
        msg.attach(part)
        # Sending email
        result = self.ses.send_raw_email(
            Source=msg['From'],
            Destinations=[self.email_address],
            RawMessage={'Data': msg.as_string()}
        )


def getDate():
    # Getting current date with time
    current_time = datetime.now()
    # Getting previous day with time
    previous_time = current_time - timedelta(days=RESULT_FOR_LAST_DAYS)
    # Formatting datetime to date
    current_date_formatted = current_time.strftime('%Y-%m-%d')
    previous_date_formatted = previous_time.strftime('%Y-%m-%d')
    return current_date_formatted, previous_date_formatted


def lambda_handler(event, context):

    dailyCost = AwsDailCostAnalysis(
        filter=FILTER, granularity=GRANULARITY, group_by=GROUP_BY, metrics=METRICS, email=EMAIL_ADDRESS)
    # Generating chart
    dailyCost.getCostByServicesAndGenerateChart()
    # sending email
    dailyCost.send_email()
    # Creating AwsDailCostAnalysis
    try:
        return {
            'statusCode': 200,
            'body': json.dumps('Report sent!')
        }
    except Exception as e:
        print(e)
