import requests
import json
import streamlit as st

class GPT: 

    def __init__(self):  
        
        self.completion_url = "https://api.openai.com/v1/chat/completions"  
        self.embedding_url = "https://api.openai.com/v1/embeddings" 
        self.API_KEY = st.secrets['OPEN_AI_KEY'] 
        self.system_instructions = []

    def api_call(self, payload: dict, url: str) -> dict:  
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.API_KEY}"  
            }
        
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    
    def embed(self, mssg: str, model='text-embedding-3-small') -> list[float]: 
        openai_api_key = self.API_KEY  
        url = 'https://api.openai.com/v1/embeddings'   
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {openai_api_key}',
        } 

        # Data payload
        data = {
            'input': mssg,
            'model': model
        } 

        # Make the POST request
        response = requests.post(url, headers=headers, data=json.dumps(data)) 
        if response.status_code != 200:
            return None

        return response.json()['data'][0]['embedding'] 
    
    def add_sys_instructions(self, instructions: str):  

        if not instructions: 
            return None

        self.system_instructions.append({"role": "system", "content": instructions})
 

    def answer(self, mssg: str, model="gpt-4-0125-preview", temperature=0.3, **kwargs) -> str:    

        # gpt-4-0125-preview  
        # 3.5 turbo: "gpt-3.5-turbo-0125"

        p = {
            "model": model,
            "messages": self.system_instructions + [{"role": "user", "content": mssg}],
            "temperature": temperature
        }  

        p.update(kwargs)

        payload = json.dumps(p)  

        response = self.api_call(payload=payload, url=self.completion_url)  
        if 'choices' not in response: 
            return "I'm having trouble thinking right now. Please try again later." 
        
        return response['choices'][0]['message']['content']
        

