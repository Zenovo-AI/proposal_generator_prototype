# import json
# import re
# from googleapiclient.discovery import Resource
# from format_document import extract_relevant_content
# from googleapiclient.errors import HttpError
# from bs4 import BeautifulSoup
# import markdown2

# class GoogleDocsHelper:
#     """
#     Handles integration with Google Docs.
#     """
    
#     def __init__(self, service):
#         if not isinstance(service, Resource):
#             raise ValueError("Requires valid Docs service instance")
#         self.service = service


#     def create_document(self, title):
#         """
#         Creates a new Google Doc and returns the document ID.
#         """
#         document = self.service.documents().create(body={"title": title}).execute()
#         return document.get("documentId")
    

#     # def clear_document(self, doc_id):
#     #     """Clears all content in the document before writing new content."""
#     #     try:
#     #         self.service.documents().batchUpdate(
#     #             documentId=doc_id,
#     #             body={"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": self.get_document_length(doc_id)}}}]}
#     #         ).execute()
#     #     except HttpError as e:
#     #         print(f"Failed to clear document: {e}")

#     # def write_to_document(self, doc_id, content):
#     #     """
#     #     Writes structured content to Google Docs, handling headings, bold text, bullet points, and tables.
#     #     """
#     #     self.clear_document(doc_id)
#     #     index = 1

#     #     # Add header with company logo and address
#     #     requests = [{
#     #         "insertTable": {
#     #             "rows": 1,
#     #             "columns": 2,
#     #             "location": {"index": index}
#     #         }
#     #     }]
        
#     #     # Company logo cell
#     #     requests.append({
#     #         "insertText": {
#     #             "location": {"index": index + 1},
#     #             "text": "CDGA"  # Replace with actual logo insertion when available
#     #         }
#     #     })
        
#     #     # Company address cell (right-aligned)
#     #     address_text = "3012 €o Business Park, Little Island,\nCork, T45 V220\nwww.cdga.ie\ninfo@cdga.ie"
#     #     requests.append({
#     #         "insertText": {
#     #             "location": {"index": index + 2},
#     #             "text": address_text
#     #         }
#     #     })
        
#     #     # Right align address
#     #     requests.append({
#     #         "updateParagraphStyle": {
#     #             "range": {"startIndex": index + 2, "endIndex": index + 2 + len(address_text)},
#     #             "paragraphStyle": {"alignment": "END"},
#     #             "fields": "alignment"
#     #         }
#     #     })
        
#     #     index += len(address_text) + 4  # Adjust index after header
#     #     html_content = markdown2.markdown(content, extras=["tables", "fenced-code-blocks"])
#     #     requests = []

#     #     table_data = []
#     #     max_columns = 0

#     #     for line in html_content.split("\n"):
#     #         line = line.strip()
#     #         if not line:
#     #             continue

#     #         # **Headings**
#     #         if line.startswith("<h1>"):
#     #             text = re.sub(r"<[^>]+>", "", line)
#     #             requests.extend(self._insert_text_request(index, text, "HEADING_1"))
#     #             index += len(text) + 2

#     #         elif line.startswith("<h2>"):
#     #             text = re.sub(r"<[^>]+>", "", line)
#     #             requests.extend(self._insert_text_request(index, text, "HEADING_2"))
#     #             index += len(text) + 2

#     #         elif line.startswith("<h3>"):
#     #             text = re.sub(r"<[^>]+>", "", line)
#     #             requests.extend(self._insert_text_request(index, text, "HEADING_3"))
#     #             index += len(text) + 2

#     #         # **Bullet Points**
#     #         elif line.startswith("•") or line.startswith("- "):
#     #             text = re.sub(r"<[^>]+>", "", line)
#     #             requests.extend([
#     #                 {"insertText": {"location": {"index": index}, "text": f"• {text}\n"}},
#     #                 {"updateParagraphStyle": {
#     #                     "range": {"startIndex": index, "endIndex": index + len(text) + 2},
#     #                     "paragraphStyle": {
#     #                         "indentStart": {"magnitude": 36, "unit": "PT"},
#     #                         "spacingMode": "NEVER_COLLAPSE",
#     #                         "spaceAbove": {"magnitude": 6, "unit": "PT"},
#     #                         "spaceBelow": {"magnitude": 6, "unit": "PT"}
#     #                     },
#     #                     "fields": "indentStart,spacingMode,spaceAbove,spaceBelow"
#     #                 }}
#     #             ])
#     #             index += len(text) + 2

