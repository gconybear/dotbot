import pickle
from io import BytesIO, StringIO 
import json
import boto3 
import streamlit as st 



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

