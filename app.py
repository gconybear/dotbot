import streamlit as st     
import time 
import openai  
import pinecone
import numpy as np 

from ui_options import tag_options  
from embed import Embedder 
from generate_response import AI
import helpers 
from doc_parsing import parse_docx, parse_pdf, parse_txt, check_file_type, split_docs 
from aws_connect import S3
from LLM_PARAMS import personalities

##6d95b0 90b7d1 
textColor="#6d95b0" 
primaryColor="#6d95b0" 

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


ask_tab, input_tab, view_content_tab, modify_tab = st.tabs(['ChatDB', 'Submit Content', 'View Content', 'Modify Content'])

with ask_tab:    
    
    with st.form(key='chat-form'):
        #st.markdown("ChatDB")
        query = st.text_input("Input query", placeholder='Ask me anything...')   
        personality = st.selectbox("Personality", ['standard'] + sorted(personalities))
        ask = st.form_submit_button("ask")
    
    if ask:

        if len(query) > 1: 
            st.caption(f"**Query**: {query}")  
            with st.spinner("Computing response"): 

                ai = AI(index) 

                #docs = ai.embed_and_get_closest_docs(query)  
                prompt, docs = ai.construct_prompt(query, return_docs=True, personality=personality) 
                answer = ai.answer(prompt)

            #st.markdown("**Answer**: i don't know yet :(")  
            
#            with st.expander("Documents"):  
#                
#                has_attachments = False 
##                with st.expander("1"): 
##                    blank()
#                st.write(docs)  
                    
            
            st.markdown(f"**DB**: {answer}")   
            blank() 
            st.markdown("----") 
            i = 1
            for d in docs['matches']: 
                with st.expander(f"Document {i} -- {d['metadata'].get('topic', 'no topic listed')} -- **{round(d['score'] * 100, 2)}%** match"): 
                    st.markdown(f"**Content**: <i>{d['metadata']['text']}</i>", unsafe_allow_html=True) 
                    st.markdown(f"**Tags**: *{', '.join(d['metadata']['tags'])}*") 
                    st.markdown(f"**Submitted by**: *{d['metadata']['submitted_by']} {d['metadata'].get('date')}*")
                    i += 1
            for d in docs['matches']: 
                if d['metadata'].get('attachments', False):  
                    # grab the s3 path and make call 
                    
                    # display as download button  
                    st.write(d['metadata'])
                    
#                        st.download_button(label=d[''], 
#                            data=f.read(),
#                            file_name="pandas-clean-id-column.pdf",
#                            mime=check_file_type(f))
            with st.expander("Prompt"):
                st.write(prompt) 
    