#     #         # **Bold Text**
#     #         elif "**" in line:
#     #             text = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
#     #             requests.extend(self._insert_text_request(index, text, bold=True))
#     #             index += len(text) + 2

#     #         # **Tables**
#     #         elif "|" in line:  
#     #             cells = [c.strip() for c in line.split("|")[1:-1]]  
#     #             table_data.append(cells)
#     #             max_columns = max(max_columns, len(cells))  

#     #         else:
#     #             # Ensure any pending table is inserted before adding normal text
#     #             if table_data:
#     #                 requests.extend(self._insert_table_request(index, table_data, max_columns))
#     #                 index += len(table_data) * max_columns + 2  # Adjust index after table
#     #                 table_data = []

#     #             # Insert normal paragraph text
#     #             text = re.sub(r"<[^>]+>", "", line)
#     #             requests.extend(self._insert_text_request(index, text))
#     #             index += len(text) + 2

#     #     # Ensure any remaining table is added
#     #     if table_data:
#     #         requests.extend(self._insert_table_request(index, table_data, max_columns))

#     #     # Send batch update request
#     #     try:
#     #         self.service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
#     #     except HttpError as e:
#     #         print(f"Failed batch request: {e}")
#     #         raise

#     # def _insert_text_request(self, index, text, style="NORMAL_TEXT", bold=False):
#     #     """Returns requests to insert text with optional bold styling."""
#     #     requests = [{"insertText": {"location": {"index": index}, "text": text + "\n\n"}}]

#     #     if bold:
#     #         requests.append({
#     #             "updateTextStyle": {
#     #                 "range": {"startIndex": index, "endIndex": index + len(text)},
#     #                 "textStyle": {"bold": True},
#     #                 "fields": "bold"
#     #             }
#     #         })

#     #     if style != "NORMAL_TEXT":
#     #         requests.append({
#     #             "updateParagraphStyle": {
#     #                 "range": {"startIndex": index, "endIndex": index + len(text)},
#     #                 "paragraphStyle": {"namedStyleType": style},
#     #                 "fields": "namedStyleType"
#     #             }
#     #         })

#     #     return requests

#     # def _insert_table_request(self, index, table_data, columns):
#     #     """
#     #     Generates requests to insert and populate a table with dynamic row and column data.
#     #     """
#     #     rows = len(table_data)
#     #     requests = [{"insertTable": {"rows": rows, "columns": columns, "location": {"index": index}}}]

#     #     cell_index = index + 1  # Table starts at index + 1
#     #     for row_idx, row in enumerate(table_data):
#     #         for col_idx, cell_text in enumerate(row):
#     #             requests.append({
#     #                 "insertText": {
#     #                     "location": {"index": cell_index + (row_idx * columns) + col_idx},
#     #                     "text": cell_text
#     #                 }
#     #             })

#     #     return requests
    
#     def clear_document(self, doc_id):
#         """Safely clears document content while preserving required structure"""
#         try:
#             doc = self.service.documents().get(documentId=doc_id).execute()
#             content = doc.get('body', {}).get('content', [])
            
#             if len(content) < 2:  # Document only contains root paragraph
#                 return  # Nothing to clear

#             # Calculate safe deletion range (preserve final newline)
#             end_index = content[-1]['endIndex']
#             safe_end = max(2, end_index - 1)  # Always leave final newline

#             delete_request = {
#                 "deleteContentRange": {
#                     "range": {
#                         "startIndex": 1,
#                         "endIndex": safe_end
#                     }
#                 }
#             }

#             self.service.documents().batchUpdate(
#                 documentId=doc_id,
#                 body={"requests": [delete_request]}
#             ).execute()

#         except HttpError as e:
#             if "empty range" in str(e).lower():
#                 print("Document already cleared")
#             else:
#                 raise

#     # def write_to_document(self, doc_id, content):
#     #     """Atomic document writing with structural validation"""
#     #     try:
#     #         # 1. Get fresh document state
#     #         doc = self.service.documents().get(documentId=doc_id).execute()
#     #         content_elements = doc.get('body', {}).get('content', [])
            
