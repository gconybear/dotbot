import uuid 
import streamlit as st  
from operator import itemgetter 
import pytz 
import pickle

eastern_tz = pytz.timezone('US/Eastern') 

def get_most_recent_db_submissions(s3, N): 
    res = s3.list_objects(Bucket='rd-dotbot', Prefix=f'content/') 
    mr = get_recent_elements(res['Contents'], N) 
    
    # fblocks = pickle.loads(s3.get_object(Bucket='fs-optimization', Key=f'routes/facility-blocks/2023-02-09.pkl')['Body'].read())
    content_list = []
    for d in mr:  
        f = pickle.loads(s3.get_object(Bucket='rd-dotbot', Key=d['Key'])['Body'].read()) 
        f.update({'upload_time': str(d['LastModified'].astimezone(eastern_tz))}) 
        content_list.append(f)
        
    return content_list

def get_recent_elements(lst, n):
    # Sort the list of dictionaries by the LastModified key in descending order
    sorted_lst = sorted(lst, key=itemgetter('LastModified'), reverse=True)
    # Return the first n elements of the sorted list
    return sorted_lst[:n] 


def get_id(): return str(uuid.uuid4()) 

def password_authenticate(password): 
    
    if password == st.secrets['super_admin_password']: 
        return True 
    
    return False 