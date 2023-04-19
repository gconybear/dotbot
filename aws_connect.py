import pickle
from io import BytesIO, StringIO 
import json
import boto3 
import streamlit as st  
from datetime import datetime



class S3: 
    
    def __init__(self): 
        
        self.s3 = boto3.client('s3', region_name = 'us-west-1', 
          aws_access_key_id=st.secrets['MASTER_ACCESS_KEY'], 
          aws_secret_access_key=st.secrets['MASTER_SECRET'])  
        
    def upload_file_to_s3(self, data, path, fname, file_type, bucket='rd-dotbot'):  
        
        assert file_type in ['csv', 'pkl', 'json']
        
        if file_type == 'csv':

            self.s3.upload_fileobj(BytesIO(bytes(data.to_csv(line_terminator='\r\n', index=False), encoding='utf-8')), 
                                   Bucket=bucket, Key=f'{path}{fname}.csv')   
            
        if file_type == 'json': 
            
            self.s3.put_object(Body=(bytes(json.dumps(data).encode('UTF-8'))), 
                          Bucket=bucket, Key=f'{path}{fname}.json')  
            
        if file_type == 'pkl': 
             
            self.s3.put_object(Body=pickle.dumps(data), Bucket=bucket, Key=f'{path}{fname}.pkl') 
            
        print(f'successful aws upload! {fname} uploaded to {bucket}/{path}.{file_type}')
        return True 
    


def pull_content_requests(conn): 

    all_requests = conn.list_objects(Bucket='rd-dotbot', Prefix=f'requests/') 
    completed_requests = conn.list_objects(Bucket='rd-dotbot', Prefix=f'requests/completed-requests/') 

    #st.write([x['LastModified'].date() for x in all_requests['Contents']])

    all_req_fp = [(x['Key'].replace('requests/', '').strip('.pkl'), x['LastModified'].date()) for x in all_requests['Contents'] if 'completed-requests' not in x['Key']] 
    comp_req_fp = [x['Key'].replace('requests/completed-requests/', '').strip('.pkl') for x in completed_requests['Contents']] 

    # only incomplete requests 
    incomplete = [(k,d) for k,d in all_req_fp if k not in comp_req_fp] 

    # read them all  
    reqs = []
    for k,d in incomplete: 
        fp = f"requests/{k}.pkl" 
        f = pickle.loads(conn.get_object(Bucket='rd-dotbot', Key=fp)['Body'].read())  
        if not isinstance(f['request'], bool):  
            f.update({'request_id': k, 'date': d}) 
            reqs.append(f)


    return sorted(reqs, key=lambda x: x['date'], reverse=True)