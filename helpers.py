import uuid 
import streamlit as st 

def get_id(): return str(uuid.uuid4()) 

def password_authenticate(password): 
    
    if password == st.secrets['super_admin_password']: 
        return True 
    
    return False 