import json
from googleapiclient.discovery import Resource
from format_document import extract_relevant_content
from googleapiclient.errors import HttpError
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
    
    # def write_to_document(self, doc_id, content):
    #     """Handles document structure and indexes properly"""
    #     requests = []
        
    #     # Get initial document state with structural awareness
    #     doc = self.service.documents().get(documentId=doc_id).execute()
    #     current_index = self._get_true_start_index(doc)

    #     for line in content.split('\n'):
    #         line = line.strip()
    #         if not line:
    #             continue

    #         # Handle document growth dynamically
    #         current_index = self._process_line(line, current_index, requests)

    #         # Execute in smaller batches with structural refresh
    #         if len(requests) >= 5:
    #             self._execute_with_structure_refresh(doc_id, requests)
    #             doc = self.service.documents().get(documentId=doc_id).execute()
    #             current_index = self._get_true_start_index(doc)

    #     self._execute_with_structure_refresh(doc_id, requests)

    # def _get_true_start_index(self, doc):
    #     """Calculates the safe insertion point considering doc structure"""
    #     if not doc['body']['content']:
    #         # New document has implicit paragraph element
    #         return 1  # Start at beginning of first paragraph
            
    #     last_element = doc['body']['content'][-1]
    #     if 'paragraph' in last_element:
    #         return last_element['endIndex'] - 1  # Insert before paragraph end
    #     return last_element['endIndex']

    # def _process_line(self, line, index, requests):
    #     """Returns new current index after processing line"""
    #     if line.startswith('### '):
    #         return self._handle_heading(line, index, requests, 'HEADING_3')
    #     elif line.startswith('## '):
    #         return self._handle_heading(line, index, requests, 'HEADING_2')
    #     elif '|' in line:
    #         return self._handle_table(line, index, requests)
    #     else:
    #         return self._handle_text(line, index, requests)

    # def _handle_heading(self, line, index, requests, style):
    #     """Handles headings with proper structural spacing"""
    #     text = line[4:] if style == 'HEADING_3' else line[3:]
    #     requests.extend([
    #         {
    #             'insertText': {
    #                 'location': {'index': index},
    #                 'text': text + '\n'
    #             }
    #         },
    #         {
    #             'updateParagraphStyle': {
    #                 'range': {
    #                     'startIndex': index,
    #                     'endIndex': index + len(text) + 1
    #                 },
    #                 'paragraphStyle': {'namedStyleType': style},
    #                 'fields': 'namedStyleType'
    #             }
    #         }
    #     ])
    #     return index + len(text) + 2  # Text + newline + structural offset

    # def _handle_table(self, line, index, requests):
    #     """Handles tables with proper cell indexing"""
    #     cells = [c.strip() for c in line.split('|')[1:-1]]
        
    #     # Table structure takes 2 indexes
    #     requests.append({
    #         'insertTable': {
    #             'rows': 1,
    #             'columns': len(cells),
    #             'location': {'index': index}
    #         }
    #     })
        
    #     # Cells are offset by table structure
    #     for i, cell in enumerate(cells):
    #         requests.append({
    #             'insertText': {
    #                 'location': {'index': index + 2 + i},
    #                 'text': cell
    #             }
    #         })
            
    #     return index + 3 + (len(cells) * 2)  # Table end index

    # def _handle_text(self, line, index, requests):
    #     """Handles regular text insertion"""
    #     requests.append({
    #         'insertText': {
    #             'location': {'index': index},
    #             'text': line + '\n'
    #         }
    #     })
    #     return index + len(line) + 1  # Text + newline

    # def _execute_with_structure_refresh(self, doc_id, requests):
    #     """Executes requests and clears list"""
    #     if not requests:
    #         return

    #     try:
    #         self.service.documents().batchUpdate(
    #             documentId=doc_id,
    #             body={'requests': requests}
    #         ).execute()
    #     except HttpError as e:
    #         print(f"Failed batch: {json.dumps(requests, indent=2)}")
    #         raise
    #     finally:
    #         requests.clear()

    def write_to_document(self, doc_id, content):
        """
        Writes formatted Markdown content to a Google Doc.
        """
        # relevant_content = extract_relevant_content(content)
        
        # Convert markdown to HTML
        html_content = markdown2.markdown(content, extras=["tables"])

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