#     #         # 2. Calculate insertion point
#     #         insert_index = 1
#     #         if content_elements:
#     #             last_element = content_elements[-1]
#     #             insert_index = last_element['endIndex'] - 1

#     #         # 3. Create content requests
#     #         requests = []
            
#     #         # 4. Add mandatory root paragraph
#     #         requests.append({
#     #             "insertText": {
#     #                 "location": {"index": insert_index},
#     #                 "text": "\n"
#     #             }
#     #         })
#     #         insert_index += 1

#     #         # 5. Process content with structural awareness
#     #         sections = [
#     #             ("HEADING_1", r"^# "),
#     #             ("HEADING_2", r"^## "),
#     #             ("BULLET", r"^[•-]"),
#     #             ("TABLE", r"\|"),
#     #         ]

#     #         for line in content.split('\n'):
#     #             line = line.strip()
#     #             if not line:
#     #                 continue

#     #             # Determine element type
#     #             element_type = "PARAGRAPH"
#     #             for style, pattern in sections:
#     #                 if re.search(pattern, line):
#     #                     element_type = style
#     #                     break

#     #             # Create element-specific requests
#     #             if element_type == "HEADING_1":
#     #                 requests.extend(self._create_heading(line[2:], insert_index, "HEADING_1"))
#     #                 insert_index += len(line) + 2
                    
#     #             elif element_type == "HEADING_2":
#     #                 requests.extend(self._create_heading(line[3:], insert_index, "HEADING_2"))
#     #                 insert_index += len(line) + 2
                    
#     #             elif element_type == "BULLET":
#     #                 requests.extend(self._create_bullet(line, insert_index))
#     #                 insert_index += len(line) + 2
                    
#     #             elif element_type == "TABLE":
#     #                 requests.extend(self._create_table(line, insert_index))
#     #                 insert_index += self._calculate_table_size(line) + 2
                    
#     #             else:
#     #                 requests.extend(self._create_paragraph(line, insert_index))
#     #                 insert_index += len(line) + 2

#     #             # Maintain paragraph structure
#     #             requests.append({
#     #                 "insertText": {
#     #                     "location": {"index": insert_index},
#     #                     "text": "\n"
#     #                 }
#     #             })
#     #             insert_index += 1

#     #         # 6. Execute in validated batches
#     #         BATCH_SIZE = 50
#     #         for i in range(0, len(requests), BATCH_SIZE):
#     #             batch = requests[i:i+BATCH_SIZE]
#     #             self.service.documents().batchUpdate(
#     #                 documentId=doc_id,
#     #                 body={"requests": batch}
#     #             ).execute()
#     #             # Refresh document state after each batch
#     #             doc = self.service.documents().get(documentId=doc_id).execute()

#     #     except HttpError as e:
#     #         print(f"Document update failed: {e}")
#     #         self._rollback_changes(doc_id)
#     #         raise

#     # def _create_paragraph(self, text, index):
#     #     """Creates a normal text paragraph request"""
#     #     return [
#     #         {
#     #             "insertText": {
#     #                 "location": {"index": index},
#     #                 "text": f"{text}\n"
#     #             }
#     #         },
#     #         {
#     #             "updateParagraphStyle": {
#     #                 "range": {"startIndex": index, "endIndex": index + len(text) + 1},
#     #                 "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
#     #                 "fields": "namedStyleType"
#     #             }
#     #         }
#     #     ]

#     # def _create_heading(self, text, index, style):
#     #     """Creates heading requests with proper styling"""
#     #     return [
#     #         {
#     #             "insertText": {
#     #                 "location": {"index": index},
#     #                 "text": f"{text}\n"
#     #             }
#     #         },
#     #         {
#     #             "updateParagraphStyle": {
#     #                 "range": {"startIndex": index, "endIndex": index + len(text) + 1},
#     #                 "paragraphStyle": {"namedStyleType": style},
#     #                 "fields": "namedStyleType"
#     #             }
#     #         }
#     #     ]

