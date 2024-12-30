from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime, timedelta
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import xml.etree.ElementTree as ET
import requests

app = Flask(__name__)

def parse_dmarc_report(file_path):
    #print(f'Parsing DMARC report: {file_path}')
    tree = ET.parse(file_path)
    root = tree.getroot()
    report = {
        'organization': root.findtext('.//report_metadata/org_name'),
        'domain': root.findtext('.//policy_published/domain'),
        'report_id': root.findtext('.//report_metadata/report_id'),
        'date_range': {
            'begin': datetime.utcfromtimestamp(int(root.findtext('.//date_range/begin'))).strftime('%Y-%m-%d'),
            'end': datetime.utcfromtimestamp(int(root.findtext('.//date_range/end'))).strftime('%Y-%m-%d')
        },
        'adkim': root.findtext('.//policy_published/adkim'),
        'aspf': root.findtext('.//policy_published/aspf'),
        'p': root.findtext('.//policy_published/p'),
        'sp': root.findtext('.//policy_published/sp'),
        'pct': int(root.findtext('.//policy_published/pct')),
        'fo': root.findtext('.//policy_published/fo'),
        'records': []
    }
    for record in root.findall('.//record'):
        source_ip = record.findtext('.//row/source_ip')
        owner = fetch_rdap_info(source_ip)
        report['records'].append({
            'source_ip': source_ip,
            'owner': owner,
            'count': int(record.findtext('.//row/count')),
            'policy_evaluated_disposition': record.findtext('.//row/policy_evaluated/disposition'),
            'policy_evaluated_dkim': record.findtext('.//row/policy_evaluated/dkim'),
            'policy_evaluated_spf': record.findtext('.//row/policy_evaluated/spf'),
            'envelope_to': record.findtext('.//identifiers/envelope_to'),
            'header_from': record.findtext('.//identifiers/header_from'),
            'envelope_from': record.findtext('.//identifiers/envelope_from'),
            'auth_results_dkim_domain': record.findtext('.//auth_results/dkim/domain'),
            'auth_results_dkim_result': record.findtext('.//auth_results/dkim/result'),
            'auth_results_spf_domain': record.findtext('.//auth_results/spf/domain'),
            'auth_results_spf_result': record.findtext('.//auth_results/spf/result')
        })
    return report

def load_reports():
    reports = []
    if os.path.exists('imported_reports.json') and os.path.getsize('imported_reports.json') > 0:
        with open('imported_reports.json', 'r') as f:
            for line in f:
                reports.append(json.loads(line))
    folder_path = './extracted_files'
    for filename in os.listdir(folder_path):
        if filename.endswith('.xml'):
            file_path = os.path.join(folder_path, filename)
            report = parse_dmarc_report(file_path)
            if report not in reports:
                reports.append(report)
            os.remove(file_path)
    
    with open('imported_reports.json', 'w') as f:
        for report in reports:
            f.write(json.dumps(report) + '\n')
    return reports

@app.route('/', methods=['POST','GET'])
def select_domain():
    reports = load_reports()
    domains = list(set(report['domain'] for report in reports))
    domains.sort()

    now = datetime.now()
    week_ago = now - timedelta(days=7)

    failed_domains = []
    for report in reports:
        if report['date_range']['begin'] > week_ago.strftime('%Y-%m-%d') and report['date_range']['end'] < now.strftime('%Y-%m-%d'):
            for record in report['records']:
                if record['auth_results_dkim_result'] != 'pass' or record['auth_results_spf_result'] != 'pass' or record['policy_evaluated_dkim'] != 'pass' or record['policy_evaluated_spf'] != 'pass':
                    if report['domain'] not in failed_domains:
                        failed_domains.append(report['domain'])

    return render_template('home.html', domains=domains, failed_domains=failed_domains)

