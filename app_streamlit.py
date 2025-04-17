import logging

# Configure basic logging before importing anything
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("global.log", mode='a')
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting Streamlit application")

import os
import streamlit as st
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Set page configuration
st.set_page_config(
    page_title="Multi-Agent Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

def add_message(role: str, content: str):
    """Add a message to the chat history"""
    st.session_state.messages.append({"role": role, "content": content})

def clear_chat():
    """Clear the chat history"""
    logger.info("Clearing chat history")
    st.session_state.messages = []

def get_agent_response(prompt: str) -> str:
    """Get a response from the agent API"""
    try:
        logger.info(f"Sending request to API: {prompt[:100]}...")
        response = requests.post(
            f"{API_URL}/agent/chat",
            json={"query": prompt},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("response", "Sorry, I couldn't process that request.")
        else:
            error_msg = f"Error: {response.status_code} - {response.text}"
            logger.error(f"API error: {error_msg}")
            return error_msg
    except Exception as e:
        logger.error(f"Exception while getting agent response: {str(e)}")
        return f"Error connecting to API: {str(e)}"

# Main app UI
def main():
    """Main Streamlit UI"""
    # Title
    st.title("Multi-Agent Chat System")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        logger.info(f"User input: {prompt}")
        # Add user message to chat history
        add_message("user", prompt)
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = get_agent_response(prompt)
                    logger.info(f"Received response from API: {response[:100]}...")
                    st.markdown(response)
                    add_message("assistant", response)
                except Exception as e:
                    error_message = f"Error connecting to API: {str(e)}"
                    logger.error(error_message)
                    st.error(error_message)
    
    # Sidebar with agent information and reset functionality
    with st.sidebar:
        st.header("Options")
        
        st.write("This chat system uses multiple specialized agents to answer your questions.")
        st.write("Each agent has different capabilities:")
        st.write("- **Reflection Agent**: Helps generate and refine detailed information")
        st.write("- **Planning Agent**: Assists with task planning and can use tools")
        
        # Add a button to clear the chat
        if st.button("Clear Chat"):
            clear_chat()
            st.rerun()

# Run the app
if __name__ == "__main__":
    main()