#     # def _create_bullet(self, text, index):
#     #     """Creates bullet point requests with list formatting"""
#     #     return [
#     #         {
#     #             "insertText": {
#     #                 "location": {"index": index},
#     #                 "text": f"• {text.strip('•- ')}\n"
#     #             }
#     #         },
#     #         {
#     #             "updateParagraphStyle": {
#     #                 "range": {"startIndex": index, "endIndex": index + len(text) + 3},
#     #                 "paragraphStyle": {
#     #                     "bullet": {"listId": "1"},
#     #                     "indentStart": {"magnitude": 18, "unit": "PT"}
#     #                 },
#     #                 "fields": "bullet,indentStart"
#     #             }
#     #         }
#     #     ]

#     # def _create_table(self, line, index):
#     #     """Creates table structure requests"""
#     #     rows = [row.split("|") for row in line.split("\n") if row.strip()]
#     #     return [
#     #         {
#     #             "insertTable": {
#     #                 "rows": len(rows),
#     #                 "columns": len(rows[0]) if rows else 0,
#     #                 "location": {"index": index}
#     #             }
#     #         },
#     #         *self._populate_table_cells(rows, index + 1)
#     #     ]

#     # def _populate_table_cells(self, rows, start_index):
#     #     """Populates table cells with content"""
#     #     requests = []
#     #     for row_idx, row in enumerate(rows):
#     #         for col_idx, cell in enumerate(row):
#     #             requests.append({
#     #                 "insertText": {
#     #                     "location": {"index": start_index + (row_idx * len(row)) + col_idx},
#     #                     "text": cell.strip()
#     #                 }
#     #             })
#     #     return requests

#     # def _calculate_table_size(self, line):
#     #     """Calculates table size for index management"""
#     #     rows = [row.split("|") for row in line.split("\n") if row.strip()]
#     #     return sum(len(row) for row in rows) + len(rows)  # Cells + row separators

#     # def get_document_length(self, doc_id):
#     #     """Get current document length in indexes"""
#     #     doc = self.service.documents().get(documentId=doc_id).execute()
#     #     return doc['body']['content'][-1]['endIndex']
    
#     # def _rollback_changes(self, doc_id):
#     #     # Implement version recovery or snapshot restoration
#     #     pass
    
#     def write_to_document(self, doc_id, content):
#         """Write content while respecting Google Docs' structural requirements"""
#         try:
#             # Clear document safely
#             self.clear_document(doc_id)
            
#             # Get current document state
#             doc = self.service.documents().get(documentId=doc_id).execute()
#             insert_index = doc['body']['content'][-1]['endIndex'] - 1
            
#             # Create content requests
#             requests = []
#             requests.append({
#                 "insertText": {
#                     "location": {"index": insert_index},
#                     "text": "\n"  # Maintain paragraph structure
#                 }
#             })
#             insert_index += 1
            
#             # Process content in paragraph units
#             paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
#             for para in paragraphs:
#                 requests.extend(self._create_paragraph(para, insert_index))
#                 insert_index += len(para) + 2  # Account for text + newlines
                
#                 # Refresh document state every 10 operations
#                 if len(requests) % 10 == 0:
#                     doc = self.service.documents().get(documentId=doc_id).execute()
#                     insert_index = doc['body']['content'][-1]['endIndex'] - 1

#             # Execute in safe batches
#             BATCH_SIZE = 20
#             for i in range(0, len(requests), BATCH_SIZE):
#                 self.service.documents().batchUpdate(
#                     documentId=doc_id,
#                     body={"requests": requests[i:i+BATCH_SIZE]}
#                 ).execute()

#         except HttpError as e:
#             print(f"Document update failed: {e}")
#             raise

#     def _content_to_requests(self, content):
#         """Convert markdown-like content to Docs API requests"""
#         requests = []
#         current_position = 1  # Start after root paragraph
        
#         elements = self._parse_content(content)
#         for element in elements:
#             requests.extend(self._create_element_requests(element, current_position))
#             current_position = self._calculate_new_position(element, current_position)
        
#         return requests

#     def _parse_content(self, content):
#         """Parse content into structured elements"""
#         # Implement proper markdown parsing
#         return [
#             {"type": "heading1", "text": "Proposal for RFQ No. 2024-108"},
#             {"type": "paragraph", "text": "CDGA Engineering Consultants Ltd"},
#             # ... parsed elements ...
#         ]

