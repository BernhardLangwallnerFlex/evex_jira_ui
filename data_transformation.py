import pandas as pd
import numpy as np
import json

# read json from data/jira-servicedesk-schema-objects.json
# with open('data/jira-servicedesk-schema-objects.json', 'r') as f:
#    schema = json.load(f)
# object_id_to_name = {v['id']: v['name'] for v in schema['values']}

# read object_id_to_name from json file
with open('data/object_id_to_name.json', 'r') as f:#
    object_id_to_name = json.load(f)

def load_issues(issues):
    df = {'key': [], 'summary': [], 'description': [], 'status': [], 'status_category': [], 'created': [], \
        'updated': [], 'labels': [],'source':[],'priority':[],'category': [],'issuetype': [] , 'main_category_id': [],\
        'sub_category_id': [], 'currentstatus_name': [], 'currentstatus_date': [], 'comments': [], 'request_type': [],\
            'priority': [], 'clones': [], 'cloned_by': [], 'zentrale': [], 'filiale': [], 'Link': []}
    for issue in issues:
        df['key'].append(issue['key'])
        df['summary'].append(issue['fields']['summary'])
        df['description'].append(issue['fields']['description'])
        df['status'].append(issue['fields']['status']['name'])
        df['status_category'].append(issue['fields']['status']['statusCategory']['name'])
        #df['creator'].append(issue['fields']['creator']['displayName'])
        df['issuetype'].append(issue['fields']['issuetype']['name'])
        df['created'].append(issue['fields']['created'])
        df['updated'].append(issue['fields']['updated'])
        df['labels'].append(issue['fields']['labels'])
        df['priority'].append(issue['fields']['priority']['name'])
        df['category'].append(issue['fields']['customfield_10065'])

        if issue['fields']['customfield_10010'] is not None:
            df['request_type'].append(issue['fields']['customfield_10010']['requestType']['name'])
        else:
            df['request_type'].append('')
        if issue['fields']['comment'] is not None:
            df['comments'].append('\n\n'.join([c['body'] for c in issue['fields']['comment']['comments']]))
        else:
            df['comments'].append([])

        try:
            df['currentstatus_name'].append(issue['fields']['customfield_10010']['currentStatus']['status'])
            df['currentstatus_date'].append(issue['fields']['customfield_10010']['currentStatus']['statusDate']['jira'])
        except:
            df['currentstatus_name'].append('')
            df['currentstatus_date'].append('')

        try:
            v = issue['fields']['customfield_10675']['value']
            df['source'].append(v)
        except:
            df['source'].append('')

        cf = issue['fields']['customfield_10680']
        if len(cf)>0:
            df['main_category_id'].append(cf[0]['objectId'])
        else:
            df['main_category_id'].append('')
        cf = issue['fields']['customfield_10679']
        if len(cf)>0:
            df['sub_category_id'].append(cf[0]['objectId'])
        else:
            df['sub_category_id'].append('')

        try: 
            df['clones'].append(issue['fields']['issuelinks'][0]['outwardIssue']['key'])    
        except:
            df['clones'].append('')
        try:
            df['cloned_by'].append(issue['fields']['issuelinks'][0]['inwardIssue']['key'])
        except:
            df['cloned_by'].append('')
        
        try:
            df['zentrale'].append("ID_" + str(issue['fields']['customfield_10673'][0]['objectId']))
        except:
            df['zentrale'].append('')
        try:
            df['filiale'].append("ID_" + str(issue['fields']['customfield_10674'][0]['objectId']))
        except:
            df['filiale'].append('')

        df['Link'].append(issue['fields']['customfield_10010']['_links']['agent'])

    df = pd.DataFrame(df)
    ### convert created, updated to datetime
    df['created'] = pd.to_datetime(df['created'], errors='coerce', utc=True)
    df['updated'] = pd.to_datetime(df['updated'], errors='coerce', utc=True)
    df['currentstatus_date'] = pd.to_datetime(df['currentstatus_date'], errors='coerce', utc=True)

    df['week_number'] = df['created'].dt.isocalendar().week
    df['week_string'] = df['created'].dt.strftime('%G-W%V')

    df['time_to_resolution_h'] = (df['currentstatus_date'] - df['created']).dt.total_seconds() / 3600
    df['time_to_resolution_days'] = (df['currentstatus_date'] - df['created']).dt.days
    df['resolution'] = '> 1 day'
    df['resolution'] = np.where(df['time_to_resolution_days']<=1, 'Same day', '> 1 day')
    df['bdays'] = np.busday_count(df['created'].to_numpy(dtype='datetime64[D]'),df['updated'].to_numpy(dtype='datetime64[D]'))
    df['created_string'] = df['created'].dt.strftime('%Y-%m-%d')
    df['updated_string'] = df['updated'].dt.strftime('%Y-%m-%d')
    df['year'] = df['created'].dt.year
    df['month'] = df['created'].dt.month
    df['Hauptkategorie'] = df['main_category_id'].map(object_id_to_name)
    df['Unterkategorie'] = df['sub_category_id'].map(object_id_to_name)
    # fill empty values with "NA"
    df['Unterkategorie'] = df['Unterkategorie'].fillna('NA')
    # put time to resolution into bins
    bins = [0,1,2,4,8,24,48,72,7*24,14*24,21*24]
    df['time_to_resolution_bin'] = pd.cut(df['time_to_resolution_h'], bins=bins)
    df['time_to_resolution_bin'] = df['time_to_resolution_bin'].apply(
        lambda x: f"{int(x.left)}–{int(x.right)}"
    )
    df['zentrale'] = df['zentrale'].astype(str)
    df['filiale'] = df['filiale'].astype(str)
    df['firma'] = "IPRO"
    # move firma column to the front
    df = df[['firma', *[col for col in df.columns if col != 'firma']]]

    return df


