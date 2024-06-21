import os
import streamlit as st
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
import fitz  # PyMuPDF

# Database Management
import sqlite3
conn = sqlite3.connect('userdata.db')
c = conn.cursor()

# Hashing function (passlib, hashlib, bcrypt, scrypt)
import hashlib
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Function to check if hashed_password entered is same as hashed_password stored
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database Functions
def create_table():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')

def add_data(username, password):
    c.execute('INSERT INTO userstable(username, password) VALUES (?, ?)', (username, password))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password=?', (username, password))
    data = c.fetchall()
    return data

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
    except Exception as e:
        st.error(f"Error reading {pdf_path}: {e}")
    return text

# Initialize Whoosh index
index_dir = "index_dir"
if not os.path.exists(index_dir):
    os.mkdir(index_dir)

schema = Schema(filename=ID(stored=True), text=TEXT(stored=True))
index = create_in(index_dir, schema)

# Index resumes
def index_resumes(directory):
    try:
        writer = index.writer()
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                filepath = os.path.join(directory, filename)
                text = extract_text_from_pdf(filepath)
                writer.add_document(filename=filename, text=text)
        writer.commit()
    except Exception as e:
        st.error(f"Error indexing resumes: {e}")

# Search resumes with partial matching
def search_resumes(query):
    searcher = index.searcher()
    query_parser = QueryParser("text", index.schema)
    query_parser.allow_wildcard = True  # Enable wildcard queries
    
    # Split the query by commas and spaces, and handle partial matching
    keywords = [keyword.strip() + '*' for keyword in query.replace(',', ' ').split()]
    parsed_query = query_parser.parse(' OR '.join(keywords))
    results = searcher.search(parsed_query)
    return results

# Streamlit app
def main():
    st.set_page_config(page_title="HR Search Application")
    st.markdown(
        """
        <div style="background-color:#333333;padding:5px;">
        <h1 style="color:cyan">HR SEARCH APPLICATION</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    menu = ['Home', 'Login', 'SignUp', 'About']
    choice = st.sidebar.radio("Menu", menu)

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if choice == "Home":
        if st.session_state.logged_in:
            # Specify the path to your CV directory
            cv_directory = "D:/cv DIRECTORY"  # Change to your CV directory

            # Index resumes (you can run this once to create the index)
            index_resumes(cv_directory)

            # Keyword search
            keywords = st.text_input('Enter keyword(s) to search in CVs (separated by spaces or commas)')
            if keywords:
                with st.spinner("Searching..."):
                    try:
                        # Perform search
                        results = search_resumes(keywords)

                        # Display search results
                        st.write(f"Found {len(results)} CV(s) matching the search criteria:")
                        for result in results:
                            st.write(f"**Filename:** {result['filename']}")
                            st.write(f"**Preview:** {result['text'][:500]}...")  # Display first 500 characters as a preview
                    except Exception as e:
                        st.error(f"An error occurred during the search: {e}")
            else:
                st.write("Enter keyword(s) to search within the CVs.")
        else:
            st.warning("Please log in to access this page.")
    elif choice == "Login":
        st.subheader('Sign in')
        username = st.text_input("Enter your username")
        password = st.text_input("Enter your password", type='password')
        if st.checkbox("Login"):
            create_table()
            hashed_pass_init = make_hashes(password)
            result = login_user(username, check_hashes(password, hashed_pass_init))
            if result:
                st.success(f"Logged in as: {username}")
                st.session_state.logged_in = True
            else:
                st.error("Credentials not found in the database.")
    elif choice == "SignUp":
        st.subheader('Create an Account')
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type='password')
        if st.button("Sign up"):
            create_table()
            hashed_password = make_hashes(new_password)
            add_data(new_username, hashed_password)
            st.success("Account created successfully")

if __name__ == "__main__":
    main()
