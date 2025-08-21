import streamlit as st
import os
import glob
from docx import Document
import re
from datetime import datetime
import requests
from io import BytesIO

def extract_company_name_from_filename(filename):
    """Extract company name from filename like 'bajaj-auto_complete_20250819_172757.docx'"""
    # Remove file extension
    name = os.path.splitext(filename)[0]
    
    # Remove timestamp pattern (e.g., _complete_20250819_172757)
    name = re.sub(r'_complete_\d{8}_\d{6}$', '', name)
    
    # Replace hyphens and underscores with spaces and title case
    company_name = name.replace('-', ' ').replace('_', ' ').title()
    
    return company_name

def extract_data_from_docx_content(content):
    """Extract company data from DOCX text content"""
    try:
        # Extract summary info
        summary_match = re.search(r'\*\*Summary:\*\*\s*(.+?)(?:\n|\r|$)', content)
        summary = summary_match.group(1).strip() if summary_match else "No summary available"
        
        # Extract date from summary
        date_match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', summary)
        extraction_date = date_match.group(1) if date_match else "Unknown date"
        
        # Extract total links count from summary
        links_count_match = re.search(r'Total links:\s*(\d+)', summary)
        total_links_from_summary = int(links_count_match.group(1)) if links_count_match else 0
        
        # Extract text length from summary
        text_length_match = re.search(r'Text length:\s*(\d+(?:,\d+)*)', summary)
        text_length_from_summary = int(text_length_match.group(1).replace(',', '')) if text_length_match else 0
        
        # Extract links section
        links = []
        link_section_started = False
        text_section_started = False
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check for section headers
            if '# Extracted Links' in line:
                link_section_started = True
                text_section_started = False
                continue
            elif '# Extracted Text Content' in line:
                link_section_started = False
                text_section_started = True
                continue
            
            # Extract links
            if link_section_started and line.startswith('https://'):
                links.append(line)
        
        # Extract text content section
        text_content_lines = []
        text_section_started = False
        
        for line in lines:
            if '# Extracted Text Content' in line:
                text_section_started = True
                continue
            
            if text_section_started and line.strip():
                # Clean up the line (remove backslashes and extra formatting)
                cleaned_line = line.replace('\\', '').strip()
                if cleaned_line:
                    text_content_lines.append(cleaned_line)
        
        text_content = '\n\n'.join(text_content_lines)
        
        return {
            'summary': summary,
            'extraction_date': extraction_date,
            'links': links,
            'text_content': text_content,
            'total_links': len(links),
            'total_links_from_summary': total_links_from_summary,
            'text_length': len(text_content),
            'text_length_from_summary': text_length_from_summary
        }
        
    except Exception as e:
        st.error(f"Error processing content: {str(e)}")
        return None

def extract_data_from_docx_file(file_path):
    """Extract company data from DOCX file"""
    try:
        # Read the document
        if isinstance(file_path, str):
            doc = Document(file_path)
        else:
            # If it's a BytesIO object (from URL)
            doc = Document(file_path)
        
        # Get full text
        full_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                full_text.append(paragraph.text)
        
        content = '\n'.join(full_text)
        return extract_data_from_docx_content(content)
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def load_docx_files_from_directory(directory_path):
    """Load all DOCX files from a directory"""
    docx_files = glob.glob(os.path.join(directory_path, "*.docx"))
    company_data = []
    
    for file_path in docx_files:
        filename = os.path.basename(file_path)
        company_name = extract_company_name_from_filename(filename)
        
        data = extract_data_from_docx_file(file_path)
        if data:
            company_data.append({
                'company_name': company_name,
                'filename': filename,
                'file_path': file_path,
                **data
            })
    
    return company_data

def load_docx_from_github(github_raw_urls):
    """Load DOCX files from GitHub raw URLs"""
    company_data = []
    
    for url in github_raw_urls:
        try:
            # Extract filename from URL
            filename = url.split('/')[-1]
            company_name = extract_company_name_from_filename(filename)
            
            # Download file
            response = requests.get(url)
            response.raise_for_status()
            
            # Create BytesIO object
            docx_file = BytesIO(response.content)
            
            # Extract data
            data = extract_data_from_docx_file(docx_file)
            if data:
                company_data.append({
                    'company_name': company_name,
                    'filename': filename,
                    'github_url': url,
                    **data
                })
                
        except Exception as e:
            st.error(f"Error loading {url}: {str(e)}")
    
    return company_data

