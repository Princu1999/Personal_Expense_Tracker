import json
from datetime import datetime
import requests
import streamlit as st

# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_BASE_URL = "http://127.0.0.1:8000"
CHAT_API_URL = f"{API_BASE_URL}/chat"
CHAT_STREAM_API_URL = f"{API_BASE_URL}/chat/stream"
CONVERSATIONS_API_URL = f"{API_BASE_URL}/conversations"
LOGIN_API_URL = f"{API_BASE_URL}/auth/login"
REGISTER_API_URL = f"{API_BASE_URL}/auth/register"


# --------------------------------------------------
# Page configuration & Styling
# --------------------------------------------------

st.set_page_config(
    page_title="Personal Expense Assistant",
    page_icon="💰",
    layout="wide",
)

# Custom CSS for styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .user-badge {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .chat-header {
        font-size: 1.4rem;
        font-weight: 600;
        color: #212529;
        margin-bottom: 0.3rem;
    }
    .chat-subheader {
        font-size: 0.85rem;
        color: #6c757d;
        margin-bottom: 1rem;
    }
    .suggestion-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Session State Initialization
# --------------------------------------------------

if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

if "current_thread_title" not in st.session_state:
    st.session_state.current_thread_title = "New Conversation"

if "conversations" not in st.session_state:
    st.session_state.conversations = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "initial_loaded" not in st.session_state:
    st.session_state.initial_loaded = False


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def get_auth_headers():
    if st.session_state.auth_token:
        return {"Authorization": f"Bearer {st.session_state.auth_token}"}
    return {}


