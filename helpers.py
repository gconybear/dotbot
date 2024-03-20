import uuid 
import streamlit as st  
from operator import itemgetter 
import pytz 
import pickle 
import re 

eastern_tz = pytz.timezone('US/Eastern')   

def contains_shortcut(text):
    # Define a regex pattern to match '--' followed by an optional space and then any word or phrase
    pattern = r"--\s*\w+"
    
    # Search for the pattern in the text
    if re.search(pattern, text):
        return True
    else:
        return False

def standardize_site_code(input_string):
    # Define the regex pattern to match the site codes
    # This pattern looks for 'RD' or 'rd' followed by 1 to 3 digits
    pattern = re.compile(r'\b(rd|RD)(\d{1,3})\b')

    def replace_func(match):
        # Extract the site code parts: prefix (RD/rd) and the numeric part
        prefix = match.group(1).upper()  # Ensure the prefix is uppercase
        numeric_part = match.group(2)

        # Standardize the numeric part to 3 digits with leading zeros
        standardized_numeric_part = numeric_part.zfill(3)

        # Return the standardized site code
        return f'{prefix}{standardized_numeric_part}'

    # Use the sub() function to replace all occurrences in the input string
    standardized_string = pattern.sub(replace_func, input_string)

    return standardized_string

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

def password_authenticate(password) -> dict:  

    password = password.strip()

    if password == st.secrets['base_password']: 
        return {'valid': True, 'admin': False}
    
    if password == st.secrets['super_admin_password']: 
        return {'valid': True, 'admin': True}
    
    if password == st.secrets['super_admin_password1']: 
        return {'valid': True, 'admin': True}
    
    return {'valid': False, 'admin': False}  

def get_sql_examples(): 

    examples = [
        "\n- What is the occupancy at RD109?",
        "How many move ins have we had at RD006 so far this month?",
        "What is the temp gate code at RD157?",
        "List the occupancy for each site code in the portfolio", 
        "What is the current street rate for 10x10's at RD190?",
        "How many tenants have a monthly rate $50 or greater than the street rate at their unit?",
        "How many move ins did we have at RD030 in March 2021?", 
        "What is the average street rate for 10x10's vs 5x5's in the portfolio?",
        "How many tenants are on autopay at RD050?", 
        "What percentage of tenants at RD002 have homeowner's insurance?",
    ] 

    return '\n- '.join(examples)