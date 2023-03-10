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


st.set_page_config(
    page_title="DotBot",
    page_icon= "🤖",
    #layout= "wide",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items = None
)  

for k in ['q', 'current_query', 'previous_queries']:  
    if k not in st.session_state: 
        if k == 'previous_queries': 
            st.session_state[k] = [] 
        else:
            st.session_state[k] = ''

def show_chat_history():
    if 'convo' in st.session_state:  
        with st.expander("Chat History"):
            for c in st.session_state['convo']: 
                if c['role'] == 'user': 
                    st.caption(f"**You**: {c['query']}") 
                if c['role'] == 'assistant': 
                    st.markdown(f"**DB**: {c['content']}") 
            blank()
            refresh_chat = st.button("Refresh Chat")
            if refresh_chat: 
                del st.session_state['convo']  
                del st.session_state['current_query']
                st.experimental_rerun() 

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


master_password = st.sidebar.text_input("Password / PIN")   
chat_personality = st.sidebar.selectbox("Chat Personality", ['standard'] + sorted(personalities))
st.sidebar.text('')
st.sidebar.text('')
st.sidebar.image('Untitled.png', width=225)

if helpers.password_authenticate(master_password): 
    st.session_state['valid_password'] = True 
else:  
    st.warning("Invalid credentials – use sidebar to enter valid PIN or password")
    st.session_state['valid_password'] = False 


st.header(":red[D]ot:red[B]ot 🦑")  

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
        query = st.text_input("Input Query Here", placeholder='ask me anything...')   
        #personality = st.selectbox("Personality", ['standard'] + sorted(personalities))
        ask = st.form_submit_button("Ask DB") 
    
    # def clear_query():   
    #     #st.session_state.previous_queries.append(st.session_state.q)
    #     st.session_state.current_query = st.session_state.q   
    #     st.session_state.q = '' 

    # query = st.text_input("", placeholder='Ask me anything...', key='q', on_change=clear_query)  

    # cq = st.session_state.get('current_query', '')
    # if (len(cq) > 2) and (cq not in st.session_state['previous_queries']):    
    if ask: 
        #query = st.session_state['current_query']

        if st.session_state['valid_password']: 

            if len(query) > 1: 
                st.caption(f"**You**: {query}")   
                with st.spinner("Computing response"): 

                    ai = AI(index) 

                    #docs = ai.embed_and_get_closest_docs(query)  
                    prompt, docs = ai.construct_prompt(query, return_docs=True, personality=chat_personality)  

                    if 'convo' in st.session_state:  
                        answer = ai.answer(prompt, history=st.session_state['convo'])  
                    else:
                        answer = ai.answer(prompt)

                #st.markdown("**Answer**: i don't know yet :(")  
                
    #            with st.expander("Documents"):  
    #                
    #                has_attachments = False 
    ##                with st.expander("1"): 
    ##                    blank()
    #                st.write(docs)  
                        
                if chat_personality.lower() != 'standard':
                    st.markdown(f"**DB ({chat_personality})**: {answer}")     
                else: 
                    st.markdown(f"**DB**: {answer}")

                blank() 
                blank()
                show_chat_history()
                #blank() 
                st.markdown("----")   
                st.markdown("**References** – DotBot used these to come up with the answer above")   
                if 'convo' not in st.session_state: 
                    st.session_state['convo'] = [{'role': 'user', 'query': query, 'content': prompt}, 
                                                {'role': 'assistant', 'content': answer}]  
                else: 
                    st.session_state['convo'].append({'role': 'user', 'query': query, 'content': prompt}) 
                    st.session_state['convo'].append({'role': 'assistant', 'content': answer}) 

                blank()
                MAX_DOCS_TO_SHOW = 5
                i = 1
                for d in docs['matches']:  
                    if i > 5: 
                        break 
                        
                    with st.expander(f"**{i}**. {d['metadata'].get('topic', 'no topic listed')} -- **{round(d['score'] * 100, 2)}%** match"): # Document {i} --
                        st.markdown(f"**Content**: {d['metadata']['text']}", unsafe_allow_html=True) 
                        st.markdown(f"**Tags**: {', '.join(d['metadata']['tags']) if len(d['metadata']['tags']) > 0 else 'no tags submitted'}") 
                        st.markdown(f"**Submitted by**: {d['metadata']['submitted_by']} {d['metadata'].get('date', '')}")
                        i += 1
                for d in docs['matches']: 
                    if d['metadata'].get('attachments', False):  
                        # grab the s3 path and make call 
                        
                        # display as download button  
                        #st.write(d['metadata']) 
                        blank()
                        
    #                        st.download_button(label=d[''], 
    #                            data=f.read(),
    #                            file_name="pandas-clean-id-column.pdf",
    #                            mime=check_file_type(f))
                st.markdown('---') 
                with st.expander("Prompt"):
                    st.write(prompt)   

                blank() 
                blank()
                refresh_chat_button = st.button("Refresh Chat ") 
                if refresh_chat_button:  
                    del st.session_state['convo']  
                    del st.session_state['current_query']
                    st.experimental_rerun()
            

        else: 
            st.error("Invalid credentials – please use sidebar to enter a valid password")
    
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

            if st.session_state['valid_password']:   

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
        
        n_results = st.slider("N most recent", min_value=5, max_value=50, value=5) 
        
        recent_uploads_search = st.button("Seach") 
        
    if recent_uploads_search:  
        if st.session_state['valid_password']:
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

        if st.session_state['valid_password']:
        
            with st.spinner("Finding content"):
                ai = AI(index) 
                docs = ai.embed_and_get_closest_docs(content_query) 
            
            i = 1
            for d in docs['matches']:  
                st.markdown(f"<u>**:blue[Document {i}]**</u>", unsafe_allow_html=True) #  - {d['metadata'].get('topic', '')}
                st.markdown(f"**Topic name**: {d['metadata'].get('topic', '')}" )
                st.markdown(f"**Content ID**: (copy ID below to use in modify tab)" ) #--> **:red[{d['id']}]**  
                st.code(f"{d['id']}", None)
                st.markdown(f"Submitted by: {d['metadata']['submitted_by']}")
                with st.expander(f"document {i} text"):
                    st.markdown(f"{d['metadata']['text']}\n\n", unsafe_allow_html=True)  
                    i += 1 
                blank()

                
with modify_tab:  
        
    with st.form('modify-form'):   
        with st.expander("Delete by Content ID"):
            content_id = st.text_input("Content ID", help="get this from the 'view content' tab")   
        
        with st.expander("Bulk Delete"): 
            topic_name = st.text_input("Delete by topic name")
        
        st.markdown("------")
        modify = st.form_submit_button("Make modification") 
        
    if modify: 
                
        modification = 'Delete' # remove this... 

        content_id_delete = len(content_id) > 1 
        topic_delete = len(topic_name) > 1

        if st.session_state['valid_password']:  
            
            if modification == 'Delete': 
                st.info("Deleting content...") 
                if content_id_delete:  
                    st.info("Deleting by content ID")
                    index.delete(ids=[content_id.strip()])  
                    st.success("Content has been removed")   

                if topic_delete: 
                    st.info("Bulk delete by topic name") 
                    #metadata['topic'] = text_topic.lower() 
                    index.delete(
                        filter={
                            "topic": {"$eq": topic_name.lower().strip()}                        }
                    )
                    st.success("Content has been removed") 
            
            if modification == 'View': 
                st.info("Section under construction")
                
        else: 
            st.error("Invalid Password")