#     def _create_element_requests(self, element, position):
#         """Create requests for each element type"""
#         if element["type"] == "heading1":
#             return [{
#                 "insertText": {
#                     "location": {"index": position},
#                     "text": f'{element["text"]}\n'
#                 }
#             }, {
#                 "updateParagraphStyle": {
#                     "range": {"startIndex": position, "endIndex": position + len(element["text"]) + 1},
#                     "paragraphStyle": {"namedStyleType": "HEADING_1"},
#                     "fields": "namedStyleType"
#                 }
#             }]
#         # Add other element types (bullets, tables, etc.)

#     def _execute_batches(self, doc_id, requests):
#         """Execute requests with automatic position validation"""
#         BATCH_SIZE = 10  # Small batches for safety
#         for i in range(0, len(requests), BATCH_SIZE):
#             try:
#                 self.service.documents().batchUpdate(
#                     documentId=doc_id,
#                     body={"requests": requests[i:i+BATCH_SIZE]}
#                 ).execute()
#             except HttpError as e:
#                 if "invalid requests" in str(e).lower():
#                     # Refresh document state and retry
#                     doc = self.service.documents().get(documentId=doc_id).execute()
#                     new_position = doc['body']['content'][-1]['endIndex']
#                     self._adjust_positions(requests[i:], new_position)
#                     continue
#                 raise

#     def _adjust_positions(self, requests, new_base):
#         """Dynamically adjust request positions based on current doc state"""
#         for request in requests:
#             if "insertText" in request:
#                 request["insertText"]["location"]["index"] += new_base
        
        
#     # def write_to_document(self, doc_id, content):
#     #     """
#     #     Writes formatted Markdown content to a Google Doc.
#     #     """
#     #     # relevant_content = extract_relevant_content(content)
        
#     #     # Convert markdown to HTML
#     #     html_content = markdown2.markdown(content, extras=["tables"])

#     #     # Requests list to batch update Google Docs
#     #     requests = []
        
#     #     # Split content by lines
#     #     lines = html_content.split("\n")
        
#     #     index = 1  # Start writing at index 1
#     #     for line in lines:
#     #         if line.startswith("<h1>"):
#     #             text_content = line[4:-5]
#     #             requests.append({
#     #                 "insertText": {"location": {"index": index}, "text": text_content + "\n\n"}
#     #             })
#     #             requests.append({
#     #                 "updateParagraphStyle": {
#     #                     "range": {"startIndex": index, "endIndex": index + len(text_content)},
#     #                     "paragraphStyle": {"namedStyleType": "HEADING_1"},
#     #                     "fields": "*"
#     #                 }
#     #             })
#     #             index += len(text_content) + 2
            
#     #         elif line.startswith("<h2>"):
#     #             text_content = line[4:-5]
#     #             requests.append({
#     #                 "insertText": {"location": {"index": index}, "text": text_content + "\n\n"}
#     #             })
#     #             requests.append({
#     #                 "updateParagraphStyle": {
#     #                     "range": {"startIndex": index, "endIndex": index + len(text_content)},
#     #                     "paragraphStyle": {"namedStyleType": "HEADING_2"},
#     #                     "fields": "*"
#     #                 }
#     #             })
#     #             index += len(text_content) + 2
            
#     #         elif line.startswith("<ul>") or line.startswith("<li>"):
#     #             text = re.sub(r"<[^>]+>", "", line).strip()
#     #             requests.append({
#     #                 "insertText": {"location": {"index": index}, "text": "• " + text + "\n"}
#     #             })
#     #             index += len(text) + 2
            
#     #         elif "|" in line:  # Table handling
#     #             cells = line.split("|")[1:-1]  # Extract table row content
#     #             requests.append({
#     #                 "insertTable": {
#     #                     "rows": 1,  # Adjust for multiple rows
#     #                     "columns": len(cells),
#     #                     "location": {"index": index}
#     #                 }
#     #             })
#     #             for col, text in enumerate(cells):
#     #                 requests.append({
#     #                     "insertText": {
#     #                         "location": {"index": index + col + 1},
#     #                         "text": text.strip()
#     #                     }
#     #                 })
#     #             index += len(cells) + 2  # Move index
            
