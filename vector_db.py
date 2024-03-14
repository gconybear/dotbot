# std lib
import uuid  
from datetime import datetime

# third party
from pinecone import Pinecone  
import streamlit as st  

# local 
from llm import GPT 
from miniDDB import miniDDB

class PineconeDB: 

    def __init__(self): 
        self.pc = Pinecone(api_key=st.secrets['PINECONE_SERVERLESS_KEY'])
        self.index = self.pc.Index("dotbot-serverless-index") 
        self.dotbot_ddb = miniDDB('dotbot-embeddings') 
    
    def create_upsert_object(self, input_text: str, **kwargs) -> dict:  
        
        def get_id(): return str(uuid.uuid4())
        
        # Get the embedding
        gpt = GPT()
        embedding = gpt.embed(input_text)
        if not embedding:
            return None 
        
        content_id = get_id() 
        metadata = kwargs 
        metadata['text'] = input_text
        
        # Create the upsert object
        upsert_obj = {
            "id": content_id,
            "values": embedding,
            "metadata": metadata
        }
        
        return upsert_obj 
    
    def upsert(self, input_text: str, namespace: str, submitted_by: str, **kwargs) -> bool: 
        
        # create the upsert object
        upsert_obj = self.create_upsert_object(input_text)  
        if not upsert_obj:
            return False

        ddb_obj = { 
            'id': upsert_obj['id'], 
            'metadata': upsert_obj.get('metadata', {}), 
            'namespace': namespace, 
            'submitted_at': datetime.now().isoformat(),
            'submitted_by': submitted_by, 
            'topic': None,
            'tags': None,
        }  

        for k, v in kwargs.items(): 
            ddb_obj[k] = v

        # add to dotbot_ddb 
        try:
            self.dotbot_ddb.add_item(item=ddb_obj, auto_id=False)  
        except: 
            st.write('failed to add to ddb')

        # upsert to pinecone index
        self.index.upsert(vectors=[upsert_obj], namespace=namespace) 

        return True