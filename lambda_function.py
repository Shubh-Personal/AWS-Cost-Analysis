import os
import sys
import boto3
import xlsxwriter
import json
from datetime import datetime,timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class AwsDailCostAnalysis():

    def __init__(self) -> None:
        self.ses = boto3.client('ses', region_name='us-east-1')
        self.ce = boto3.client('ce')

    def getCostByServices(self):
        end_date,start_date =getDate()
        response = self.ce.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date,
                        'End': end_date
                    },
                    Granularity='DAILY',
                    Metrics=[
                        'UnblendedCost',
                    ],
                    GroupBy=[
                        {"Type": "DIMENSION","Key": "SERVICE"}
                            ],
                    Filter={
                        "Dimensions":{
                            'Key':'SERVICE',
                            'Values':[
                                'Amazon Elastic Compute Cloud - Compute',
                                'Amazon Simple Email Service',
                                'AWS Lambda',
                                'Amazon Elastic File System',
                                'AWS Cost Explorer',
                                'EC2 - Other'
                                ],
                            'MatchOptions':['EQUALS']
                        }
                    }
                )
        data = response["ResultsByTime"][0]["Groups"]
        x_data=[]
        y_data=[]
        total=0
        for costData in data:
            x_data.append(costData["Keys"][0])
            y_data.append(float(costData["Metrics"]["UnblendedCost"]["Amount"]))
            total+=float(costData["Metrics"]["UnblendedCost"]["Amount"])
        x_data.append("Total")
        y_data.append(float(total))
        return x_data,y_data

    def generatePieChart(self):
        #getting the cost related data
        services, cost = self.getCostByServices()
        workbook = xlsxwriter.Workbook('cost_analysis.xlsx')
        worksheet = workbook.add_worksheet()
        # Create a bold format
        bold_format = workbook.add_format({'bold': True})
        
        worksheet.write('A1', 'AWS Services',bold_format)
        worksheet.write('B1', 'Cost',bold_format)
        
        worksheet.write_column('A2', services)
        worksheet.write_column('B2', cost)
        chart = workbook.add_chart({'type': 'pie'})
        chart.add_series({
        'categories': '=Sheet1!$A$2:$A$7',
        'values': '=Sheet1!$B$2:$B$7',
        })
        chart.set_title({'name': 'AWS Daily Cost Analysis'})
        chart.set_legend({'position': 'right'})
        worksheet.insert_chart('D2', chart,{'x_scale': 1.5, 'y_scale': 1.5})
        workbook.close()

    def send_email(self,filename="cost_analysis.xlsx"):
        msg = MIMEMultipart()
        msg['From'] = "shubhpatel4799@gmail.com"
        msg['To'] = "shubhpatel4799@gmail.com"
        msg['Subject'] = "AWS Daily Cost Analysis"
        text = "Find your Cost Analysis report below\n\n"
        msg.attach(MIMEText(text))
        with open(filename, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=filename
            )
        part['Content-Disposition'] = 'attachment; filename="%s"' % filename
        msg.attach(part)
        result = self.ses.send_raw_email(
            Source=msg['From'],
            Destinations= ["shubhpatel4799@gmail.com"] , 
            RawMessage={'Data': msg.as_string()}
        )

def getDate():
    current_date = datetime.now()
    previous_date = current_date - timedelta(days=1)
    current_date_formatted = current_date.strftime('%Y-%m-%d')
    previous_date_formatted = previous_date.strftime('%Y-%m-%d')
    return current_date_formatted,previous_date_formatted

def lambda_handler(event, context):
    try:
        dailyCost = AwsDailCostAnalysis()
        dailyCost.generatePieChart()
        dailyCost.send_email()
        return {
            'statusCode': 200,
            'body': json.dumps('Report sent!')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps('Something went wrong!!')
        }