def display_company_card(company_info):
    """Display a beautiful card for each company"""
    
    # Create an expandable card with company name and key metrics
    with st.expander(
        f"🏢 **{company_info['company_name']}** | 🔗 {company_info['total_links']} Links | 📝 {company_info['text_length']:,} chars", 
        expanded=False
    ):
        
        # Header info
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**📄 File:** `{company_info['filename']}`")
            if 'extraction_date' in company_info:
                st.markdown(f"**📅 Extracted:** {company_info['extraction_date']}")
        with col2:
            # Validation check
            if company_info['total_links'] != company_info.get('total_links_from_summary', 0):
                st.warning(f"⚠️ Link count mismatch: Found {company_info['total_links']}, Expected {company_info.get('total_links_from_summary', 0)}")
        
        st.markdown("---")
        
        # Summary information
        st.markdown("### 📋 Document Summary")
        st.info(company_info['summary'])
        
        # Links section
        st.markdown(f"### 🔗 Extracted Links ({company_info['total_links']} total)")
        
        if company_info['links']:
            # Create tabs for better organization if many links
            if len(company_info['links']) > 10:
                tab1, tab2 = st.tabs(["📋 Links List", "🔍 Quick View"])
                
                with tab1:
                    for i, link in enumerate(company_info['links'], 1):
                        # Extract domain for better display
                        domain = re.search(r'https?://(?:www\.)?([^/]+)', link)
                        domain_name = domain.group(1) if domain else "Unknown"
                        
                        st.markdown(f"**{i}.** [{domain_name}]({link})")
                        
                with tab2:
                    # Show links in a more compact format
                    for i, link in enumerate(company_info['links'], 1):
                        st.markdown(f"{i}. {link}")
            else:
                for i, link in enumerate(company_info['links'], 1):
                    # Extract domain for better display
                    domain = re.search(r'https?://(?:www\.)?([^/]+)', link)
                    domain_name = domain.group(1) if domain else "Unknown"
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{i}.** [{domain_name}]({link})")
                    with col2:
                        if st.button("🔗 Open", key=f"open_{company_info['filename']}_{i}"):
                            st.markdown(f"[Open in new tab]({link})")
        else:
            st.warning("No links found")
        
        # Text content section
        st.markdown("### 📖 Extracted Text Content")
        if company_info['text_content']:
            # Clean display of text content
            text_content = company_info['text_content']
            
            # Show character count
            st.caption(f"📊 {len(text_content):,} characters")
            
            # Text content in expandable section if long
            if len(text_content) > 1000:
                with st.expander("📖 Click to read full content", expanded=False):
                    st.markdown(text_content)
                
                # Show preview
                st.markdown("**Preview (first 500 characters):**")
                st.text_area(
                    "Content Preview",
                    value=text_content[:500] + "..." if len(text_content) > 500 else text_content,
                    height=150,
                    disabled=True,
                    label_visibility="collapsed"
                )
            else:
                st.markdown(text_content)
        else:
            st.warning("No text content found")
        
        # Download section
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if 'github_url' in company_info:
                st.markdown(f"[📥 Download Original]({company_info['github_url']})")
        with col2:
            # Copy links button
            links_text = '\n'.join([f"{i+1}. {link}" for i, link in enumerate(company_info['links'])])
            st.download_button(
                "📋 Copy All Links",
                data=links_text,
                file_name=f"{company_info['company_name']}_links.txt",
                mime="text/plain",
                key=f"copy_links_{company_info['filename']}"
            )
        with col3:
            # Copy text content button
            st.download_button(
                "📄 Copy Text Content",
                data=company_info['text_content'],
                file_name=f"{company_info['company_name']}_content.txt",
                mime="text/plain",
                key=f"copy_text_{company_info['filename']}"
            )