#     #         elif line.strip():  # Normal paragraph text
#     #             text = re.sub(r"<[^>]+>", "", line).strip()
#     #             requests.append({
#     #                 "insertText": {"location": {"index": index}, "text": text + "\n\n"}
#     #             })
#     #             index += len(text) + 2

#     #     # Send batch update request
#     #     self.service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


# class GoogleDriveAPI:
#     def __init__(self, service):
#         """
#         Initializes the Google Drive API with an existing service instance.
#         """
#         self.service = service
        
#     def create_folder(self, folder_name, parent_folder_id="root"):
#         """Create a folder in the specified parent folder (or root if none provided)."""
#         try:
#             drive_service = self.service.files()  # ✅ Ensure drive API is initialized correctly

#             # Check if folder already exists
#             query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents"
#             results = drive_service.list(q=query, fields="files(id, name)").execute()
#             folders = results.get("files", [])

#             if folders:
#                 return folders[0]["id"]  # Return existing folder ID

#             # Create new folder
#             file_metadata = {
#                 "name": folder_name,
#                 "mimeType": "application/vnd.google-apps.folder",
#                 "parents": [parent_folder_id] if parent_folder_id else ["root"],  # ✅ Default to root
#             }

#             folder = drive_service.create(body=file_metadata, fields="id").execute()
#             return folder["id"]

#         except AttributeError:
#             raise RuntimeError("Google Drive API service is not initialized correctly.")



import json
import re
import time
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError


def debug_find_placeholders(docs_service, doc_id):
        """
        Fetch the document and print detected text content to check if placeholders exist.
        """
        try:
            doc = docs_service.documents().get(documentId=doc_id).execute()
            content = doc.get("body", {}).get("content", [])

            detected_text = []
            for element in content:
                if "paragraph" in element:
                    for text_run in element["paragraph"].get("elements", []):
                        if "textRun" in text_run:
                            detected_text.append(text_run["textRun"]["content"])

            print("\n--- Detected Text in Google Doc ---\n")
            print("\n".join(detected_text))  # Print all detected text in the document
            print("\n--- End of Document Text ---\n")

        except HttpError as e:
            print(f"Error fetching document: {e}")


class GoogleDocsHelper:
    """
    Handles Google Docs integration using template-based approach.
    """

    def __init__(self, docs_service, drive_service):
        if not isinstance(docs_service, Resource) or not isinstance(drive_service, Resource):
            raise ValueError("Requires valid Docs and Drive service instances")
        self.docs_service = docs_service
        self.drive_service = drive_service

    def create_from_template(self, template_id, replacements, document_name):
        """
        Copies a Google Docs template, replaces placeholders, and returns the new document ID.
        """
        try:
            # ✅ Step 1: Copy the existing Google Docs template
            copied_file = self.drive_service.files().copy(
                fileId=template_id,
                body={"name": document_name}
            ).execute()
            new_doc_id = copied_file["id"]

            # ✅ Step 2: Fetch document content for debugging
            debug_find_placeholders(self.docs_service, new_doc_id)

            # ✅ Step 3: Build text replacement requests
            requests = []
            for placeholder, content in replacements.items():
                requests.append({
                    "replaceAllText": {
                        "containsText": {"text": f"{{{placeholder}}}", "matchCase": True},
                        "replaceText": content or "[MISSING CONTENT]"
                    }
                })

            # ✅ Step 4: Execute text replacement
            self.docs_service.documents().batchUpdate(
                documentId=new_doc_id,
                body={"requests": requests}
            ).execute()

            return new_doc_id  # Returns the Google Docs file ID

        except HttpError as e:
            print(f"❌ Error creating document from template: {e}")
            raise


    def generate_view_link(self, file_id):
        """
        Generates a shareable Google Drive link to view the Google Doc file.
        """
        try:
            # ✅ Set file permissions to allow viewing
            self.drive_service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
                fields="id"
            ).execute()

            # ✅ Get the file's view link
            file = self.drive_service.files().get(fileId=file_id, fields="webViewLink").execute()
            return file.get("webViewLink")

        except HttpError as e:
            print(f"Error generating view link: {e}")
            return None


