import streamlit as st

from agents.sql import SQLAgent
from rag import RAG 


class AI: 

    def __init__(self): 

        pass 

    def answer(self, query: str, agent: str, model: str, return_docs=True, csv_output=False) -> str:  

        assert agent in ['sql', 'base'], st.error(f"Agent {agent} not yet available")

        if agent == 'sql': 
            ai = SQLAgent() 
            ans, docs = ai.answer(query, return_docs=return_docs, return_csv=csv_output)   
            if not csv_output:
                return f"**({agent.lower()} agent)** " + ans, docs 
            else:
                return ans, docs
        elif agent == 'base': 
            ai = RAG() 
            ans, docs = ai.answer(query, model=model, return_docs=return_docs) 
            return f"**({agent.lower()} agent)** " + ans, docs
        else: 
            raise ValueError(f"Agent {agent} not found") 
            return None