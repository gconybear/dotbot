from prompts import base_sql
from rag import RAG 
from tools.coding import Coder 
from llm import GPT

class SQLAgent: 

    def __init__(self): 
        
        self.llm = GPT()
        self.shortcuts = ['--sql', '-- sql']
        self.base_prompt = base_sql.sql_context
        self.agent_name = 'sql'
        self.agent_description = "SQL assistant. Use when the user has a question about SQL queries or general questions about accessing data from our redline database."

    def gather_query_examples(self, query: str) -> str:
        """
        takes in a query, embeds it, and retrieves relevant SQL examples from pinecone index 
        """ 

        rag_agent = RAG() 
        context, _ = rag_agent.prepare_context(query=query, namespace='REDLINE-SQL', top_k=8, MAX_LEN=1000)

        return context 
    
    def answer(self, query: str, return_docs=True) -> str: 
        
        """
        1. gather context via RAG 
        2. generate sql query with gpt4 and execute (Coder)
        3. analyze result with 3.5 turbo and return
        """  

        # gather context (vector retrieval)
        context = base_sql.sql_examples_context + self.gather_query_examples(query=query)  

        # generate sql query and execute (GPT-4 call + eval)
        c = Coder(context=[context, self.base_prompt], include_base_context=False) 
        res = c.answer(query) 

        # analyze result with 3.5 turbo and return (GPT-3.5 call)
        instructions = base_sql.analyzer_instructions + f"Q: {query}\n\n" + f"Result: {res.get('answer')}"
        self.llm.add_sys_instructions(instructions)
        answer = self.llm.answer(mssg=query, model="gpt-3.5-turbo-0125") 

        # for now, also include code used 
        answer += f"\n\nThe following code was used to generate the result: \n\n```python\n{res.get('code', '')}```\n\n"

        if return_docs: 
            return answer, context 
        else:
            return answer