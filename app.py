import streamlit as st     
import pandas as pd 
from io import StringIO
from datetime import datetime 
import time

from generate_response import AI  

from miniDDB import miniDDB, format_floats
from agents import meta
from rag import RAG 
from vector_db import PineconeDB
import helpers 
# from doc_parsing import parse_docx, parse_pdf, parse_txt, check_file_type, split_docs 
from aws_connect import S3, pull_content_requests


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

def get_content_requests(): 
    s3 = S3() 
    conn = s3.s3 

    reqs = pull_content_requests(conn) 

    return reqs  

 

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# ----- APP -----   

MODES = ['base', 'SQL'] 

master_password = st.sidebar.text_input("Password / PIN", type='password')   
chat_agent = st.sidebar.selectbox("Mode", MODES)  
st.sidebar.text('')
st.sidebar.text('')
# model_choice = st.sidebar.selectbox("Model", ['GPT 3.5', 'GPT 4'], help="""
# GPT 4 is the most sophisticated model in the world, but takes slightly longer to respond. Use it for more complex questions.""") 

#model = "gpt-3.5-turbo-0125" if model_choice == 'GPT 3.5' else "gpt-4-0125-preview" 

model = "gpt-4-0125-preview" 

st.sidebar.image('Untitled.png', width=225)  
with st.sidebar.expander("**Disclaimer**"): 
    st.markdown("""Not all information generated by DotBot can be guarenteed to be 
                factually accurate – always consult with official sources for important information 
                and use the 'Content Request' tab to report any inaccuracies or request new information to 
                 be inputted into the system.""")

authed = helpers.password_authenticate(master_password) 
valid_user = authed['valid'] 
admin_user = authed['admin']
 
if valid_user:   
    st.session_state['valid_password'] = True  

    if admin_user:
        st.session_state['admin'] = True 
    else: 
        st.session_state['admin'] = False
else:  
    st.warning("Invalid credentials – use sidebar to enter valid PIN or password")
    st.session_state['valid_password'] = False 


st.header(":red[D]ot:red[B]ot")  # 🦑

