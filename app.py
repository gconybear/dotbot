import streamlit as st     
import time 
import openai  
import pinecone

from ui_options import tag_options  
from embed import Embedder 
from generate_response import AI
import helpers 
from doc_parsing import parse_docx, parse_pdf, parse_txt, check_file_type, split_docs 
from aws_connect import S3

##6d95b0 90b7d1 
textColor="#6d95b0" 
secondaryBackgroundColor="#e9eff2"

def blank(): return st.write('')  

@st.cache_resource(ttl=.5*60*60)
def get_index(): 
    
    openai.api_key = st.secrets['OPEN_AI_KEY']  

    pinecone.init(
        api_key=st.secrets['PINECONE_KEY'],
        environment=st.secrets['PINECONE_ENV']
    ) 
    
    index = pinecone.Index(st.secrets['PINECONE_INDEX']) 
    
    return index  

#def get_bot(index): 
#    
#    idx = get_index()
#    
#    return AI()

index = get_index() 

# ----- APP -----  


st.header("DotBot 🤖")  

#hide_st_style = """
#            <style>
#            #MainMenu {visibility: hidden;}
#            footer {visibility: hidden;}
#            header {visibility: hidden;}
#            </style>
#            """
#st.markdown(hide_st_style, unsafe_allow_html=True)


ask_tab, input_tab = st.tabs(['ChatDB', 'Submit Content'])

with ask_tab:    
    
    with st.form(key='chat-form'):
        #st.markdown("ChatDB")
        query = st.text_input("Input query", placeholder='Ask me anything...')  
        ask = st.form_submit_button("ask")
    
    if ask:

        if len(query) > 1: 
            st.caption(f"**Query**: {query}")  
            with st.spinner("Computing response"): 

                ai = AI(index) 

                #docs = ai.embed_and_get_closest_docs(query)  
                prompt, docs = ai.construct_prompt(query, return_docs=True) 
                answer = ai.answer(prompt)

            #st.markdown("**Answer**: i don't know yet :(") 
            with st.expander("Prompt"):
                st.write(prompt)  
            
            with st.expander("Documents"): 
                st.write(docs)
                
            st.write(answer)
    
with input_tab: 
    with st.form(key='submit-form'):  
        
        upload_type = st.radio("Upload type", ['write custom text', 'upload document'], help="")  
        blank() 
        
        with st.expander("Text"):  
            text_topic = st.text_input("Topic ")
            user_text = st.text_area("Content", placeholder="Tell me about something")   
            chunkify_text = st.checkbox("Break content into chunks", False, help="check this if you're inputting a lot of text (3/4 of a page or more)")
            
        with st.expander("Document"):   
            
            doc_topic = st.text_input("Topic")
            user_doc = st.file_uploader("Upload document (.pdf, .docx, and .txt supported)", accept_multiple_files=False) 
            chunkify = st.checkbox("Break content into chunks", True, help="unchecking this box will feed the entire piece of content in as one rather than breaking it into chunks")
            
        blank()
        tags = st.multiselect("Select tags (optional)", [] + sorted([x.lower() for x in tag_options]), help="Tags will allow for filtering. For example, if you're submitting content specific to RD001, include the 'RD001' tag to help DB match to RD001 when a user asks a question about that site") 
        attachments = st.file_uploader("Add attachments (optional)", accept_multiple_files=False, help="Include any attachments that serve as a good reference for the content you're submitting. \n\n**All file types accepted**")
        
        st.markdown("----")
        name = st.text_input("Name") 
        password = st.text_input("Password")
        submit = st.form_submit_button("Submit")  
        
    if submit:  
        
        # todo: check for required info 
        
        password_valid = helpers.password_authenticate(password)
        
        if password_valid:   
            
            # generate content id 
            content_id = helpers.get_id()   
            
            # instantiate embedding class
            em = Embedder(index)  
        
            text_upload = upload_type == 'write custom text' 
            doc_upload = upload_type == 'upload document'  
            
            metadata = {
                'text_upload': text_upload, 
                'doc_upload': doc_upload, 
                'tags': tags, 
                'submitted_by': name, 
            }
            
            
            
            if attachments is not None: 
                    
                attachment_data = {
                    'content_id': content_id, 
                    'file_type': check_file_type(attachments), 
                    'contents': attachments
                } 

                
                s3_path = f"attachments/{content_id}.pkl" 
                
                metadata['attachments'] = True  
                metadata['attachments_s3_path'] = s3_path  
            else: 
                metadata['attachments'] = False 
                
                
                #st.write(dir(f))
#                    pdf_display = f'<iframe src="data:application/pdf;base64,{f.read()}" width="800" height="800" type="application/pdf"></iframe>'
#                    st.markdown(pdf_display, unsafe_allow_html=True) 
                    
#                    st.download_button(label="Download PDF Tutorial", 
#                        data=f.read(),
#                        file_name="pandas-clean-id-column.pdf",
#                        mime=check_file_type(f))

            if text_upload:   
        
                
                st.write("**Content**: ", user_text) 
                
                metadata['topic'] = text_topic.lower()
                
                user_text = f"The topic of this text is about: {text_topic}\n\n" + user_text

                with st.spinner("Turning text into numbers..."):
                    if chunkify_text: 
                        chunks = split_docs(user_text)   
                        
                        cid = content_id 
                        i = 1
                        for chunk in chunks:       
                            
                            user_text = f"The topic of this text is about: {doc_topic}\n\n" + chunk 
                            em.embed_and_save(content_id=cid, text=user_text, metadata=metadata, aws=True)  
                            cid = helpers.get_id()  
                            
                            st.success(f"saved chunk {i}")
                            i +=1 
                        
                    else:
                        # saves to pinecone AND s3
                        em.embed_and_save(content_id=content_id, text=user_text, metadata=metadata, aws=True) 

                st.success("Success! Your input has been uploaded to the system")  
                
            if doc_upload:   
                
                metadata['topic'] = doc_topic.lower()
                 
                file_type = check_file_type(user_doc)
                st.write(f"{file_type} document found") 
                
                if file_type == 'text/plain': 
                    parsed = parse_txt(user_doc)   
                    
                    if chunkify:
                        chunks = split_docs(parsed)  
                        
                        cid = content_id 
                        i = 1
                        for chunk in chunks:       
                            
                            user_text = f"The topic of this text is about: {doc_topic}\n\n" + chunk 
                            em.embed_and_save(content_id=cid, text=user_text, metadata=metadata, aws=True)  
                            cid = helpers.get_id()  
                            
                            st.success(f"saved chunk {i}")
                            i +=1  
                        
                        st.success("**Success**, entire document saved")
                        
                    else:  
                        
                        user_text = f"The topic of this text is about: {doc_topic}\n\n" + parsed
                        
                        em.embed_and_save(content_id=content_id, text=user_text, metadata=metadata, aws=True) 
                        st.success("text embedded and saved")
                
        else: 
            st.error("Invalid password")
            
            
        
        
        
        