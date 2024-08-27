import os
import base64
import re
import json

import streamlit as st
import openai
from openai import AssistantEventHandler
from tools import TOOL_MAP
from typing_extensions import override
from dotenv import load_dotenv
import streamlit_authenticator as stauth

# Perplexity
#from openai import OpenAI

def str_to_bool(str_input):
    if not isinstance(str_input, str):
        return False
    return str_input.lower() == "true"


load_dotenv()

# Add this line near other environment variable definitions
authentication_required = str_to_bool(os.environ.get("AUTHENTICATION_REQUIRED", "False"))


authenticator = None
if authentication_required and "credentials" in st.secrets:
    try:
        authenticator = stauth.Authenticate(
            st.secrets["credentials"],
            st.secrets["cookie"]["name"],
            st.secrets["cookie"]["key"],
            st.secrets["cookie"]["expiry_days"],
        )
    except Exception as e:
        st.error(f"Error initializing authenticator: {str(e)}")
        
        



# Load environment variables
# openai_api_key = os.environ.get("OPENAI_API_KEY")

# Perplexity key
perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")

instructions = os.environ.get("RUN_INSTRUCTIONS", "")


client = None

    #client = openai.OpenAI(api_key=openai_api_key)
client = openai.OpenAI(api_key=perplexity_api_key, base_url="https://api.perplexity.ai")




# Add custom CSS for RTL support
def add_custom_css():
    st.markdown("""
    <style>
    .stTextInput input {
        direction: rtl;
        text-align: right;
    }
    .stChatMessage {
        direction: rtl;
        text-align: right;
    }
    .stChatMessageContent {
        direction: rtl;
        text-align: right;
    }
    .centered-text {
        text-align: center;
        direction: rtl;
    }
    </style>
    """, unsafe_allow_html=True)


def get_perplexity_response(user_input):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-chat	",  # or another appropriate model
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_input}
            ],
            stream=True
        )
        return response
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None    
    
    
    
    
    



def create_thread(content, file):
    return client.beta.threads.create()


def create_message(thread, content, file):
    attachments = []
    if file is not None:
        attachments.append(
            {"file_id": file.id, "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]}
        )
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=content, attachments=attachments
    )


def create_file_link(file_name, file_id):
    content = client.files.content(file_id)
    content_type = content.response.headers["content-type"]
    b64 = base64.b64encode(content.text.encode(content.encoding)).decode()
    link_tag = f'<a href="data:{content_type};base64,{b64}" download="{file_name}">Download Link</a>'
    return link_tag


def format_annotation(text):
    citations = []
    text_value = text.value
    for index, annotation in enumerate(text.annotations):
        text_value = text_value.replace(annotation.text, f" [{index}]")

        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(
                f"[{index}] {file_citation.quote} from {cited_file.filename}"
            )
        elif file_path := getattr(annotation, "file_path", None):
            link_tag = create_file_link(
                annotation.text.split("/")[-1],
                file_path.file_id,
            )
            text_value = re.sub(r"\[(.*?)\]\s*\(\s*(.*?)\s*\)", link_tag, text_value)
    text_value += "\n\n" + "\n".join(citations)
    return text_value


#def run_stream(user_input, file, selected_assistant_id):
#    if "thread" not in st.session_state:
#        st.session_state.thread = create_thread(user_input, file)
#    create_message(st.session_state.thread, user_input, file)
#    with client.beta.threads.runs.stream(
#        thread_id=st.session_state.thread.id,
#        assistant_id=selected_assistant_id,
#        event_handler=EventHandler(),
#    ) as stream:
#        stream.until_done()

def run_stream(user_input, file, selected_assistant_id):
    with st.chat_message("Assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        for chunk in get_perplexity_response(user_input):
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
    
    st.session_state.chat_log.append({"name": "assistant", "msg": full_response})
    




def render_chat():
    for chat in st.session_state.chat_log:
        with st.chat_message(chat["name"]):
            st.markdown(f'<div dir="rtl">{chat["msg"]}</div>', unsafe_allow_html=True)


if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

if "in_progress" not in st.session_state:
    st.session_state.in_progress = False


def disable_form():
    st.session_state.in_progress = True


#def login():
#    if st.session_state["authentication_status"] is False:
#        st.error("Username/password is incorrect")
#    elif st.session_state["authentication_status"] is None:
#        st.warning("Please enter your username and password")

def login():
    if "authentication_status" not in st.session_state:
        st.warning("Authentication is not set up properly.")
    elif st.session_state["authentication_status"] is False:
        st.error("Username/password is incorrect")
    elif st.session_state["authentication_status"] is None:
        st.warning("Please enter your username and password")

def reset_chat():
    st.session_state.chat_log = []
    st.session_state.in_progress = False

def load_chat_screen(assistant_title):
    add_custom_css()  # Add RTL CSS

    # Add sidebar with image and text
    with st.sidebar:
        st.image("Fby2Jxqn_400x400.jpg", use_column_width=True)
        st.markdown("""
        <div class="centered-text">
        <p>Experimental AI-based bot for political/historical fact-checking.</p>
        <p>בוט נסיוני מבוסס בינה מלאכותית לבדיקת עובדות בתחום הפוליטי/היסטורי.</p>
        <p>Developed and maintained by civax</p>
        </div>
        """, unsafe_allow_html=True)

    st.title(assistant_title if assistant_title else "")

    user_msg = st.chat_input(
        "טקסט לבדיקה", on_submit=disable_form, disabled=st.session_state.in_progress
    )

    if user_msg:
        render_chat()
        with st.chat_message("user"):
            st.markdown(f'<div dir="rtl">{user_msg}</div>', unsafe_allow_html=True)
        st.session_state.chat_log.append({"name": "user", "msg": user_msg})

        run_stream(user_msg, None, None)
        st.session_state.in_progress = False
        st.rerun()

    render_chat()


def main():
    # Simplify this function to use a single assistant title
    assistant_title = os.environ.get("ASSISTANT_TITLE", "AI Fact-Checker")

    if authentication_required:
        if "credentials" in st.secrets and "authenticator" in globals():
            authenticator.login()
            if not st.session_state["authentication_status"]:
                login()
                return
            else:
                authenticator.logout(location="sidebar")
        else:
            st.error("Authentication is required but not properly configured.")
            return

    load_chat_screen(assistant_title)


if __name__ == "__main__":
    main()