def upsert_jira_data(df_old, df_new, key_col="key"):
    df_old, df_new = df_old.align(df_new, join="outer", axis=1)

    df_old = df_old.set_index(key_col)
    df_new = df_new.set_index(key_col)

    df_old.update(df_new)

    new_rows = df_new.loc[df_new.index.difference(df_old.index)]
    df_combined = pd.concat([df_old, new_rows])

    return df_combined.reset_index()



def load_issues_Amparex(issues):
    df = {'key': [], 'summary': [], 'description': [], 'status': [], 'status_category': [], 'created': [], \
        'updated': [], 'labels': [],'source':[],'priority':[],'category': [],'issuetype': [] , 'main_category_id': [],\
        'sub_category_id': [], 'currentstatus_name': [], 'currentstatus_date': [], 'comments': [], 'request_type': [],\
            'priority': [], 'clones': [], 'cloned_by': [], 'zentrale': [], 'filiale': [], 'Link': []}
    for issue in issues:
        df['key'].append(issue['key'])
        df['summary'].append(issue['fields']['summary'])
        df['description'].append(issue['fields']['description'])
        df['status'].append(issue['fields']['status']['name'])
        df['status_category'].append(issue['fields']['status']['statusCategory']['name'])
        #df['creator'].append(issue['fields']['creator']['displayName'])
        df['issuetype'].append(issue['fields']['issuetype']['name'])
        df['created'].append(issue['fields']['created'])
        df['updated'].append(issue['fields']['updated'])
        df['labels'].append(issue['fields']['labels'])
        df['priority'].append(issue['fields']['priority']['name'])
        df['category'].append(issue['fields']['customfield_10065'])

        if issue['fields']['customfield_10010'] is not None:
            df['request_type'].append(issue['fields']['customfield_10010']['requestType']['name'])
        else:
            df['request_type'].append('')
        if issue['fields']['comment'] is not None:
            df['comments'].append('\n\n'.join([c['body'] for c in issue['fields']['comment']['comments']]))
        else:
            df['comments'].append([])

        try:
            df['currentstatus_name'].append(issue['fields']['customfield_10010']['currentStatus']['status'])
            df['currentstatus_date'].append(issue['fields']['customfield_10010']['currentStatus']['statusDate']['jira'])
        except:
            df['currentstatus_name'].append('')
            df['currentstatus_date'].append('')

        try:
            v = issue['fields']['customfield_10675']['value']
            df['source'].append(v)
        except:
            df['source'].append('')

        cf = issue['fields']['customfield_10680']
        if len(cf)>0:
            df['main_category_id'].append(cf[0]['objectId'])
        else:
            df['main_category_id'].append('')
        cf = issue['fields']['customfield_10679']
        if len(cf)>0:
            df['sub_category_id'].append(cf[0]['objectId'])
        else:
            df['sub_category_id'].append('')

        try: 
            df['clones'].append(issue['fields']['issuelinks'][0]['outwardIssue']['key'])    
        except:
            df['clones'].append('')
        try:
            df['cloned_by'].append(issue['fields']['issuelinks'][0]['inwardIssue']['key'])
        except:
            df['cloned_by'].append('')
        
        try:
            df['zentrale'].append("ID_" + str(issue['fields']['customfield_10673'][0]['objectId']))
        except:
            df['zentrale'].append('')
        try:
            df['filiale'].append("ID_" + str(issue['fields']['customfield_10674'][0]['objectId']))
        except:
            df['filiale'].append('')

        try:
            df['Link'].append(issue['fields']['customfield_10010']['_links']['agent'])
        except:
            df['Link'].append('')

    df = pd.DataFrame(df)
    ### convert created, updated to datetime
    df['created'] = pd.to_datetime(df['created'], errors='coerce', utc=True)
    df['updated'] = pd.to_datetime(df['updated'], errors='coerce', utc=True)
    df['currentstatus_date'] = pd.to_datetime(df['currentstatus_date'], errors='coerce', utc=True)

    df['week_number'] = df['created'].dt.isocalendar().week
    df['week_string'] = df['created'].dt.strftime('%G-W%V')

    df['time_to_resolution_h'] = (df['currentstatus_date'] - df['created']).dt.total_seconds() / 3600
    df['time_to_resolution_days'] = (df['currentstatus_date'] - df['created']).dt.days
    df['resolution'] = '> 1 day'
    df['resolution'] = np.where(df['time_to_resolution_days']<=1, 'Same day', '> 1 day')
    df['bdays'] = np.busday_count(df['created'].to_numpy(dtype='datetime64[D]'),df['updated'].to_numpy(dtype='datetime64[D]'))
    df['created_string'] = df['created'].dt.strftime('%Y-%m-%d')
    df['updated_string'] = df['updated'].dt.strftime('%Y-%m-%d')
    df['year'] = df['created'].dt.year
    df['month'] = df['created'].dt.month
    df['Hauptkategorie'] = df['main_category_id'].map(object_id_to_name)
    df['Unterkategorie'] = df['sub_category_id'].map(object_id_to_name)
    # fill empty values with "NA"
    df['Unterkategorie'] = df['Unterkategorie'].fillna('NA')
    # put time to resolution into bins
    bins = [0,1,2,4,8,24,48,72,7*24,14*24,21*24]
    df['time_to_resolution_bin'] = pd.cut(df['time_to_resolution_h'], bins=bins)
    df['time_to_resolution_bin'] = df['time_to_resolution_bin'].apply(
        lambda x: f"{int(x.left)}–{int(x.right)}"
    )
    df['zentrale'] = df['zentrale'].astype(str)
    df['filiale'] = df['filiale'].astype(str)
    df['firma'] = "Amparex"
    # move firma column to the front
    df = df[['firma', *[col for col in df.columns if col != 'firma']]]

    return df

