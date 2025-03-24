import json
import re
from googleapiclient.discovery import Resource
from format_document import extract_relevant_content
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
import markdown2

class GoogleDocsHelper:
    """
    Handles integration with Google Docs.
    """
    
    def __init__(self, service):
        if not isinstance(service, Resource):
            raise ValueError("Requires valid Docs service instance")
        self.service = service
        
    def get_document_length(self, doc_id):
        """Fetches the current document length to ensure correct index placement."""
        doc = self.service.documents().get(documentId=doc_id).execute()
        body = doc.get("body", {})
        content = body.get("content", [])
        return content[-1]["endIndex"] if content else 1  # Return last index position


    def create_document(self, title):
        """
        Creates a new Google Doc and returns the document ID.
        """
        document = self.service.documents().create(body={"title": title}).execute()
        return document.get("documentId")
    

    def clear_document(self, doc_id):
        """Clears all content in the document before writing new content."""
        try:
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": self.get_document_length(doc_id)}}}]}
            ).execute()
        except HttpError as e:
            print(f"Failed to clear document: {e}")

    def write_to_document(self, doc_id, content):
        """
        Writes structured content to Google Docs, handling headings, bold text, bullet points, and tables.
        """
        self.clear_document(doc_id)  # 🔥 Ensure document is empty before writing
        index = 1  # Always start at index 1
        html_content = markdown2.markdown(content, extras=["tables", "fenced-code-blocks"])
        requests = []

        table_data = []
        max_columns = 0

        for line in html_content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # **Headings**
            if line.startswith("<h1>"):
                text = re.sub(r"<[^>]+>", "", line)
                requests.extend(self._insert_text_request(index, text, "HEADING_1"))
                index += len(text) + 2

            elif line.startswith("<h2>"):
                text = re.sub(r"<[^>]+>", "", line)
                requests.extend(self._insert_text_request(index, text, "HEADING_2"))
                index += len(text) + 2

            elif line.startswith("<h3>"):
                text = re.sub(r"<[^>]+>", "", line)
                requests.extend(self._insert_text_request(index, text, "HEADING_3"))
                index += len(text) + 2

            # **Bullet Points**
            elif line.startswith("•") or line.startswith("- "):
                text = re.sub(r"<[^>]+>", "", line)
                requests.append({"insertText": {"location": {"index": index}, "text": f"• {text}\n"}})
                index += len(text) + 2

            # **Bold Text**
            elif "**" in line:
                text = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
                requests.extend(self._insert_text_request(index, text, bold=True))
                index += len(text) + 2

            # **Tables**
            elif "|" in line:  
                cells = [c.strip() for c in line.split("|")[1:-1]]  
                table_data.append(cells)
                max_columns = max(max_columns, len(cells))  

            else:
                # Ensure any pending table is inserted before adding normal text
                if table_data:
                    requests.extend(self._insert_table_request(index, table_data, max_columns))
                    index += len(table_data) * max_columns + 2  # Adjust index after table
                    table_data = []

                # Insert normal paragraph text
                text = re.sub(r"<[^>]+>", "", line)
                requests.extend(self._insert_text_request(index, text))
                index += len(text) + 2

        # Ensure any remaining table is added
        if table_data:
            requests.extend(self._insert_table_request(index, table_data, max_columns))

        # Send batch update request
        try:
            self.service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
        except HttpError as e:
            print(f"Failed batch request: {e}")
            raise

    def _insert_text_request(self, index, text, style="NORMAL_TEXT", bold=False):
        """Returns requests to insert text with optional bold styling."""
        requests = [{"insertText": {"location": {"index": index}, "text": text + "\n\n"}}]

        if bold:
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": index, "endIndex": index + len(text)},
                    "textStyle": {"bold": True},
                    "fields": "bold"
                }
            })

        if style != "NORMAL_TEXT":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": index, "endIndex": index + len(text)},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType"
                }
            })

        return requests

    def _insert_table_request(self, index, table_data, columns):
        """
        Generates requests to insert and populate a table with dynamic row and column data.
        """
        rows = len(table_data)
        requests = [{"insertTable": {"rows": rows, "columns": columns, "location": {"index": index}}}]

        cell_index = index + 1  # Table starts at index + 1
        for row_idx, row in enumerate(table_data):
            for col_idx, cell_text in enumerate(row):
                requests.append({
                    "insertText": {
                        "location": {"index": cell_index + (row_idx * columns) + col_idx},
                        "text": cell_text
                    }
                })

        return requests
        
        
    # def write_to_document(self, doc_id, content):
    #     """
    #     Writes formatted Markdown content to a Google Doc.
    #     """
    #     # relevant_content = extract_relevant_content(content)
        
    #     # Convert markdown to HTML
    #     html_content = markdown2.markdown(content, extras=["tables"])

    #     # Requests list to batch update Google Docs
    #     requests = []
        
    #     # Split content by lines
    #     lines = html_content.split("\n")
        
    #     index = 1  # Start writing at index 1
    #     for line in lines:
    #         if line.startswith("<h1>"):
    #             text_content = line[4:-5]
    #             requests.append({
    #                 "insertText": {"location": {"index": index}, "text": text_content + "\n\n"}
    #             })
    #             requests.append({
    #                 "updateParagraphStyle": {
    #                     "range": {"startIndex": index, "endIndex": index + len(text_content)},
    #                     "paragraphStyle": {"namedStyleType": "HEADING_1"},
    #                     "fields": "*"
    #                 }
    #             })
    #             index += len(text_content) + 2
            
    #         elif line.startswith("<h2>"):
    #             text_content = line[4:-5]
    #             requests.append({
    #                 "insertText": {"location": {"index": index}, "text": text_content + "\n\n"}
    #             })
    #             requests.append({
    #                 "updateParagraphStyle": {
    #                     "range": {"startIndex": index, "endIndex": index + len(text_content)},
    #                     "paragraphStyle": {"namedStyleType": "HEADING_2"},
    #                     "fields": "*"
    #                 }
    #             })
    #             index += len(text_content) + 2
            
    #         elif line.startswith("<ul>") or line.startswith("<li>"):
    #             text = re.sub(r"<[^>]+>", "", line).strip()
    #             requests.append({
    #                 "insertText": {"location": {"index": index}, "text": "• " + text + "\n"}
    #             })
    #             index += len(text) + 2
            
    #         elif "|" in line:  # Table handling
    #             cells = line.split("|")[1:-1]  # Extract table row content
    #             requests.append({
    #                 "insertTable": {
    #                     "rows": 1,  # Adjust for multiple rows
    #                     "columns": len(cells),
    #                     "location": {"index": index}
    #                 }
    #             })
    #             for col, text in enumerate(cells):
    #                 requests.append({
    #                     "insertText": {
    #                         "location": {"index": index + col + 1},
    #                         "text": text.strip()
    #                     }
    #                 })
    #             index += len(cells) + 2  # Move index
            
    #         elif line.strip():  # Normal paragraph text
    #             text = re.sub(r"<[^>]+>", "", line).strip()
    #             requests.append({
    #                 "insertText": {"location": {"index": index}, "text": text + "\n\n"}
    #             })
    #             index += len(text) + 2

    #     # Send batch update request
    #     self.service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


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

