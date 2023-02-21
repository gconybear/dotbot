import openai   
import streamlit as st 
import pinecone

import LLM_PARAMS  
import helpers 
from aws_connect import S3


class Embedder: 
    
    def __init__(self, index): 
        
        openai.api_key = st.secrets['OPEN_AI_KEY']  
        self.index = index

        
    def get_embedding(self, text: str, model: str=LLM_PARAMS.EMBEDDING_MODEL) -> list[float]:
        
        result = openai.Embedding.create(
          model=model,
          input=text
        )
        return result["data"][0]["embedding"]  
    
    def embed_and_save(self, content_id: str, text: str, metadata: dict, aws=True):  
        
        # save to aws
        if aws: 
            s3 = S3() 
            s3.upload_file_to_s3(
                data={'content_id': content_id, 'content': text, 'metadata': metadata}, 
                path='content/', 
                fname=content_id, 
                file_type='pkl'
            )

            
        v = self.get_embedding(text) 
        _id = content_id # helpers.get_id()   
        self.content_id = _id 
        
        if len(metadata) != 0: 
            metadata.update({'text': text}) 
        else: 
            metadata = {'text': text}  
            
        metadata['content_path'] = f'content/{_id}.pkl'
        
        # saving to pinecone 
        to_upsert = (_id, v, metadata) 
        self.index.upsert([to_upsert]) 
        
        
        return True 
        
        
        
        
        
    
     