@app.route('/reports', methods=['GET'])
def get_reports():
    domain = request.args.get('domain')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    print(start_date_str, end_date_str)

    date_format = '%Y-%m-%d'

    try:
        start_date = datetime.strptime(start_date_str, date_format)
        start_date_unix = int(start_date.timestamp())
        end_date = datetime.strptime(end_date_str, date_format)
        end_date_unix = int(end_date.timestamp())
    except ValueError:
        start_date_unix = None
        end_date_unix = None

    reports = load_reports()
    filtered_reports = []

    for report in reports:
        if domain and domain != report['domain']:
            continue
        if start_date_unix and int(datetime.strptime(report['date_range']['begin'], date_format).timestamp()) < start_date_unix:
            continue
        if end_date_unix and int(datetime.strptime(report['date_range']['end'], date_format).timestamp()) > end_date_unix:
            continue
        filtered_reports.append(report)

    if not filtered_reports:
        return render_template('report_empty.html', domain=domain)

    # Ensure the 'static' directory exists
    if not os.path.exists('static'):
        os.makedirs('static')

    create_dkim_graph(filtered_reports)
    create_spf_graph(filtered_reports)
    create_dkim_policy_graph(filtered_reports)
    create_spf_policy_graph(filtered_reports)

    failed_spf_entries = []
    for report in filtered_reports:
        for record in report['records']:
            if not record['auth_results_spf_result'] == 'pass':
                failed_spf_entries.append(record)

    failed_dkim_entries = []
    for report in filtered_reports:
        for record in report['records']:
            if not record['auth_results_dkim_result'] == 'pass':
                failed_dkim_entries.append(record)

    failed_spf_policy_entries = []
    for report in filtered_reports:
        for record in report['records']:
            if not record['policy_evaluated_spf'] == 'pass':
                failed_spf_policy_entries.append(record)
    
    failed_dkim_policy_entries = []
    for report in filtered_reports:
        for record in report['records']:
            if not record['policy_evaluated_dkim'] == 'pass':
                failed_dkim_policy_entries.append(record)

    # Define the headers for each table
    headers = ['source_ip', 'owner', 'date', 'count', 'policy_evaluated_disposition', 'policy_evaluated_dkim', 'policy_evaluated_spf', 'envelope_to', 'header_from', 'envelope_from', 'auth_results_dkim_domain', 'auth_results_dkim_result', 'auth_results_spf_domain', 'auth_results_spf_result']

    # Prepare the tables data
    tables = [
        prepare_table_data(failed_spf_entries, headers, 'Failed SPF Entries', filtered_reports),
        prepare_table_data(failed_dkim_entries, headers, 'Failed DKIM Entries', filtered_reports),
        prepare_table_data(failed_spf_policy_entries, headers, 'Failed SPF Policy Entries', filtered_reports),
        prepare_table_data(failed_dkim_policy_entries, headers, 'Failed DKIM Policy Entries', filtered_reports)
    ]

    tables = [table for table in tables if table is not None]

    return render_template('report.html', domain=domain, graphs=['static/dkim_results_pie_chart.png', 'static/spf_results_pie_chart.png', 'static/dkim_policy_results_pie_chart.png','static/spf_policy_results_pie_chart.png'], statistics=[], tables=tables)

def create_dkim_graph(filtered_reports):
    # Count the occurrences of 'pass' and 'fail' in 'auth_results_dkim_result'
    dkim_results = {'pass': 0, 'fail': 0}
    for report in filtered_reports:
        for record in report['records']:
            result = record['auth_results_dkim_result']
            if result in dkim_results:
                dkim_results[result] += 1
    #print(dkim_results)

    # Create a pie chart
    labels = 'Pass', 'Fail'
    sizes = [dkim_results['pass'], dkim_results['fail']]
    colors = ['green', 'red']
    explode = (0.1, 0)  # explode the 1st slice (i.e. 'Pass')

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('DMARC Report: DKIM Results')
    # Save the pie chart as an image file
    if(os.path.exists('static/dkim_results_pie_chart.png')):
        os.remove('static/dkim_results_pie_chart.png')
    plt.savefig('static/dkim_results_pie_chart.png')
    plt.close()