with input_tab: 
    with st.form(key='submit-form'):  
        
        st.caption("1. Create or upload content")
        upload_type = st.selectbox("Upload type", ['choose an option', 'write custom text', 'upload document'], help="")  
        blank() 
        
        with st.expander("Text"):  
            text_topic = st.text_input("Topic ")
            user_text = st.text_area("Content", placeholder="Tell me about something")   
            chunkify_text = st.checkbox("Break content into chunks", False, help="check this if you're inputting a lot of text (3/4 of a page or more)")
            
        with st.expander("Document"):   
            
            doc_topic = st.text_input("Topic")
            user_doc = st.file_uploader("Upload document (.pdf, .docx, and .txt supported)", accept_multiple_files=False) 
            chunkify = st.checkbox("Break content into chunks", True, help="unchecking this box will feed the entire piece of content in as one rather than breaking it into chunks")
        
        st.markdown('----') 
        st.caption("2. Add supplementary information (optional)")
        tags = st.multiselect("Select tags (optional)", [] + sorted([x.lower() for x in tag_options]), help="Tags will allow for filtering. For example, if you're submitting content specific to RD001, include the 'RD001' tag to help DB match to RD001 when a user asks a question about that site") 
        attachments = st.file_uploader("Add attachments (optional)", accept_multiple_files=False, help="Include any attachments that serve as a good reference for the content you're submitting. \n\n**All file types accepted**")
        
        st.markdown("----") 
        st.caption("3. Input credentials")
        name = st.text_input("Name") 
        password = st.text_input("Password")
        submit = st.form_submit_button("Submit")  
        
    if submit:  
        
        # todo: check for required info   
        text_upload = upload_type == 'write custom text' 
        doc_upload = upload_type == 'upload document'  
        
        upload_check = upload_type.lower() != 'choose an option'  
        
        if not upload_check: 
            st.error("Please choose an upload option")
        
        if text_upload: 
            topic_check = text_topic != '' 
            content_check = user_text != '' 
        
        if doc_upload: 
            topic_check = doc_topic != '' 
            content_check = user_doc is not None  
            
        if not (topic_check & content_check): 
            st.error("Make sure you inputted a **topic** and **content** to the system")
            
        name_check = name != ''  
        first_and_last_check = len(name.split()) >= 2
        
        if not first_and_last_check: 
            st.error("Please submit a first **and** last name")
        
        all_checks_passed = upload_check & topic_check & content_check & name_check & first_and_last_check
         
        if all_checks_passed:
            password_valid = helpers.password_authenticate(password)

            if password_valid:   

                # generate content id 
                content_id = helpers.get_id()   

                # instantiate embedding class
                em = Embedder(index)   
                s3 = S3() 


                metadata = {
                    'text_upload': text_upload, 
                    'doc_upload': doc_upload, 
                    'tags': tags, 
                    'submitted_by': name, 
                    'date': str(np.datetime64('today')), 
                    'timestamp': str(np.datetime64('now'))
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

                    # upload attachments to s3 
                    s3.upload_file_to_s3(
                        data=attachment_data, 
                        path='attachments/', 
                        fname=content_id, 
                        file_type='pkl'
                    )

                    st.success("Attachments saved")

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
                    
                    doc_parsed = False
                    if file_type == 'text/plain': 
                        parsed = parse_txt(user_doc)   
                        doc_parsed = True
                    
                    if file_type == 'application/pdf': 
                        
                        parsed = parse_pdf(user_doc) 
                        doc_parsed = True
                    
                    if file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        
                        parsed = parse_docx(user_doc) 
                        doc_parsed = True
                    
                    
                    if doc_parsed:
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
            
            
        
             
with view_content_tab: 
    
#    with st.form(key='-form'): 
    
    with st.expander("Text Search"):
        content_query = st.text_input("Search content") 

        search_content = st.button("Search")  
        
    with st.expander("Most Recent Uploads"): 
        
        n_results = st.slider("N most recent", min_value=5, max_value=50, value=10) 
        
        recent_uploads_search = st.button("Seach") 
        
    if recent_uploads_search: 
        with st.spinner("Pulling recent uploads"): 
            s3 = S3().s3
            res = helpers.get_most_recent_db_submissions(s3, n_results) 
            
            i = 1
            for doc in res:  
                st.markdown(f"<u>**:blue[Document {i}]** - {doc['metadata'].get('topic', '')}</u>", unsafe_allow_html=True) 
                st.markdown(f"**Content ID** (copy ID below to use in modify tab)" ) #--> **:red[{d['id']}]**  
                st.code(f"{doc['content_id']}", None)
                st.markdown(f"Submitted by: {doc['metadata']['submitted_by']} | {doc['upload_time']}")
                with st.expander(f"document {i} text"): 
                    st.markdown(f"<i>{doc['content']}</i>", unsafe_allow_html=True)    
                i += 1 
                blank()
            
        
    if search_content:  
        
        with st.spinner("Finding content"):
            ai = AI(index) 
            docs = ai.embed_and_get_closest_docs(content_query) 
        
        i = 1
        for d in docs['matches']:  
            st.markdown(f"<u>**:blue[Document {i}]** - {d['metadata'].get('topic', '')}</u>", unsafe_allow_html=True) 
            st.markdown(f"**Content ID** (copy ID below to use in modify tab)" ) #--> **:red[{d['id']}]**  
            st.code(f"{d['id']}", None)
            st.markdown(f"Submitted by: {d['metadata']['submitted_by']}")
            with st.expander(f"document {i} text"):
                st.markdown(f"{d['metadata']['text']}\n\n", unsafe_allow_html=True)  
                i += 1 
            blank()

                
with modify_tab:  
        
    with st.form('modify-form'):  
        c1, c2 = st.columns(2)
        content_id = c1.text_input("Content ID", help="get this from the 'view content' tab")  
        modification = c2.selectbox("Modification", ['Delete', 'View']) 
        
        st.markdown("------")
        psswrd = st.text_input("Password")
        modify = st.form_submit_button("Make modification") 
        
    if modify: 
        
        password_valid = helpers.password_authenticate(psswrd)
        
        if password_valid:  
            
            if modification == 'Delete': 
                st.info("Deleting content...")
                index.delete(ids=[content_id.strip()])  
                st.success("Content has been removed")  
            
            if modification == 'View': 
                st.info("Section under construction")
                
        else: 
            st.error("Invalid Password")