def main():
    # Page configuration
    st.set_page_config(
        page_title="Company Research Dashboard",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 16px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Company Research Dashboard</h1>
        <p>View extracted company data, links, and insights from DOCX files</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.header("⚙️ Configuration")
    
    # Data source selection
    data_source = st.sidebar.selectbox(
        "Choose data source:",
        ["Sample Data (Demo)", "GitHub Repository", "Local Directory"]
    )
    
    company_data = []
    
    if data_source == "GitHub Repository":
        st.sidebar.markdown("### 🔧 GitHub Configuration")
        
        # GitHub repository URL input
        repo_url = st.sidebar.text_input(
            "GitHub Repository URL:",
            placeholder="https://github.com/username/repo",
            help="Enter the GitHub repository URL containing DOCX files"
        )
        
        # Data folder path
        data_folder = st.sidebar.text_input(
            "Data Folder Path:",
            value="data/",
            help="Folder path within the repo containing DOCX files (include trailing slash)"
        )
        
        if repo_url:
            # Convert GitHub URL to raw URLs
            if "github.com" in repo_url:
                # Convert to raw.githubusercontent.com format
                raw_base = repo_url.replace("github.com", "raw.githubusercontent.com")
                if "/tree/" in raw_base:
                    raw_base = raw_base.replace("/tree/", "/")
                elif not raw_base.endswith("/main") and not raw_base.endswith("/master"):
                    if not raw_base.endswith("/"):
                        raw_base += "/"
                    raw_base += "main/"
                
                if not raw_base.endswith("/"):
                    raw_base += "/"
                
                st.sidebar.info("📝 List your DOCX filenames below")
                
                docx_filenames = st.sidebar.text_area(
                    "DOCX Filenames (one per line):",
                    value="bajaj-auto_complete_20250819_172757.docx",
                    help="List your DOCX filenames, one per line"
                )
                
                if docx_filenames.strip():
                    filenames = [f.strip() for f in docx_filenames.split('\n') if f.strip()]
                    github_urls = [f"{raw_base}{data_folder}{filename}" for filename in filenames]
                    
                    with st.spinner("🔄 Loading data from GitHub..."):
                        company_data = load_docx_from_github(github_urls)
    
    elif data_source == "Local Directory":
        directory_path = st.sidebar.text_input(
            "Local Directory Path:",
            placeholder="/path/to/your/docx/files",
            help="Enter the full path to directory containing DOCX files"
        )
        
        if directory_path and os.path.exists(directory_path):
            with st.spinner("🔄 Loading local files..."):
                company_data = load_docx_files_from_directory(directory_path)
        elif directory_path:
            st.sidebar.error("❌ Directory not found")
    
    else:  # Sample Data
        st.info("🚀 Showing sample data based on your Bajaj Auto DOCX format")
        
        # Sample data based on your actual Bajaj Auto example
        sample_content = """**Summary:** Total links: 19, Text length: 2,306 characters, Date: 2025-08-19 17:27:57

# Extracted Links

Link 1:
https://www.storyboard18.com/brand-makers/bajaj-auto-sales-surge-8-in-may-2025-exports-drive-growth-68329.htm

Link 2:
https://www.nseindia.com/get-quotes/equity?symbol=BAJAJ-AUTO

Link 3:
https://ackodrive.com/news/auto-sales-may-2025-bajaj-s-export-continues-to-drive-growth/

# Extracted Text Content

Bajaj Auto reported an 8% increase in total sales (including exports) in May 2025 compared to May 2024, reaching 3,84,621 units.

Exports were a key driver of this growth, surging by 22% year-on-year to 1,58,888 vehicles in May 2025."""
        
        sample_data = extract_data_from_docx_content(sample_content)
        if sample_data:
            company_data = [{
                'company_name': 'Bajaj Auto',
                'filename': 'bajaj-auto_complete_20250819_172757.docx',
                **sample_data
            }]
    
    # Main content
    if company_data:
        # Statistics
        st.markdown("## 📊 Dashboard Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏢 Companies", len(company_data))
        with col2:
            total_links = sum(comp['total_links'] for comp in company_data)
            st.metric("🔗 Total Links", total_links)
        with col3:
            avg_links = total_links / len(company_data) if company_data else 0
            st.metric("📈 Avg Links/Company", f"{avg_links:.1f}")
        with col4:
            total_text = sum(comp['text_length'] for comp in company_data)
            st.metric("📝 Total Characters", f"{total_text:,}")
        
        st.markdown("---")
        
        # Search functionality
        search_term = st.text_input(
            "🔍 Search companies:",
            placeholder="Enter company name to filter...",
            help="Search by company name"
        )
        
        # Filter companies
        filtered_data = company_data
        if search_term:
            filtered_data = [
                comp for comp in company_data 
                if search_term.lower() in comp['company_name'].lower()
            ]
        
        # Sort options
        sort_option = st.selectbox(
            "📊 Sort by:",
            ["Company Name", "Number of Links (High to Low)", "Number of Links (Low to High)", "Text Length (High to Low)"]
        )
        
        if sort_option == "Company Name":
            filtered_data = sorted(filtered_data, key=lambda x: x['company_name'])
        elif sort_option == "Number of Links (High to Low)":
            filtered_data = sorted(filtered_data, key=lambda x: x['total_links'], reverse=True)
        elif sort_option == "Number of Links (Low to High)":
            filtered_data = sorted(filtered_data, key=lambda x: x['total_links'])
        elif sort_option == "Text Length (High to Low)":
            filtered_data = sorted(filtered_data, key=lambda x: x['text_length'], reverse=True)
        
        # Display results
        st.markdown(f"## 📋 Company Data ({len(filtered_data)} companies)")
        
        if filtered_data:
            for company_info in filtered_data:
                display_company_card(company_info)
        else:
            st.warning("🔍 No companies found matching your search criteria")
            
    else:
        st.markdown("## 🚀 Get Started")
        st.markdown("""
        ### How to use this dashboard:
        
        1. **📊 Sample Data (Demo):**
           - See how the dashboard works with your exact DOCX format
           - Perfect for testing and demonstrations
        
        2. **🌐 GitHub Repository (Recommended for sharing):**
           - Upload your DOCX files to a GitHub repository
           - Enter the repository URL in the sidebar
           - List your DOCX filenames
           - Deploy to Streamlit Cloud and share the URL!
        
        3. **💻 Local Directory:**
           - For testing with local files
           - Enter the path to your DOCX files folder
        
        ### ✅ Expected DOCX format:
        Your DOCX files should contain exactly what you showed:
        - **Summary** section with total links, text length, and date
        - **Extracted Links** section with numbered URLs
        - **Extracted Text Content** section with the main content
        
        ### 🚀 Ready to deploy?
        1. Create a GitHub repository
        2. Add your DOCX files to a `data/` folder
        3. Add this code as `app.py`
        4. Deploy on [Streamlit Cloud](https://share.streamlit.io)
        5. Share your public URL with others!
        """)

if __name__ == "__main__":
    main()