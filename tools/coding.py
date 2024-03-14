import json 

from llm import GPT
from prompts.base_code_context import BASE_CONTEXT


class Coder: 

    def __init__(self, context=[], include_base_context=True): # base_context=BASE_CONTEXT, additional_context=None  

        """
        additional context can be anything – e.g., we found sql examples and want to provide them  
        """ 

        # assert type(base_context) in [str, type(None)], "base context must be a string or None"
        # assert type(additional_context) in [str, type(None)], "additional context must be a string or None"  
        if include_base_context: 
            self.context = [BASE_CONTEXT] + context 
        else:
            self.context = context

        # self.instructions = base_context 
        # self.additional_context = additional_context
        

    def answer(self, query: str, model="gpt-4-0125-preview", temperature=0.3):  

        assert isinstance(query, str), f"query must be a string, got {query} of type {type(query)}"

        response_format={'type': 'json_object'} 

        # get gpt object 
        gpt = GPT()  
        for instructions in self.context:
             gpt.add_sys_instructions(instructions)           

        res = gpt.answer(mssg=query, 
                         model=model, 
                         temperature=temperature, 
                         response_format=response_format) 
        
        try: 
            res = json.loads(res)
            raw_code = res.get('code', '')  
            output_file = res.get('output_file', False)
            file_name = res.get('file_name', None) 
            comments = res.get('comments', '')
        except: 
            raw_code = ''  
            output_file = False
            file_name = None
            comments = ''
        try:
            namespace = {} 
            answer = exec(raw_code, namespace)  
            result = namespace.get('result', None)
        except Exception as e: 
            print(e)
            result = None

        return {
            "code": raw_code, 
            "answer": result, 
            "output_file": output_file,
            "file_name": file_name, 
            "comments": comments
        }
