import json
import time
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from reportlab.lib.pagesizes import letter
import markdown2
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from format_document import extract_relevant_content


def create_pdf(file_path, content):
    """
    Converts Markdown content into formatted text and generates a well-spaced PDF.
    """
    
    relevant_content = extract_relevant_content(content)
    
    # Convert Markdown to HTML
    html_content = markdown2.markdown(relevant_content, extras=["tables"])

    # Set up PDF document
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Process HTML content line by line
    lines = html_content.split("\n")
    for line in lines:
        if line.startswith("<h1>"):  # Large title
            story.append(Paragraph(line[4:-5], styles["Title"]))
            story.append(Spacer(1, 12))
        elif line.startswith("<h2>"):  # Section headings
            story.append(Paragraph(line[4:-5], styles["Heading2"]))
            story.append(Spacer(1, 10))
        elif line.startswith("<ul>"):  # Bullet points
            story.append(Spacer(1, 5))
        elif line.startswith("<li>"):
            story.append(Paragraph(f"• {line[4:-5]}", styles["Normal"]))
            story.append(Spacer(1, 5))
        elif "|" in line:  # Handle tables
            table_data = [row.split("|")[1:-1] for row in lines if "|" in row]
            table = Table(table_data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]))
            story.append(table)
            story.append(Spacer(1, 10))
        elif line.strip():  # Normal text paragraphs
            story.append(Paragraph(line.strip(), styles["Normal"]))
            story.append(Spacer(1, 8))

    # Build the PDF
    doc.build(story)



class GoogleDriveHelper:
    
    def __init__(self, credentials):
        """
        Initializes the Google Docs API with OAuth2 credentials.
        """
        if not credentials or not isinstance(credentials, dict):
            raise ValueError("Invalid credentials: Expected a dictionary.")

        # Use either 'token' or 'refresh_token' if present
        token_data = credentials.get("token") or credentials.get("refresh_token")

        if not token_data:
            raise ValueError("Invalid credentials: Missing 'token' or 'refresh_token'.")

        # Ensure token_data is parsed correctly if it's a string
        if isinstance(token_data, str):
            try:
                token_data = json.loads(token_data)
            except json.JSONDecodeError:
                raise ValueError("Invalid token format: Expected JSON string or dictionary.")

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),  
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            token_uri=token_data.get("token_uri"),
        )

        self.service = build("drive", "v3", credentials=creds)
        
    # def __init__(self, service):
    #     self.service = service

    def create_folder(self, folder_name, parent_folder_id="root"):
        """Create a folder in the specified parent folder (or root if none provided)."""
        try:
            drive_service = self.service.files()  # ✅ Ensure drive API is initialized correctly

            # Check if folder already exists
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents"
            results = drive_service.list(q=query, fields="files(id, name)").execute()
            folders = results.get("files", [])

            if folders:
                return folders[0]["id"]  # Return existing folder ID

            # Create new folder
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id] if parent_folder_id else ["root"],  # ✅ Default to root
            }

            folder = drive_service.create(body=file_metadata, fields="id").execute()
            return folder["id"]

        except AttributeError:
            raise RuntimeError("Google Drive API service is not initialized correctly.")



    def upload_file(self, folder_id, file_path, content, file_name=None):
        """Upload file to specific folder"""
        if not file_name:
            file_name = f"proposal_{int(time.time())}.pdf"
        
        create_pdf(file_path, content)
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        
        return file.get('webViewLink')