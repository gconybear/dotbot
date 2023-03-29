import streamlit as st  
import openai 


from embed import Embedder 
import LLM_PARAMS

PROMPT_KEY = 6

class AI: 
    
    def __init__(self, index): 
        
        openai.api_key = st.secrets['OPEN_AI_KEY'] 
        
        self.index = index 
        
    def get_embedding(self, text: str, model: str=LLM_PARAMS.EMBEDDING_MODEL) -> list[float]:
        
        result = openai.Embedding.create(
          model=model,
          input=text
        )
        return result["data"][0]["embedding"]
    
    def nearest_docs(self, V: list[float], K=10):  
        
        "finds the nearest docs given an embedding"
        
        return self.index.query([V], top_k=K, include_metadata=True)
    
    def embed_and_get_closest_docs(self, Q: str): 
        
        v = self.get_embedding(Q) 
        print('computed embedding --> ', v)
        docs = self.nearest_docs(v)  
        print(docs)
        
        return docs.to_dict() 
    
    def construct_prompt(self, Q: str, header=LLM_PARAMS.PROMPT_HEADERS[PROMPT_KEY], return_docs=False, personality='standard'):  
        
        if personality != 'standard': 
            header=LLM_PARAMS.PROMPT_HEADERS[6].format(personality, personality, personality) 
        else: 
            header=LLM_PARAMS.PROMPT_HEADERS[5] 

        header += """  For reference, we label our stores in the format RDXXX where XXX represents numerical signifiers. 
        For example, RD050 is equivalent to rd50, and RD005 is equivalent to rd5 or RD005 but NOT rd157."""
        
        docs = self.embed_and_get_closest_docs(Q)  
        
        print(docs.keys())
        
        MAX_LEN = 1000  
        SEPARATOR = "\n* " 
        
        current_len = len(header.split()) 
        
        sections = []
        while current_len < MAX_LEN: 
            for doc in docs['matches']:  
                print(doc)
                print(doc.keys())
                token_count = len(doc['metadata']['text'].split()) 
                if token_count <= (MAX_LEN - current_len): 
                    sections.append(SEPARATOR + doc['metadata']['text'].replace("\n", " "))  
                    current_len += token_count
                else: 
                    pass  
            break  
        
        if return_docs: 
            return header + "".join(sections) + "\n\n Q: " + Q + "\n A:", docs 
        else: 
            return header + "".join(sections) + "\n\n Q: " + Q + "\n A:"
    
    def answer(self, prompt, COMPLETIONS_API_PARAMS=LLM_PARAMS.COMPLETIONS_API_PARAMS, history=None):  
        
        if LLM_PARAMS.COMPLETIONS_MODEL == "gpt-3.5-turbo": 
            
            #st.info("Using ChatGPT API") 

            if history is not None:    

                history = [{'role': x['role'], 'content': x.get('query', x['content'])} for x in history] 

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", 
                    messages = history + [{"role": "user", "content": prompt}]
                    ) 
                    
            else:
            
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", 
                    messages=[{"role": "user", "content": prompt}]
                    ) 
                
            return response['choices'][0]['message']['content'] #.strip(' \n') 
        
        else:

            response = openai.Completion.create(
                prompt=prompt,
                **COMPLETIONS_API_PARAMS
            )

            return response["choices"][0]["text"].strip(" \n")
        
        
        
        
        