# std lib 
import time 

# third party
from pinecone import Pinecone  
import streamlit as st 

# local 
from llm import GPT 
from prompts import base_context



class RAG:   

    def __init__(self, 
                 llm='gpt',  
                 base_context=base_context.BASE_CONTEXT):  
        

        assert llm in ['gpt'] # only gpt is supported for now         

        if llm == 'gpt': 
            self.llm = GPT() 

        self.base_prompt = base_context  
        self.agent_name = 'base' 
        self.shortcuts = ['--base', '-- base']

    def prepare_context(self, query: str, MAX_LEN=800, SEPARATOR = "\n* ", return_docs=False, namespace='original', top_k=7) -> str: 
        """ 
        function to build context given user query 

        right now, just retrieves docs via cosine similarity
        in the future, can also rank, prune, and summarize context as needed 
        """
        
        # get embedding 
        embed_start = time.time()
        embedding = self.llm.embed(query) 
        embed_end = time.time() 
        embed_diff = embed_end - embed_start

        # retrieve relevant docs 
        ret_start = time.time()
        retriever = Retriever() 
        docs = retriever.query_pinecone_index(vector=embedding, namespace=namespace, top_k=top_k)  
        ret_end = time.time()
        ret_diff = ret_end - ret_start

        # builds context by concatenating text from relevant docs, nothing fancy for now
        cbuild_start = time.time()
        context = []
        current_len = 0 
        while current_len < MAX_LEN: 
            for doc in docs.get('matches', []):    
                text = doc['metadata']['text']
                token_count = len(text.split())
                if current_len + token_count < MAX_LEN: 
                    context.append(SEPARATOR + text.replace("\n", " "))
                    current_len += token_count 
                else: 
                    break  
            break  
    
        cbuild_end = time.time()
        cbuild_diff = cbuild_end - cbuild_start 

        time_dict = {
            "embedding": embed_diff, 
            "retrieval": ret_diff, 
            "context_build": cbuild_diff
        }

        if return_docs:
            return "".join(context).strip(), time_dict, docs 
    
        return "".join(context).strip(), time_dict # does not include query, just context 
    
    def prompt_formatter(self, query: str, context: str) -> str: 
        """ 
        function to format prompt 
        """   
        # prompt = self.base_prompt  
        # prompt += INSTRUCTIONS 

        sys_instructions = self.base_prompt + base_context.INSTRUCTIONS 
        self.llm.add_sys_instructions(sys_instructions) # adds context as system message 

        prompt = ""
        prompt += f"Here is the user query: {query}"    
        prompt += f"\n\n\nHere is some provided context to help you answer:\n\n\n\n {context}\n\n\n\n" 
        prompt += f"Now, using the context above, please answer the following question: {query}"
        
        return prompt 


    def answer(self, query: str, return_docs=True, model="gpt-4-0125-preview", temperature=0.3, **kwargs) -> str:

        # "gpt-3.5-turbo-0125" 

        """ 
        function to answer user query with basic rag model 
        """    

        # prepare context 
        if return_docs: 
            context, time_dict, docs = self.prepare_context(query, return_docs=return_docs) 
        else:
            context, time_dict, docs = self.prepare_context(query)  

        # format prompt with context 
        prompt = self.prompt_formatter(query, context)  

        # call llm
        answer = self.llm.answer(prompt, model=model, temperature=temperature, **kwargs) 

        if return_docs: 
            return answer, docs 
        else:
            return answer
        
    
    

class Retriever: 
    
    """
    retrieves docs from knowledge base 
    """ 

    def __init__(self):

        self.pc = Pinecone(api_key=st.secrets['PINECONE_SERVERLESS_KEY'])
        self.index = self.pc.Index("dotbot-serverless-index")    

    def query_pinecone_index(self, vector: list[float], top_k=7, namespace='original'):
        
        """
        Queries a Pinecone index with a given vector.

        Parameters:
        - vector: The query vector as a list of floats.
        - top_k: Number of top similar items to retrieve.
        - include_values: Whether to include the values in the response.
        - api_key: Your Pinecone API key.
        - index_host: The Index Host URL for your Pinecone index.

        Returns:
        - The response from the Pinecone index query as a string.
        """ 

        response = self.index.query(
            vector=vector,
            top_k=top_k,
            include_values=True, 
            include_metadata=True, 
            namespace=namespace
        )
        
        return response 
    
    def embed_and_retrieve(self, query: str, top_k=7, namespace='original') -> dict: 
        """
        function to embed and retrieve docs 
        """ 

        # get embedding 
        gpt = GPT()
        embedding = gpt.embed(query) 

        # retrieve docs 
        docs = self.query_pinecone_index(vector=embedding, top_k=top_k, namespace=namespace)  

        return docs

    