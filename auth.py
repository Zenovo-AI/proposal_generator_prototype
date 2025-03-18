import json
from pathlib import Path
import tempfile
from time import sleep
from google.auth.transport.requests import Request
import streamlit as st
from googleapiclient.discovery import build
from streamlit_js import st_js, st_js_blocking
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


# Function to retrieve data from local storage
def ls_get(k, key=None):
    if key is None:
        key = f"ls_get_{k}"
    return st_js_blocking(f"return JSON.parse(localStorage.getItem('{k}'));", key=key)

# Function to set data in local storage
def ls_set(k, v, key=None):
    if key is None:
        key = f"ls_set_{k}"
    jdata = json.dumps(v, ensure_ascii=False)
    st_js_blocking(f"localStorage.setItem('{k}', JSON.stringify({jdata}));", key=key)

# Initialize session with user info if it exists in local storage
def init_session():
    key = "user_info_init_session"
    if "user_info" not in st.session_state:
        user_info = ls_get("user_info", key=key)
        if user_info:
            st.session_state["user_info"] = user_info
    if "auth_code" not in st.session_state:
        st.session_state["auth_code"] = None
    if "credentials" not in st.session_state:
        st.session_state["credentials"] = None
        
auth_cache_dir = Path(__file__).parent / "auth_cache"
auth_cache_dir.mkdir(exist_ok=True, parents=True)

client_secret_path = auth_cache_dir / "client_secret.json"
auth_status_path = auth_cache_dir / "auth_success.txt"
credentials_path = auth_cache_dir / "credentials.json"

scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file"
    ]


# def auth_flow():
#     st.sidebar.title("Authentication")

#     # Add a logout button in the sidebar
#     if st.sidebar.button("Logout"):
#         logout()

#     # Step 1: Check if user is already logged in
#     if auth_status_path.exists() and credentials_path.exists():
#         with open(credentials_path, "r") as f:
#             credentials_json = json.load(f)

        
#         st.session_state["credentials"] = credentials_json
#         st.write(credentials_json)
#         st.sidebar.success(f"Already authenticated as {credentials_json['email']}!")
#         st.write(f"Hello {credentials_json['given_name']}, welcome back!")
#         return credentials_json 

#     # Step 2: Upload client secret JSON file (only needed once)
#     client_config = st.sidebar.file_uploader("Upload your client secret JSON file", type=["json"])
    
#     if client_config:
#         # Save the uploaded file to the temp directory
#         with client_secret_path.open("wb") as f:
#             f.write(client_config.read())

#     # Step 3: Check if client secret file exists
#     if not client_secret_path.exists():
#         st.warning("Please upload your client secret JSON file.")
#         return

#     client_config = json.loads(client_secret_path.read_text())

#     redirect_uri = "http://localhost:8501"
    
#     flow = Flow.from_client_config(
#     client_config,
#     scopes=scopes,
#     redirect_uri=redirect_uri,
# )

#     # Step 4: Handle OAuth Authentication
#     auth_code = st.query_params.get("code")

#     if auth_code:
#         flow = Flow.from_client_config(
#             client_config,
#             scopes=scopes,
#             redirect_uri=redirect_uri,
#         )

#         # Fetch token using the auth code
#         flow.fetch_token(code=auth_code)
#         credentials = flow.credentials
#         user_info_service = build("oauth2", "v2", credentials=credentials)
#         user_info = user_info_service.userinfo().get().execute()

#         assert user_info.get("email"), "Email not found in response"

#         # ✅ Save credentials persistently
#         with open(credentials_path, "w") as f:
#             json.dump({"email": user_info["email"], "given_name": user_info.get("given_name", ""), "token": credentials.to_json()}, f)

#         # ✅ Create a flag file to mark successful authentication
#         auth_status_path.write_text("Authenticated")

#         # ✅ Store in session state to avoid redundant API calls
#         st.session_state["credentials"] = {"email": user_info["email"], "token": credentials.to_json()}

#         st.sidebar.success(f"Login Successful! Welcome, {user_info['email']}")
#         st.write(f"Hello {user_info['given_name']}, welcome back to the Proposal Generator APP!")
#         # Display user profile picture if available
#         if "picture" in user_info:
#             st.sidebar.image(user_info["picture"], caption=user_info["name"], width=100)
#         return True

#     else:
#         authorization_url, state = flow.authorization_url(
#             access_type="offline",
#             prompt="consent",
#             include_granted_scopes="true",
#         )
#         st.link_button("Sign in with Google", authorization_url)
#         return False


# def auth_flow():
#     st.sidebar.title("Authentication")

#     # Check if user is already authenticated
#     if auth_status_path.exists() and credentials_path.exists():
#         with open(credentials_path, "r") as f:
#             credentials_json = json.load(f)
        
