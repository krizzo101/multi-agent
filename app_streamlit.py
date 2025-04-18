import logging
import sys
import os
from pathlib import Path

# Explicitly create and set permissions for the log file
log_file = "global.log"
try:
    # Make sure the file exists with write permissions
    Path(log_file).touch(exist_ok=True)
    os.chmod(log_file, 0o666)  # Set read/write permissions for all users
    print(f"Created/verified log file: {log_file}")
except Exception as e:
    print(f"Error creating log file: {str(e)}")

# Make sure the log directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging with less verbose output and proper flush
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        logging.FileHandler(log_file, mode='a', encoding='utf-8')
    ]
)

# Force immediate log flush
class ImmediateFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Replace the standard file handler with our immediate-flush version
for i, handler in enumerate(logging.root.handlers):
    if isinstance(handler, logging.FileHandler) and not isinstance(handler, ImmediateFileHandler):
        # Replace with immediate handler
        new_handler = ImmediateFileHandler(handler.baseFilename, mode=handler.mode, encoding=handler.encoding)
        new_handler.setFormatter(handler.formatter)
        new_handler.setLevel(handler.level)
        logging.root.handlers[i] = new_handler

# Set specific loggers to higher levels to reduce noise
logging.getLogger("src.templates").setLevel(logging.WARNING)
logging.getLogger("src.prompt").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("Starting Streamlit application")

import os
import streamlit as st
import requests
from typing import List, Dict
from dotenv import load_dotenv
import time

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
        logger.info(f"Sending request to API: {prompt[:50]}...")
        
        # Check if API is available first
        try:
            health_response = requests.get(f"{API_URL}/health", timeout=3)
            if health_response.status_code != 200:
                logger.error(f"API health check failed: {health_response.status_code}")
                return "Error: API service is not responding properly. Please check if the backend is running."
        except requests.exceptions.RequestException as e:
            logger.error(f"API health check failed: {str(e)}")
            return "Error: Cannot connect to the API service. Please make sure the backend server is running."
        
        # Add a timeout to prevent hanging
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/agent/chat",
            json={"query": prompt},
            timeout=20  # 20 second timeout - reduced from 30
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Request completed in {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json().get("response", "Sorry, I couldn't process that request.")
            logger.info(f"Got successful response of length {len(result)}")
            return result
        else:
            error_msg = f"Error: {response.status_code} - {response.text}"
            logger.error(f"API error: {error_msg}")
            return error_msg
    except requests.exceptions.Timeout:
        logger.error("Request timed out. The server took too long to respond.")
        return "Sorry, the request timed out. The server might be busy or processing a complex query. Please try again with a simpler query."
    except requests.exceptions.ConnectionError:
        logger.error("Connection error. Could not connect to the API.")
        return "Error: Could not connect to the API server. Please check if the backend service is running."
    except Exception as e:
        logger.error(f"Exception while getting agent response: {str(e)}", exc_info=True)
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
        logger.info(f"User input: {prompt[:50]}...")
        # Add user message to chat history
        add_message("user", prompt)
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Add a timeout context to prevent hanging UI
                    response = get_agent_response(prompt)
                    # Check if response is empty or error
                    if not response:
                        st.error("The system encountered an error: Empty response received")
                    elif response.startswith("Error") or response.startswith("Sorry, the request timed out"):
                        st.error(response)
                    else:
                        st.markdown(response)
                        add_message("assistant", response)
                except Exception as e:
                    error_message = f"Error connecting to API: {str(e)}"
                    logger.error(error_message, exc_info=True)
                    st.error(error_message)
    
    # Sidebar with agent information and reset functionality
    with st.sidebar:
        st.header("Options")
        
        st.write("This chat system uses multiple specialized agents to answer your questions.")
        st.write("Each agent has different capabilities:")
        st.write("- **Reflection Agent**: Helps generate and refine detailed information")
        st.write("- **Planning Agent**: Assists with task planning and can use tools")
        
        # Add a status indicator for the API
        try:
            health_response = requests.get(f"{API_URL}/health", timeout=2)
            if health_response.status_code == 200:
                st.success("API Status: Online")
            else:
                st.error("API Status: Error")
        except:
            st.error("API Status: Offline")
        
        # Add a button to clear the chat
        if st.button("Clear Chat"):
            clear_chat()
            st.rerun()

# Force a log message to ensure logging is working
logger.info("Streamlit app ready to serve requests")

# Run the app
if __name__ == "__main__":
    main()