class GoogleDriveAPI:
    """
    Handles Google Drive operations such as retrieving templates and organizing files.
    """

    def __init__(self, service):
        self.service = service

    def get_template_id(self, template_name):
        """
        Find the template file ID in Google Drive by name.
        Searches for both Google Docs and .docx formats.
        """
        try:
            query = f"(name='{template_name}' and mimeType='application/vnd.google-apps.document')"  # Google Docs format
            
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)'
            ).execute()

            return response['files'][0]['id']
        
        except (KeyError, IndexError):
            raise ValueError(f"Template '{template_name}' not found in Google Drive")


    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Creates a folder in Google Drive if it doesn't already exist.
        """
        try:
            # ✅ Check if the folder already exists
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"

            existing = self.service.files().list(
                q=query,
                fields='files(id)'
            ).execute().get('files', [])

            if existing:
                return existing[0]['id']  # Return existing folder ID

            # ✅ Create a new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id] if parent_folder_id else []
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            return folder['id']

        except HttpError as e:
            print(f"Folder creation failed: {e}")
            raise



# class GoogleDocsHelper:
#     """
#     Handles Google Docs integration using template-based approach
#     """
    
#     def __init__(self, docs_service, drive_service):
#         if not isinstance(docs_service, Resource) or not isinstance(drive_service, Resource):
#             raise ValueError("Requires valid Docs and Drive service instances")
#         self.docs_service = docs_service
#         self.drive_service = drive_service

#     def create_from_template(self, template_id, replacements, document_name="New Document"):
#         """
#         Creates document from template with placeholder replacements
#         """
#         try:
#             # Copy template file
#             new_file = self.drive_service.files().copy(
#                 fileId=template_id,
#                 body={'name': document_name}
#             ).execute()
#             new_doc_id = new_file['id']

#             # Build replacement requests
#             requests = []
#             for placeholder, content in replacements.items():
#                 requests.append({
#                     'replaceAllText': {
#                         'containsText': {
#                             'text': f'{{{placeholder}}}',
#                             'matchCase': True
#                         },
#                         'replaceText': content
#                     }
#                 })

#             # Execute batch update
#             self.docs_service.documents().batchUpdate(
#                 documentId=new_doc_id,
#                 body={'requests': requests}
#             ).execute()

#             return new_doc_id

#         except HttpError as e:
#             print(f"Template processing failed: {e}")
#             raise

#     def update_template_content(self, doc_id, replacements):
#         """
#         Updates existing document with new content using template placeholders
#         """
#         try:
#             requests = []
#             for placeholder, content in replacements.items():
#                 requests.append({
#                     'replaceAllText': {
#                         'containsText': {
#                             'text': f'{{{placeholder}}}',
#                             'matchCase': True
#                         },
#                         'replaceText': content
#                     }
#                 })

#             self.docs_service.documents().batchUpdate(
#                 documentId=doc_id,
#                 body={'requests': requests}
#             ).execute()

#         except HttpError as e:
#             print(f"Document update failed: {e}")
#             raise

# class GoogleDriveAPI:
#     def __init__(self, service):
#         self.service = service

#     def create_template_document(self, template_name="ProposalTemplate"):
#         """Create a properly formatted template document with placeholders"""
#         try:
#             # Create empty document
#             doc_service = build('docs', 'v1', credentials=self.service._http.credentials)
#             document = doc_service.documents().create(body={'title': template_name}).execute()
#             doc_id = document['documentId']
            
#             # Build template content with proper request separation
#             requests = [
#                 # Document title
#                 {
#                     'insertText': {
#                         'location': {'index': 1},
#                         'text': "Proposal Template\n"
#                     }
#                 },
#                 {
#                     'updateParagraphStyle': {
#                         'range': {'startIndex': 1, 'endIndex': 17},
#                         'paragraphStyle': {'namedStyleType': 'TITLE'},
#                         'fields': 'namedStyleType'
#                     }
#                 },
                
#                 # Header section
#                 {
#                     'insertText': {
#                         'location': {'index': 2},
#                         'text': "{{HEADER}}\n"
#                     }
#                 },
                
