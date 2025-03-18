import json
from googleapiclient.discovery import build, Resource
from format_document import extract_relevant_content
from google.oauth2.credentials import Credentials
import re
import markdown2

class GoogleDocsHelper:
    """
    Handles integration with Google Docs.
    """
    
    def __init__(self, service):
        if not isinstance(service, Resource):
            raise ValueError("Requires valid Docs service instance")
        self.service = service


    def create_document(self, title):
        """
        Creates a new Google Doc and returns the document ID.
        """
        document = self.service.documents().create(body={"title": title}).execute()
        return document.get("documentId")

    def write_to_document(self, doc_id, content):
        """
        Writes formatted Markdown content to a Google Doc.
        """
        relevant_content = extract_relevant_content(content)
        
        # Convert markdown to HTML
        html_content = markdown2.markdown(relevant_content, extras=["tables"])

        # Requests list to batch update Google Docs
        requests = []
        
        # Split content by lines
        lines = html_content.split("\n")
        
        index = 1  # Start writing at index 1
        for line in lines:
            if line.startswith("<h1>"):
                text_content = line[4:-5]
                requests.append({
                    "insertText": {"location": {"index": index}, "text": text_content + "\n\n"}
                })
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": index, "endIndex": index + len(text_content)},
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "fields": "*"
                    }
                })
                index += len(text_content) + 2
            
            elif line.startswith("<h2>"):
                text_content = line[4:-5]
                requests.append({
                    "insertText": {"location": {"index": index}, "text": text_content + "\n\n"}
                })
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": index, "endIndex": index + len(text_content)},
                        "paragraphStyle": {"namedStyleType": "HEADING_2"},
                        "fields": "*"
                    }
                })
                index += len(text_content) + 2
            
            elif line.startswith("<ul>") or line.startswith("<li>"):
                text = re.sub(r"<[^>]+>", "", line).strip()
                requests.append({
                    "insertText": {"location": {"index": index}, "text": "• " + text + "\n"}
                })
                index += len(text) + 2
            
            elif "|" in line:  # Table handling
                cells = line.split("|")[1:-1]  # Extract table row content
                requests.append({
                    "insertTable": {
                        "rows": 1,  # Adjust for multiple rows
                        "columns": len(cells),
                        "location": {"index": index}
                    }
                })
                for col, text in enumerate(cells):
                    requests.append({
                        "insertText": {
                            "location": {"index": index + col + 1},
                            "text": text.strip()
                        }
                    })
                index += len(cells) + 2  # Move index
            
            elif line.strip():  # Normal paragraph text
                text = re.sub(r"<[^>]+>", "", line).strip()
                requests.append({
                    "insertText": {"location": {"index": index}, "text": text + "\n\n"}
                })
                index += len(text) + 2

        # Send batch update request
        self.service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()



class GoogleDriveAPI:
    def __init__(self, service):
        """
        Initializes the Google Drive API with an existing service instance.
        """
        self.service = service
        
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