# --- HIDE STREAMLIT STYLE ---
hide_st_style = """
            <style>
            MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
#st.markdown(hide_st_style, unsafe_allow_html=True)

if st.session_state.get('admin'):
    ask_tab, request_tab, input_tab, view_content_tab, modify_tab = st.tabs(['ChatDB', 
                                                                             'Content Request', 
                                                                             'Submit Content', 
                                                                             'View Content', 
                                                                             'Modify Content']) 
else: 
    ask_tab, request_tab = st.tabs(['ChatDB', 'Content Request'])

with ask_tab:     
    
    csv_output = False
    with st.form(key='chat-form'):
        st.caption(f"Using **{chat_agent}** agent")
        query = st.text_input("Input Query Here", placeholder='ask me anything...')     
        if chat_agent == 'SQL': 
            csv_output = st.checkbox("Output csv", help="check this box if you want the output to be in csv format") 

        blank()
        ask = st.form_submit_button("Ask DB") 
  
    if ask:  


        if not st.session_state['valid_password']:    
            st.error("Invalid credentials – please use sidebar to enter a valid password") 
            st.stop()
        
        if len(query) > 1: 
            with st.spinner("Computing response"):    

                query = helpers.standardize_site_code(query)

                start = time.time()
                agent = meta.AI() 
                ans, docs = agent.answer(query=query, 
                                         agent=chat_agent.lower(), 
                                         model=model, 
                                         return_docs=True, 
                                         csv_output=csv_output)   
                end = time.time() 
                if csv_output:  
                    # ans is a csv string, turn it into a dataframe
                    csv_file_like_object = StringIO(ans)
                    df = pd.read_csv(csv_file_like_object) 
                    st.markdown("Here are the results in csv format. Use the button below to download the data.") 
                    st.download_button(label="Download Data",
                                        data=ans,
                                        file_name="dotbot_output.csv",
                                        mime="text/csv")
                    st.dataframe(df) 
                     
                else:
                    st.markdown(ans)    

                ddb_item = {
                    "timestamp": datetime.now().isoformat(),
                    "message": str(query), 
                    "response": str(ans), 
                    "response_time": end - start,
                    "interface": 'app',
                    'file_output': csv_output,
                    "success": True
                } 

                # save to ddb  
                ddb_item = format_floats(ddb_item)
                ddb = miniDDB(table_name='dotbot-logs') 
                ddb.add_item(item=ddb_item, auto_id=True)


 

            blank() 
            st.markdown('------')  
            if chat_agent == 'base': 
                st.caption("Context used to answer the question. Results ordered by relevance.")
                MAX_DOCS_TO_SHOW = 5
                i = 1
                for d in docs['matches']:   
                    if i > 5: 
                        break 
                        
                    with st.expander(f"Source **{i}**"): # Document {i} --
                        st.markdown(f"**Content**: {d['metadata']['text']}", unsafe_allow_html=True) 
                        st.markdown(f"**Tags**: {', '.join(d['metadata'].get('tags')) if len(d['metadata'].get('tags', [])) > 0 else 'None'}") 
                        i += 1 
            
            if chat_agent == 'SQL': 
                with st.expander("SQL Examples"): 
                    st.markdown(docs, unsafe_allow_html=True)
                
                

            blank() 
            blank()
            refresh_chat_button = st.button("Refresh Chat ") 
            if refresh_chat_button:  
                del st.session_state['convo']  
                del st.session_state['current_query']
                st.experimental_rerun()
            

    
            

with request_tab: 
    with st.form(key='request-form'):

        new_content_request = st.text_input("Describe what you'd like to see in DotBot") 
        request_name = st.text_input("Your name")
        req = st.form_submit_button("Request") 

    if req:   

        request_id = helpers.get_id()

        s3 = S3()  
        s3.upload_file_to_s3(
                            data={'name': request_name, 'request': new_content_request}, 
                            path='requests/', 
                            fname=request_id, 
                            file_type='pkl'
                        ) 
        
        st.success("Request successfully submitted!")

if st.session_state.get('admin'):    
    with input_tab:  
        # rizz
        with st.form('info-submit-form'): 
            agent_select = st.selectbox("Agent", ['base', 'SQL', 'accounting'], help="Choose the agent you'd like to feed information to") 
            context_summary = st.text_input("Provide some background detail on what the content below is for", help="The topic of the content you're submitting") 
            context_full = st.text_area("Content", help="The content you're submitting")  
            st.markdown('------') 
            submitted_by_name = st.text_input("Your name")
            submit_info = st.form_submit_button("Submit Content") 

        if submit_info: 
            if not submitted_by_name: 
                st.error("Please input your name")
                st.stop() 
            
            if not context_summary:
                st.error("Please input a summary of the content you're submitting")
                st.stop() 
            
            if not context_full:
                st.error("Please input the content you're submitting")
                st.stop() 

            agent_select = agent_select.lower()  

            # pinecone vector db namespace 
            if agent_select == 'base': 
                namespace = 'original' 
            elif agent_select == 'sql': 
                namespace = 'REDLINE-SQL' 
            elif agent_select == 'accounting': 
                namespace = 'accounting' 
            else: 
                namespace = 'original'    

            st.caption(f"namespace: **{namespace}**")

            if agent_select == 'sql': 
                context_full = '```\n' + context_full + '\n```' 
            
            concat_context = context_summary + "\n\n" + context_full
            
            vdb = PineconeDB()   
            success = vdb.upsert(input_text=concat_context, 
                              namespace=namespace, 
                              submitted_by=submitted_by_name) 
            if success: 
                st.success("Content successfully submitted") 
            else:
                st.error("There was a problem submitting your content")

    # with input_tab: 
    #     with st.form(key='submit-form'):  
            
    #         st.caption("1. Create or upload content")
    #         upload_type = st.selectbox("Upload type", ['choose an option', 'write custom text', 'upload document'], help="")   
    #         request_id = st.text_input("Request ID (if necessary)", help="If addressing a previously submitted content request, use this box to input the request id (get this from view content -> content requests)")
    #         blank() 
            
    #         with st.expander("Text"):  
    #             text_topic = st.text_input("Topic ")
    #             user_text = st.text_area("Content", placeholder="Tell me about something")   
    #             chunkify_text = st.checkbox("Break content into chunks", False, help="check this if you're inputting a lot of text (3/4 of a page or more)")
                
    #         with st.expander("Document"):   
                
    #             doc_topic = st.text_input("Topic")
    #             user_doc = st.file_uploader("Upload document (.pdf, .docx, and .txt supported)", accept_multiple_files=False) 
    #             chunkify = st.checkbox("Break content into chunks", True, help="unchecking this box will feed the entire piece of content in as one rather than breaking it into chunks")
            
    #         st.markdown('----') 
    #         st.caption("2. Add supplementary information (optional)")
    #         tags = st.multiselect("Select tags (optional)", [] + sorted([x.lower() for x in tag_options]), help="Tags will allow for filtering. For example, if you're submitting content specific to RD001, include the 'RD001' tag to help DB match to RD001 when a user asks a question about that site") 
    #         attachments = st.file_uploader("Add attachments (optional)", accept_multiple_files=False, help="Include any attachments that serve as a good reference for the content you're submitting. \n\n**All file types accepted**")
            
    #         st.markdown("----") 
    #         st.caption("3. Input credentials")
    #         name = st.text_input("Name") 
    #         password = st.text_input("Password")
    #         submit = st.form_submit_button("Submit")  
            
    #     if submit:   

    #         request_id = request_id.strip()
            
    #         # todo: check for required info   
    #         text_upload = upload_type == 'write custom text' 
    #         doc_upload = upload_type == 'upload document'   
    #         from_request = request_id != ''
            
    #         upload_check = upload_type.lower() != 'choose an option'  
            
    #         if not upload_check: 
    #             st.error("Please choose an upload option")
            
    #         if text_upload: 
    #             topic_check = text_topic != '' 
    #             content_check = user_text != '' 
            
    #         if doc_upload: 
    #             topic_check = doc_topic != '' 
    #             content_check = user_doc is not None  
                
    #         if not (topic_check & content_check): 
    #             st.error("Make sure you inputted a **topic** and **content** to the system")
                
    #         name_check = name != ''  
    #         first_and_last_check = len(name.split()) >= 2
            
    #         if not first_and_last_check: 
    #             st.error("Please submit a first **and** last name")
            
    #         all_checks_passed = upload_check & topic_check & content_check & name_check & first_and_last_check
            
    #         if all_checks_passed:

    #             if st.session_state['valid_password']:   

    #                 # generate content id 
    #                 content_id = helpers.get_id()   

    #                 # instantiate embedding class
    #                 em = Embedder(index)   
    #                 s3 = S3() 


    #                 metadata = {
    #                     'text_upload': text_upload, 
    #                     'doc_upload': doc_upload, 
    #                     'tags': tags, 
    #                     'submitted_by': name, 
    #                     'date': str(np.datetime64('today')), 
    #                     'timestamp': str(np.datetime64('now'))
    #                 }


    #                 if attachments is not None: 

    #                     attachment_data = {
    #                         'content_id': content_id, 
    #                         'file_type': check_file_type(attachments), 
    #                         'contents': attachments
    #                     } 


    #                     s3_path = f"attachments/{content_id}.pkl" 

    #                     metadata['attachments'] = True  
    #                     metadata['attachments_s3_path'] = s3_path   

    #                     # upload attachments to s3 
    #                     s3.upload_file_to_s3(
    #                         data=attachment_data, 
    #                         path='attachments/', 
    #                         fname=content_id, 
    #                         file_type='pkl'
    #                     )

    #                     st.success("Attachments saved")

    #                 else: 
    #                     metadata['attachments'] = False 


    #                     #st.write(dir(f))
    #     #                    pdf_display = f'<iframe src="data:application/pdf;base64,{f.read()}" width="800" height="800" type="application/pdf"></iframe>'
    #     #                    st.markdown(pdf_display, unsafe_allow_html=True) 

    #     #                    st.download_button(label="Download PDF Tutorial", 
    #     #                        data=f.read(),
    #     #                        file_name="pandas-clean-id-column.pdf",
    #     #                        mime=check_file_type(f))

    #                 if text_upload:   


    #                     st.write("**Content**: ", user_text) 

    #                     metadata['topic'] = text_topic.lower()

    #                     user_text = f"The topic of this text is about: {text_topic}\n\n" + user_text

    #                     with st.spinner("Turning text into numbers..."):
    #                         if chunkify_text: 
    #                             chunks = split_docs(user_text)   

    #                             cid = content_id 
    #                             i = 1
    #                             for chunk in chunks:       

    #                                 user_text = f"The topic of this text is about: {doc_topic}\n\n" + chunk 
    #                                 em.embed_and_save(content_id=cid, text=user_text, metadata=metadata, aws=True)  
    #                                 cid = helpers.get_id()  

    #                                 st.success(f"saved chunk {i}")
    #                                 i +=1 

    #                         else:
    #                             # saves to pinecone AND s3
    #                             em.embed_and_save(content_id=content_id, text=user_text, metadata=metadata, aws=True) 
                        
                        
    #                     if from_request:
    #                         s3.upload_file_to_s3(
    #                             data={'done': True, 'metadata': metadata}, 
    #                             path='requests/completed-requests/', 
    #                             fname=request_id, 
    #                             file_type='pkl'
    #                         )

    #                     st.success("Success! Your input has been uploaded to the system")  

    #                 if doc_upload:   

    #                     metadata['topic'] = doc_topic.lower()

    #                     file_type = check_file_type(user_doc)
    #                     st.write(f"{file_type} document found") 
                        
    #                     doc_parsed = False
    #                     if file_type == 'text/plain': 
    #                         parsed = parse_txt(user_doc)   
    #                         doc_parsed = True
                        
    #                     if file_type == 'application/pdf': 
                            
    #                         parsed = parse_pdf(user_doc) 
    #                         doc_parsed = True
                        
    #                     if file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                            
    #                         parsed = parse_docx(user_doc) 
    #                         doc_parsed = True
                        
                        
    #                     if doc_parsed:
    #                         if chunkify:
    #                             chunks = split_docs(parsed)  

    #                             cid = content_id 
    #                             i = 1
    #                             for chunk in chunks:       

    #                                 user_text = f"The topic of this text is about: {doc_topic}\n\n" + chunk 
    #                                 em.embed_and_save(content_id=cid, text=user_text, metadata=metadata, aws=True)  
    #                                 cid = helpers.get_id()  

    #                                 st.success(f"saved chunk {i}")
    #                                 i +=1  

    #                             st.success("**Success**, entire document saved")

    #                         else:  

    #                             user_text = f"The topic of this text is about: {doc_topic}\n\n" + parsed

    #                             em.embed_and_save(content_id=content_id, text=user_text, metadata=metadata, aws=True) 
    #                             st.success("text embedded and saved")  

    #                     if from_request:
    #                         s3.upload_file_to_s3(
    #                             data={'done': True, 'metadata': metadata}, 
    #                             path='requests/completed-requests/', 
    #                             fname=request_id, 
    #                             file_type='pkl'
    #                         )
                                
                        

    #             else: 
    #                 st.error("Invalid password")
                
                
            
                
    with view_content_tab: 
        
    #    with st.form(key='-form'): 
        
        with st.expander("Search for Existing Content"):
            content_query = st.text_input("Search content") 

            search_content = st.button("Search")  
            
        with st.expander("Most Recent Uploads"): 
            
            n_results = st.slider("N most recent", min_value=5, max_value=50, value=5) 
            
            recent_uploads_search = st.button("Seach")  

        with st.expander("Content Requests"): 
            st.caption("Use this to browse open requests submitted from around the org")
            show_content_requests = st.button("Show")
            
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

        if show_content_requests:    

            with st.spinner("Pulling requests"):
                content_requests = get_content_requests() 
 
            st.markdown('-----') 
            
            current_date = None
            for r in content_requests:  
                name = r['name'] 
                if len(name) == 0: 
                    name = 'no name attached' 

                #st.markdown(f"**{name}**: <i>{r['request']}</i>", unsafe_allow_html=True)      
                if r['date'] != current_date:
                    st.caption(r['date']) 
                    current_date = r['date'] 

                st.markdown(f"**{name}**: <i>{r['request']}</i>", unsafe_allow_html=True) 
                st.code(f"{r['request_id']}", None)  
                st.caption("Copy the above signifier to use in the 'submit content tab' ")

                blank() 
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