#         # st.session_state["credentials"] = credentials_json
#         # st.write(credentials_json)
#         # st.sidebar.success(f"Already authenticated as {credentials_json['email']}!")
#         # return credentials_json
#         creds = Credentials.from_authorized_user_info(
#             credentials_json['token'],
#             scopes=scopes
#         )
        
#         # Refresh if needed
#         if not creds.valid:
#             if creds.expired and creds.refresh_token:
#                 creds.refresh(Request())
#                 # Update stored credentials
#                 credentials_json['token'] = json.loads(creds.to_json())
#                 with open(credentials_path, "w") as f:
#                     json.dump(credentials_json, f)

#         st.session_state["credentials"] = creds
#         st.sidebar.success(f"Already authenticated as {credentials_json['email']}!")
#         if isinstance(credentials_json["token"], str):
#             try:
#                 credentials_json["token"] = json.loads(credentials_json["token"])
#             except json.JSONDecodeError:
#                 raise ValueError("Invalid token format in stored credentials.")
#         return credentials_json 

#     # Step 1: Upload client secret JSON file (only once)
#     client_config = st.sidebar.file_uploader("Upload your client secret JSON file", type=["json"])
    
#     if client_config:
#         with client_secret_path.open("wb") as f:
#             f.write(client_config.read())

#     if not client_secret_path.exists():
#         st.warning("Please upload your client secret JSON file.")
#         return {"status": "missing_client_secret"}

#     client_config = json.loads(client_secret_path.read_text())

#     redirect_uri = "http://localhost:8501"
    
#     flow = Flow.from_client_config(
#         client_config,
#         scopes=scopes,
#         redirect_uri=redirect_uri,
#     )

#     # Step 2: Handle OAuth Authentication
#     auth_code = st.query_params.get("code")

#     if auth_code and "auth_code" not in st.session_state:
#         try:
#             flow.fetch_token(code=auth_code)
#             credentials = flow.credentials
#             user_info_service = build("oauth2", "v2", credentials=credentials)
#             user_info = user_info_service.userinfo().get().execute()

#             assert user_info.get("email"), "Email not found in response"

#             # Save credentials
#             credentials_data = {
#                 "email": user_info["email"],
#                 "given_name": user_info.get("given_name", ""),
#                 "token": credentials.to_json(),
#             }
#             with open(credentials_path, "w") as f:
#                 json.dump(credentials_data, f)

#             auth_status_path.write_text("Authenticated")
#             st.session_state["credentials"] = credentials_data
#             st.session_state["auth_code"] = auth_code  # Prevent reusing auth_code

#             st.sidebar.success(f"Login Successful! Welcome, {user_info['email']}")
#             return credentials

#         except Exception as e:
#             st.error(f"Authentication failed: {str(e)}")
#             logout()  # Ensure session is cleared
#             return {"status": "error", "message": str(e)}

#     else:
#         authorization_url, _ = flow.authorization_url(
#             access_type="offline",
#             prompt="consent",
#             include_granted_scopes="true",
#         )
#         st.link_button("Sign in with Google", authorization_url)
#         return {"status": "waiting_for_login"}


def auth_flow():
    st.sidebar.title("Authentication")

    # Check if user is already authenticated
    if auth_status_path.exists() and credentials_path.exists():
        with open(credentials_path, "r") as f:
            credentials_json = json.load(f)
        
        # Ensure that the "token" field is a dictionary.
        if isinstance(credentials_json.get("token"), str):
            try:
                credentials_json["token"] = json.loads(credentials_json["token"])
            except json.JSONDecodeError:
                raise ValueError("Invalid token format in stored credentials.")
        
        st.session_state["credentials"] = credentials_json
        st.sidebar.success(f"Already authenticated as {credentials_json['email']}!")
        return credentials_json

    # Step 1: Upload client secret JSON file (only once)
    client_config = st.sidebar.file_uploader("Upload your client secret JSON file", type=["json"])
    if client_config:
        # Ensure directory exists before writing
        auth_cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Write file with verification
        try:
            with client_secret_path.open("wb") as f:
                f.write(client_config.read())
            st.session_state.client_secret_uploaded = True
            st.rerun()
        except Exception as e:
            st.error(f"Error saving client secret: {str(e)}")
            return
        
    if not client_secret_path.exists():
        st.warning("Please upload your client secret JSON file.")
        return {"status": "missing_client_secret"}

    # Add file read error handling
    try:
        client_config = json.loads(client_secret_path.read_text())
    except Exception as e:
        st.error(f"Error reading client secret: {str(e)}")
        return

    client_config = json.loads(client_secret_path.read_text())
    redirect_uri = "https://hospitalpolicies-mwh7xj6f6vuyvnhqwqkob5.streamlit.app"
    
    # After client secret is uploaded
    if client_secret_path.exists():
        client_config = json.loads(client_secret_path.read_text())
        
        # Auto-initiate OAuth flow if not authenticated
        if not auth_status_path.exists():
            flow = Flow.from_client_config(
                client_config,
                scopes=scopes,
                redirect_uri=redirect_uri,
            )
    # flow = Flow.from_client_config(
    #     client_config,
    #     scopes=scopes,
    #     redirect_uri=redirect_uri,
    # )

    # Step 2: Handle OAuth Authentication
    auth_code = st.query_params.get("code")
    if auth_code and "auth_code" not in st.session_state:
        try:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            user_info_service = build("oauth2", "v2", credentials=credentials)
            user_info = user_info_service.userinfo().get().execute()

            assert user_info.get("email"), "Email not found in response"

            # Save credentials as a dictionary, but ensure token is stored as a dict
            credentials_data = {
                "email": user_info["email"],
                "given_name": user_info.get("given_name", ""),
                "token": json.loads(credentials.to_json()),  # Parse the token into a dict
            }
            with open(credentials_path, "w") as f:
                json.dump(credentials_data, f)

            auth_status_path.write_text("Authenticated")
            st.session_state["credentials"] = credentials_data
            st.session_state["auth_code"] = auth_code  # Prevent reusing auth_code

            st.sidebar.success(f"Login Successful! Welcome, {user_info['email']}")
            return flow.credentials

        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            logout()  # Ensure session is cleared
            return {"status": "error", "message": str(e)}

    else:
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        st.link_button("Sign in with Google", authorization_url)
        return {"status": "waiting_for_login"}