def format_relative_time(dt_str: str) -> str:
    """Format ISO timestamp into friendly relative time."""
    if not dt_str:
        return ""
    try:
        # Handle formats with or without Z/offset
        clean_str = dt_str.replace("Z", "+00:00")
        if "+" not in clean_str and "-" in clean_str[10:]:
            dt = datetime.fromisoformat(clean_str)
        else:
            dt = datetime.fromisoformat(clean_str)
        
        now = datetime.utcnow()
        # Compare as naive utc datetimes
        dt_naive = dt.replace(tzinfo=None)
        diff_seconds = (now - dt_naive).total_seconds()
        
        if diff_seconds < 60:
            return "Just now"
        elif diff_seconds < 3600:
            mins = max(1, int(diff_seconds // 60))
            return f"{mins}m ago"
        elif diff_seconds < 86400:
            hours = int(diff_seconds // 3600)
            return f"{hours}h ago"
        elif diff_seconds < 172800:
            return "Yesterday"
        else:
            return dt_naive.strftime("%b %d")
    except Exception:
        return ""


def fetch_conversations():
    """Fetch all conversations for the user from backend."""
    if not st.session_state.auth_token:
        return []
    try:
        res = requests.get(
            CONVERSATIONS_API_URL,
            headers=get_auth_headers(),
            timeout=10,
        )
        if res.status_code == 200:
            st.session_state.conversations = res.json()
            return st.session_state.conversations
        elif res.status_code == 401:
            logout()
    except Exception:
        pass
    return st.session_state.conversations


def select_conversation(thread_id: str, title: str):
    """Load a specific conversation and its stored message history."""
    st.session_state.current_thread_id = thread_id
    st.session_state.current_thread_title = title
    try:
        res = requests.get(
            f"{CONVERSATIONS_API_URL}/{thread_id}",
            headers=get_auth_headers(),
            timeout=10,
        )
        if res.status_code == 200:
            data = res.json()
            st.session_state.messages = data.get("messages", [])
            st.session_state.current_thread_title = data.get("title", title)
        elif res.status_code == 401:
            logout()
        else:
            st.session_state.messages = []
    except Exception as e:
        st.error(f"Failed to load conversation: {e}")
        st.session_state.messages = []


def start_new_chat():
    """Start a fresh new conversation."""
    st.session_state.current_thread_id = None
    st.session_state.current_thread_title = "New Conversation"
    st.session_state.messages = []


def delete_conversation(thread_id: str):
    """Delete a conversation thread."""
    try:
        res = requests.delete(
            f"{CONVERSATIONS_API_URL}/{thread_id}",
            headers=get_auth_headers(),
            timeout=10,
        )
        if res.status_code == 200:
            if st.session_state.current_thread_id == thread_id:
                start_new_chat()
            fetch_conversations()
        elif res.status_code == 401:
            logout()
        else:
            st.error("Failed to delete conversation.")
    except Exception as e:
        st.error(f"Error deleting conversation: {e}")


def logout():
    st.session_state.auth_token = None
    st.session_state.current_user = None
    st.session_state.current_thread_id = None
    st.session_state.current_thread_title = "New Conversation"
    st.session_state.conversations = []
    st.session_state.messages = []
    st.session_state.initial_loaded = False
    st.rerun()


# --------------------------------------------------
# Authentication Screen (Login / Register)
# --------------------------------------------------

if not st.session_state.auth_token:
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<div class='main-header'>💰 Personal Expense Assistant</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Please sign in or create an account to manage your isolated expenses.</div>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Create Account"])

        with tab_login:
            st.subheader("Sign In")
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="e.g. user@example.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_login = st.form_submit_button("Sign In", use_container_width=True)

                if submit_login:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        try:
                            res = requests.post(
                                LOGIN_API_URL,
                                json={"email": email.strip(), "password": password},
                                timeout=15,
                            )
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state.auth_token = data["access_token"]
                                st.session_state.current_user = data["user"]
                                st.session_state.messages = []
                                st.session_state.initial_loaded = False
                                st.success("Logged in successfully!")
                                st.rerun()
                            else:
                                err_detail = res.json().get("detail", "Invalid email or password.")
                                st.error(f"Login failed: {err_detail}")
                        except requests.exceptions.ConnectionError:
                            st.error("❌ Cannot connect to backend. Please ensure FastAPI server is running.")
                        except Exception as e:
                            st.error(f"❌ Error during login: {e}")

        with tab_register:
            st.subheader("Register New Account")
            with st.form("register_form"):
                reg_username = st.text_input("Username", placeholder="e.g. johndoe")
                reg_email = st.text_input("Email Address", placeholder="e.g. user@example.com")
                reg_password = st.text_input("Password", type="password", placeholder="Choose a secure password")
                reg_currency = st.selectbox("Default Currency", ["INR", "USD", "EUR", "GBP", "CAD", "AUD", "JPY"], index=0)
                submit_register = st.form_submit_button("Create Account", use_container_width=True)

                if submit_register:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("Please fill in all required fields.")
                    else:
                        try:
                            res = requests.post(
                                REGISTER_API_URL,
                                json={
                                    "username": reg_username.strip(),
                                    "email": reg_email.strip(),
                                    "password": reg_password,
                                    "default_currency": reg_currency,
                                },
                                timeout=15,
                            )
                            if res.status_code == 201:
                                data = res.json()
                                st.session_state.auth_token = data["access_token"]
                                st.session_state.current_user = data["user"]
                                st.session_state.messages = []
                                st.session_state.initial_loaded = False
                                st.success("Account created and logged in successfully!")
                                st.rerun()
                            else:
                                err_detail = res.json().get("detail", "Registration failed.")
                                st.error(f"Registration failed: {err_detail}")
                        except requests.exceptions.ConnectionError:
                            st.error("❌ Cannot connect to backend. Please ensure FastAPI server is running.")
                        except Exception as e:
                            st.error(f"❌ Error during registration: {e}")

    st.stop()


# --------------------------------------------------
# Initial Data Load on Login
# --------------------------------------------------

if not st.session_state.initial_loaded:
    convs = fetch_conversations()
    if convs:
        # Load most recent conversation
        first_conv = convs[0]
        select_conversation(first_conv["id"], first_conv["title"])
    else:
        start_new_chat()
    st.session_state.initial_loaded = True


# --------------------------------------------------
# Logged In View (Sidebar + Main Chat)
# --------------------------------------------------

user_info = st.session_state.current_user or {}
username = user_info.get("username", "User")
email = user_info.get("email", "")
currency = user_info.get("default_currency", "INR")

with st.sidebar:
    # User Profile Info
    st.markdown(
        f"""
        <div class='user-badge'>
            <div style='font-weight: 700; font-size: 1.05rem;'>👤 {username}</div>
            <div style='font-size: 0.8rem; color: #6c757d;'>{email}</div>
            <div style='font-size: 0.8rem; margin-top: 4px;'>Currency: <code>{currency}</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        start_new_chat()
        st.rerun()

    st.divider()

    # Conversations Section (Chronological order: Most recent at top)
    st.markdown("### 💬 Chat History")

    conversations = st.session_state.conversations or []

    if not conversations:
        st.caption("No conversations yet. Start chatting!")
    else:
        for conv in conversations:
            thread_id = conv["id"]
            title = conv.get("title", "Conversation")
            updated_at = conv.get("updated_at", "")
            time_badge = format_relative_time(updated_at)
            
            is_active = (thread_id == st.session_state.current_thread_id)
            
            # Truncate title if long
            display_title = title if len(title) <= 22 else f"{title[:20]}..."
            button_label = f"💬 {display_title}"
            if time_badge:
                button_label += f" ({time_badge})"

            col_thread, col_del = st.columns([5, 1])

            with col_thread:
                if st.button(
                    button_label,
                    key=f"thread_btn_{thread_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    select_conversation(thread_id, title)
                    st.rerun()

            with col_del:
                if st.button("🗑️", key=f"del_btn_{thread_id}", help="Delete chat"):
                    delete_conversation(thread_id)
                    st.rerun()

    st.divider()

    # Quick Tips
    st.markdown("### 💡 Quick Tips")
    st.markdown(
        """
        - *"I spent 450 on groceries"*
        - *"Recorded 1200 for electricity bill"*
        - *"How much have I spent so far?"*
        - *"Show me my food expenses"*
        """
    )
    st.divider()

    if st.button("🚪 Logout", use_container_width=True):
        logout()


# --------------------------------------------------
# Main Chat Layout
# --------------------------------------------------

# Active Chat Title Header
current_title = st.session_state.current_thread_title or "New Conversation"
st.markdown(f"<div class='chat-header'>💬 {current_title}</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='chat-subheader'>Isolated account storage ({currency})</div>",
    unsafe_allow_html=True,
)

# Display messages for the active conversation
messages = st.session_state.messages or []

if not messages:
    st.info(
        "👋 **Welcome!** Start a conversation below to track your expenses or query your spending history. "
        "Your chat memory is saved permanently in PostgreSQL."
    )
else:
    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        with st.chat_message(role):
            st.write(content)

# Chat input
user_input = st.chat_input("Ask about your expenses or record a new one...")

if user_input:
    # 1. Display user message immediately in UI
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):
        st.write(user_input)

    # 2. Call streaming endpoint and display response token by token in real time
    headers = get_auth_headers()
    payload = {
        "message": user_input,
        "thread_id": st.session_state.current_thread_id,
    }

    with st.chat_message("assistant"):
        def generate_response_stream():
            try:
                with requests.post(
                    CHAT_STREAM_API_URL,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=60,
                ) as response:
                    if response.status_code == 401:
                        yield "⚠️ Session expired or invalid token. Please log in again."
                        return

                    response.raise_for_status()

                    for raw_line in response.iter_lines(decode_unicode=True):
                        if not raw_line:
                            continue
                        if raw_line.startswith("data: "):
                            data_str = raw_line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                event = json.loads(data_str)
                            except Exception:
                                continue

                            event_type = event.get("type")
                            if event_type == "metadata":
                                tid = event.get("thread_id")
                                title = event.get("title")
                                if tid:
                                    st.session_state.current_thread_id = tid
                                if title:
                                    st.session_state.current_thread_title = title
                            elif event_type == "token":
                                token = event.get("content", "")
                                if token:
                                    yield token
                            elif event_type == "error":
                                err_msg = event.get("error", "Unknown error")
                                yield f"\n\n❌ Error: {err_msg}"
                            elif event_type == "done":
                                tid = event.get("thread_id")
                                title = event.get("title")
                                if tid:
                                    st.session_state.current_thread_id = tid
                                if title:
                                    st.session_state.current_thread_title = title
            except requests.exceptions.ConnectionError:
                yield "❌ Could not connect to the backend. Make sure FastAPI is running on http://127.0.0.1:8000."
            except requests.exceptions.Timeout:
                yield "❌ The backend took too long to respond."
            except requests.exceptions.RequestException as e:
                yield f"❌ Backend request failed: {e}"
            except Exception as e:
                yield f"❌ Something went wrong: {e}"

        # Real-time token-by-token stream rendering
        assistant_response = st.write_stream(generate_response_stream())

    # 3. Save assistant message in session history
    if assistant_response:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": assistant_response,
            }
        )

    # 4. Refresh conversation list in sidebar
    fetch_conversations()
    st.rerun()