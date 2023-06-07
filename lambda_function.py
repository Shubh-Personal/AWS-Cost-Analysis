#importing all required modules
import os
import sys
import boto3
import xlsxwriter
import json
from datetime import datetime,timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#Class for fetching daily cost using cost explorer and generating excel
class AwsDailCostAnalysis():

    #constructor for setting up aws services object
    def __init__(self) -> None:
        self.ses = boto3.client('ses', region_name='us-east-1')
        self.ce = boto3.client('ce')

    #function for getting aws daily cost for specific services
    def getCostByServices(self):
        #getting the today and previous day for gettig cost
        end_date,start_date =getDate()
        #getting Aws cost for specific resources
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
        #Fetching response data
        data = response["ResultsByTime"][0]["Groups"]
        x_data=[]
        y_data=[]
        total=0
        #Fetching services and their cost 
        for costData in data:
            x_data.append(costData["Keys"][0])
            y_data.append(float(costData["Metrics"]["UnblendedCost"]["Amount"]))
            total+=float(costData["Metrics"]["UnblendedCost"]["Amount"])
        #Gettign the total cost
        x_data.append("Total")
        y_data.append(float(total))
        return x_data,y_data

    #function for generating pie chart for data
    def generatePieChart(self):
        #getting the cost related data
        services, cost = self.getCostByServices()
        #Creating new Excel sheet
        workbook = xlsxwriter.Workbook('cost_analysis.xlsx')
        #Adding new worksheet
        worksheet = workbook.add_worksheet()
        # Create a bold format
        bold_format = workbook.add_format({'bold': True})
        #Adding Header Column for data
        worksheet.write('A1', 'AWS Services',bold_format)
        worksheet.write('B1', 'Cost',bold_format)
        #Adding data in Excel file from list
        worksheet.write_column('A2', services)
        worksheet.write_column('B2', cost)
        #selecting chart type
        chart = workbook.add_chart({'type': 'pie'})
        #Adding data in chart
        chart.add_series({
        'categories': '=Sheet1!$A$2:$A$7',
        'values': '=Sheet1!$B$2:$B$7',
        })
        #Setting metadata for chart
        chart.set_title({'name': 'AWS Daily Cost Analysis'})
        chart.set_legend({'position': 'right'})
        #Adding chart at D2 cel with 1.5 scale
        worksheet.insert_chart('D2', chart,{'x_scale': 1.5, 'y_scale': 1.5})
        workbook.close()

    #this function sends the generated email to user
    def send_email(self,filename="cost_analysis.xlsx"):
        msg = MIMEMultipart()
        #Metadata for Email
        msg['From'] = "shubhpatel4799@gmail.com"
        msg['To'] = "shubhpatel4799@gmail.com"
        msg['Subject'] = "AWS Daily Cost Analysis"
        text = "Find your Cost Analysis report below\n\n"
        #Adding Email Body (Text and File)
        msg.attach(MIMEText(text))
        with open(filename, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=filename
            )
        #Adding file data to email
        part['Content-Disposition'] = 'attachment; filename="%s"' % filename
        msg.attach(part)
        #Sending email
        result = self.ses.send_raw_email(
            Source=msg['From'],
            Destinations= ["shubhpatel4799@gmail.com"] , 
            RawMessage={'Data': msg.as_string()}
        )

def getDate():
    #Getting current date with time
    current_time = datetime.now()
    #Getting previous day with time
    previous_time = current_time
    #Formatting datetime to date
    current_date_formatted = current_time.strftime('%Y-%m-%d')
    previous_date_formatted = previous_time.strftime('%Y-%m-%d')
    return current_date_formatted,previous_date_formatted

def lambda_handler(event, context):
    try:
        #Creating AwsDailCostAnalysis
        dailyCost = AwsDailCostAnalysis()
        #Generating chart
        dailyCost.generatePieChart()
        #sending email
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
