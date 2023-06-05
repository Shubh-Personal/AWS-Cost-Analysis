import json
import os
import sys
import boto3
import datetime
import pandas as pd
import traceback
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#Global
REGION = "us-east-1"
MONTH_SPAN = 2
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./vendored"))

def getStartAndEndDatesinISO():
    end = datetime.date.today().replace(day=1)
    start = datetime.date.today().replace(day=1)
    if end.month-MONTH_SPAN<1:
        start = start.replace(month=12+end.month-MONTH_SPAN).replace(year=end.year-1)
     
    else:
        start = start.replace(month=end.month-MONTH_SPAN)
        
    return end.isoformat(),start.isoformat()        

class CostVisualizer:

    def __init__(self):
        self.report=None
        self.costexpClient = boto3.client('ce',region_name=REGION)
        self.end,self.start = getStartAndEndDatesinISO()
        print(self.end, self.start)
        
    def send_report(self):
        results = []
        response = self.costexpClient.get_cost_and_usage(
            TimePeriod={
                'Start': self.start,
                'End': self.end
            },
            Granularity='MONTHLY',
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
                        'Amazon Cost Explorer'
                         ],
                     'MatchOptions':['EQUALS']
                 }
             }
        )
            
        if response:
            results.extend(response['ResultsByTime'])
     
            while 'nextToken' in response:
                nextToken = response['nextToken']
                response = self.costexpClient.get_cost_and_usage(
                    TimePeriod={
                        'Start': self.start,
                        'End': self.end
                    },
                    Granularity='MONTHLY',
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
                                'Amazon Cost Explorer'
                                 ],
                             'MatchOptions':['EQUALS']
                         }
                     }
                    ,
                    NextPageToken=nextToken
                )
     
                results.extend(response['ResultsByTime'])
                if 'nextToken' in response:
                    nextToken = response['nextToken']
                else:
                    nextToken = False
        rows = []
        sort = ''
        for v in results:
            row = {'date':v['TimePeriod']['Start']}
            sort = v['TimePeriod']['Start']
            for i in v['Groups']:
                key = i['Keys'][0]
                # if key in self.accounts:
                #     key = self.accounts[key][ACCOUNT_LABEL]
                row.update({key:float(i['Metrics']['UnblendedCost']['Amount'])}) 
            if not v['Groups']:
                row.update({'Total':float(v['Total']['UnblendedCost']['Amount'])})
            rows.append(row)  
        print(rows)
        df = pd.DataFrame(rows)
        df.set_index("date", inplace= True)
        df = df.fillna(0.0)
        df = df.T
        df = df.sort_values(sort, ascending=False)
        report = {'Name':'Cost Analysis', 'Data':df}
        
        #generating Xls
        os.chdir('/tmp')
        writer = pd.ExcelWriter('cost_analysis.xlsx', engine='xlsxwriter')
        workbook = writer.book
        report['Data'].to_excel(writer, sheet_name=report['Name'])
        worksheet = writer.sheets[report['Name']]
        chart = workbook.add_chart({'type': 'column', 'subtype': 'stacked'})
        chartend=12
        for row_num in range(1, len(report['Data']) + 1):
            chart.add_series({
                'name':       [report['Name'], row_num, 0],
                'categories': [report['Name'], 0, 1, 0, chartend],
                'values':     [report['Name'], row_num, 1, row_num, chartend],
            })
        chart.set_y_axis({'label_position': 'low'})
        chart.set_x_axis({'label_position': 'low'})
        worksheet.insert_chart('O2', chart, {'x_scale': 2.0, 'y_scale': 2.0})
        writer.close()

        msg = MIMEMultipart()
        msg['From'] = "shubhpatel4799@gmail.com"
        msg['To'] = "shubhpatel4799@gmail.com"
        msg['Subject'] = "Cost Analysis"
        text = "Find your Cost Analysis report below\n\n"
        msg.attach(MIMEText(text))
        # s3 = boto3.client('s3',region_name=REGION)
        
        with open("cost_analysis.xlsx", "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name="cost_analysis.xlsx"
            )
            # res = s3.client.put_object(Bucket='shubh-s3-learn1',Body=fil.read())
        part['Content-Disposition'] = 'attachment; filename="%s"' % "cost_analysis.xlsx"
        msg.attach(part)
        ses = boto3.client('ses', region_name=REGION)
        result = ses.send_raw_email(
            Source=msg['From'],
            Destinations= ["shubhpatel4799@gmail.com"] , 
            RawMessage={'Data': msg.as_string()}
        )
        


def lambda_handler(event, context):
    try:
    costVisualizer = CostVisualizer()
    costVisualizer.send_report()
        return {
            'statusCode': 200,
            'body': json.dumps('Report sent!')
        }
    except Exception as e:
        traceback.format_exc()
        return {
            'statusCode': 500,
            'body': json.dumps('Something went wrong!!')
        }