def logout():
    """Completely clears all authentication artifacts"""
    
    # Remove authentication files
    if auth_status_path.exists():
        auth_status_path.unlink()
    if credentials_path.exists():
        credentials_path.unlink()

    # Ensure no residual credentials in session state
    if "credentials" in st.session_state:
        del st.session_state["credentials"]
    if "user_info" in st.session_state:
        del st.session_state["user_info"]
    st.session_state.pop("credentials", None)
    st.session_state.pop("auth_code", None)

    # Clear browser storage
    st.session_state.clear()  # Alternative to looping through keys
    st.query_params.update(logout="true")  # Force query param update
    st.sidebar.success("Logged out. Please sign in again.")

    # Force re-run
    st.rerun()
    
# def logout():
#     """Clears session but preserves auth files"""
#     if auth_status_path.exists():
#         auth_status_path.unlink()
#     if credentials_path.exists():
#         credentials_path.unlink()
        
#     # Remove session credentials but keep files
#     keys = ["credentials", "user_info", "auth_code", 
#            "drive_service", "docs_service"]
#     for key in keys:
#         st.session_state.pop(key, None)
    
#     st.query_params.update(logout="true")
#     st.sidebar.success("Logged out. Please sign in again.")
#     st.rerun()
    
    
def validate_session():
    """Check for required auth state"""
    required_keys = [
        "credentials", 
        "drive_service",
        "docs_service",
        "authenticated_email"
    ]
    
    if any(key in st.session_state for key in required_keys):
        if not auth_status_path.exists():
            logout()


# st.title("Google OAuth")

# # --- Upload Client Secret JSON ---
# client_config = st.sidebar.file_uploader("Upload your client secret JSON file", type=["json"])
# if client_config:
#     client_config = json.loads(client_config.read())

# @st.cache_resource
# def get_flow():
#     """Initializes OAuth Flow"""
#     if not client_config:
#         st.warning("Please upload your client secret JSON file to proceed.")
#         st.stop()
#     return Flow.from_client_config(
#         client_config,
#         scopes=scopes,
#         redirect_uri="http://127.0.0.1:8000/auth/code"  # Redirect to FastAPI
#     )

# @st.cache_data
# def get_auth_url(_flow: Flow):
#     """Generates Google Auth URL"""
#     auth_url, oauth_state = _flow.authorization_url(prompt="consent")
#     return auth_url, oauth_state

# flow = get_flow()
# auth_url, state = get_auth_url(flow)

# st.link_button("Login with Google", url=auth_url, type="primary")

# # --- Get OAuth Response from URL ---
# full_url = st.query_params  # Retrieves query parameters automatically

# # Extract state and code
# state_received = full_url.get("state")
# auth_code = full_url.get("code")

# if state_received and auth_code:
#     if state_received == state:  # Verify OAuth state
#         try:
#             # Exchange auth code for access token
#             flow.fetch_token(code=auth_code)
#             credentials = flow.credentials

#             # Verify ID Token
#             id_info = id_token.verify_oauth2_token(credentials.id_token, requests.Request())

#             # --- Extract Name & Picture ---
#             user_name = id_info.get("given_name", "User")
#             user_picture = id_info.get("picture", "")

#             # --- Display Welcome Message ---
#             st.write(f"✅ Hello {user_name}, welcome back to the Proposal Generator APP! 🎉")
#             if user_picture:
#                 st.image(user_picture, width=150)
    
#         except Exception as e:
#             st.error(f"Authentication failed: {str(e)}")
#     else:
#         st.error("State mismatch! Possible CSRF attack detected.")
# else:
#     st.warning("Waiting for authentication...")