def create_spf_graph(filtered_reports):
    # Count the occurrences of 'pass' and 'fail' in 'auth_results_spf_result'
    spf_results = {'pass': 0, 'fail': 0, 'none': 0, 'neutral': 0, 'softfail': 0, 'temperror': 0, 'permerror': 0}
    for report in filtered_reports:
        for record in report['records']:
            result = record['auth_results_spf_result']
            if result in spf_results:
                spf_results[result] += 1
    #print(spf_results)

    # Create a pie chart
    labels = 'Pass', 'Fail', 'None', 'Neutral', 'Softfail', 'Temperror', 'Permerror'
    sizes = [spf_results['pass'], spf_results['fail'], spf_results['none'], spf_results['neutral'], spf_results['softfail'], spf_results['temperror'], spf_results['permerror']]
    colors = ['green', 'red', 'grey', 'blue','yellow', 'orange', 'purple']
    explode = (0, 0.1 , 0, 0, 0, 0, 0)  # explode the 1st slice (i.e. 'Pass')

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('DMARC Report: SPF Results')
    # Save the pie chart as an image file
    if(os.path.exists('static/spf_results_pie_chart.png')):
        os.remove('static/spf_results_pie_chart.png')
    plt.savefig('static/spf_results_pie_chart.png')
    plt.close()

def create_dkim_policy_graph(filtered_reports):
    # Count the occurrences of 'pass' and 'fail' in 'policy_evaluated_dkim'
    dkim_results = {'pass': 0, 'fail': 0}
    for report in filtered_reports:
        for record in report['records']:
            result = record['policy_evaluated_dkim']
            if result in dkim_results:
                dkim_results[result] += 1
    #print(dkim_results)

    # Create a pie chart
    labels = 'Pass', 'Fail'
    sizes = [dkim_results['pass'], dkim_results['fail']]
    colors = ['green', 'red']
    explode = (0.1, 0)  # explode the 1st slice (i.e. 'Pass')

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('DMARC Report: DKIM Policy Results')
    # Save the pie chart as an image file
    if(os.path.exists('static/dkim_policy_results_pie_chart.png')):
        os.remove('static/dkim_policy_results_pie_chart.png')
    plt.savefig('static/dkim_policy_results_pie_chart.png')
    plt.close()

def create_spf_policy_graph(filtered_reports):
    # Count the occurrences of 'pass' and 'fail' in 'policy_evaluated_spf'
    spf_results = {'pass': 0, 'fail': 0}
    for report in filtered_reports:
        for record in report['records']:
            result = record['policy_evaluated_spf']
            if result in spf_results:
                spf_results[result] += 1
    #print(spf_results)

    # Create a pie chart
    labels = 'Pass', 'Fail'
    sizes = [spf_results['pass'], spf_results['fail']]
    colors = ['green', 'red']
    explode = (0, 0.1)  # explode the 1st slice (i.e. 'Pass')

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('DMARC Report: SPF Policy Results')
    # Save the pie chart as an image file
    if(os.path.exists('static/spf_policy_results_pie_chart.png')):
        os.remove('static/spf_policy_results_pie_chart.png')
    plt.savefig('static/spf_policy_results_pie_chart.png')
    plt.close()

def prepare_table_data(records, headers, title, reports):
    if not records:
        return None
    for record in records:
        record['date'] = ''
    for report in reports:
        for record in records:
            if record in report['records']:
                record['date'] = report['date_range']['begin']+" - "+report['date_range']['end']
    return {
        'title': title,
        'headers': headers,
        'rows': [[record.get(header, '') for header in headers] for record in records]
    }

def fetch_rdap_info(ip):
    try:
        print(f"Fetching RDAP data for IP {ip}")
        response = requests.get(f'https://www.rdap.net/ip/{ip}')
        response.raise_for_status()
        data = response.json()
        return data.get('name', 'Unknown')
    except requests.RequestException as e:
        print(f"Error fetching RDAP data for IP {ip}: {e}")
        return 'Unknown'

if __name__ == '__main__':
    app.run(debug=True)