#                 # RFQ Number
#                 {
#                     'insertText': {
#                         'location': {'index': 3},
#                         'text': "Proposal for RFQ No. {{RFQ_NUMBER}}\n"
#                     }
#                 },
#                 {
#                     'updateParagraphStyle': {
#                         'range': {'startIndex': 3, 'endIndex': 3 + len("Proposal for RFQ No. {{RFQ_NUMBER}}") + 1},
#                         'paragraphStyle': {'namedStyleType': 'HEADING_1'},
#                         'fields': 'namedStyleType'
#                     }
#                 },
                
#                 # Executive Summary
#                 {
#                     'insertText': {
#                         'location': {'index': 4},
#                         'text': "Executive Summary\n{{EXECUTIVE_SUMMARY}}\n\n"
#                     }
#                 },
                
#                 # Scope of Work
#                 {
#                     'insertText': {
#                         'location': {'index': 5},
#                         'text': "Scope of Work\n{{SCOPE_OF_WORK}}\n\n"
#                     }
#                 },
                
#                 # Timeline Table
#                 {
#                     'insertText': {
#                         'location': {'index': 6},
#                         'text': "Project Timeline\n{{TIMELINE_TABLE}}\n\n"
#                     }
#                 },
                
#                 # Contact Info
#                 {
#                     'insertText': {
#                         'location': {'index': 7},
#                         'text': "Contact Information\n{{CONTACT_INFO}}\n"
#                     }
#                 }
#             ]
            
#             # Execute batch update
#             doc_service.documents().batchUpdate(
#                 documentId=doc_id,
#                 body={'requests': requests}
#             ).execute()
            
#             return doc_id
            
#         except Exception as e:
#             raise RuntimeError(f"Template creation failed: {str(e)}")

#     def _create_heading_request(self, text, level):
#         return {
#             'insertText': {
#                 'location': {'index': 1},
#                 'text': f'{text}\n'
#             },
#             'updateParagraphStyle': {
#                 'range': {'startIndex': 1, 'endIndex': len(text)+2},
#                 'paragraphStyle': {'namedStyleType': f'HEADING_{level}'},
#                 'fields': 'namedStyleType'
#             }
#         }

#     def _create_section_request(self, title, placeholder):
#         return {
#             'insertText': {
#                 'location': {'index': 1},
#                 'text': f'{title}\n{placeholder}\n\n'
#             }
#         }

#     def _create_table_request(self, title, placeholder):
#         return {
#             'insertText': {
#                 'location': {'index': 1},
#                 'text': f'{title}\n{placeholder}\n\n'
#             }
#         }

#     def get_or_create_template(self, template_name="ProposalTemplate"):
#         """Self-healing template retrieval with error handling"""
#         try:
#             template_id = self.create_template_document(template_name)
            
#             # Move to templates folder
#             templates_folder_id = self.create_folder("ProposalTemplates")
#             self.service.files().update(
#                 fileId=template_id,
#                 addParents=templates_folder_id,
#                 removeParents='root',
#                 fields='id, parents'
#             ).execute()
            
#             return template_id
                
#         except Exception as e:
#             return None
        
#     def get_template_id(self, template_name):
#         """Find template ID by name"""
#         try:
#             response = self.service.files().list(
#                 q=f"name='{template_name}' and mimeType='application/vnd.google-apps.document'",
#                 spaces='drive',
#                 fields='files(id, name)'
#             ).execute()
#             return response['files'][0]['id']
#         except (KeyError, IndexError):
#             raise ValueError(f"Template '{template_name}' not found in Google Drive")

#     def create_folder(self, folder_name, parent_folder_id=None):
#         """Create folder with duplicate check"""
#         try:
#             # Check for existing folder
#             query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
#             if parent_folder_id:
#                 query += f" and '{parent_folder_id}' in parents"
                
#             existing = self.service.files().list(
#                 q=query,
#                 fields='files(id)'
#             ).execute().get('files', [])
            
#             if existing:
#                 return existing[0]['id']

#             # Create new folder
#             folder_metadata = {
#                 'name': folder_name,
#                 'mimeType': 'application/vnd.google-apps.folder',
#                 'parents': [parent_folder_id] if parent_folder_id else []
#             }
#             folder = self.service.files().create(
#                 body=folder_metadata,
#                 fields='id'
#             ).execute()
#             return folder['id']
#         except HttpError as e:
#             print(f"Folder creation failed: {e}")
#             raise