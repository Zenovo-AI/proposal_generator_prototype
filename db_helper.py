import sqlite3

# Create a connection to the database
conn = sqlite3.connect('files.db', check_same_thread=False)

# Mapping of sections to tables
SECTION_TO_TABLE_MAPPING = {
    "Request for Proposal (RFP) Document": "rfp_documents",
    "Terms of Reference (ToR)": "tor_documents",
    "Technical Evaluation Criteria": "evaluation_criteria_documents",
    "Company and Team Profiles": "company_profiles_documents",
    "Environmental and Social Standards": "social_standards_documents",
    "Project History and Relevant Experience": "project_history_documents",
    "Additional Requirements and Compliance Documents": "additional_requirements_documents",
}

# Function to create table
def create_table(section):
    table_name = SECTION_TO_TABLE_MAPPING.get(section)
    if not table_name:
        raise ValueError(f"No table mapping found for section: {section}")
    
    with conn:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (file_name TEXT)")
        
        
# Function to initialize the database tables (for the first run)
def initialize_database():
    for section in SECTION_TO_TABLE_MAPPING.keys():
        create_table(section)

# Function to insert file metadata into database
def insert_file_metadata(file_name, section):
    try:
        create_table(section)
        table_name = SECTION_TO_TABLE_MAPPING.get(section)
        if not table_name:
            raise ValueError(f"No table mapping found for section: {section}")
        
        with conn:
            conn.execute(f"INSERT INTO {table_name} (file_name) VALUES (?)", (file_name,))
    except Exception as e:
        raise Exception(f"Error inserting file metadata: {e}")

# Function to delete file from database
def delete_file(file_name, section):
    try:
        table_name = SECTION_TO_TABLE_MAPPING.get(section)
        if not table_name:
            raise ValueError(f"No table mapping found for section: {section}")
        
        with conn:
            conn.execute(f"DELETE FROM {table_name} WHERE file_name = ?", (file_name,))
    except Exception as e:
        raise Exception(f"Error deleting file: {e}")
    
# Function to get the list of files from a section
def get_uploaded_files(section):
    table_name = SECTION_TO_TABLE_MAPPING.get(section)
    if not table_name:
        raise ValueError(f"No table mapping found for section: {section}")
    
    cursor = conn.cursor()
    cursor.execute(f"SELECT file_name FROM {table_name}")
    return cursor.fetchall()
