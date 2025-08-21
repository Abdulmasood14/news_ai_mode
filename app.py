import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

# Page configuration
st.set_page_config(
    page_title="Company Scraper Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .company-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
        cursor: pointer;
    }
    
    .company-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    .card-title {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    .card-stats {
        font-size: 14px;
        opacity: 0.9;
    }
    
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 30px;
    }
    
    .section-header {
        color: #2E86AB;
        border-bottom: 2px solid #2E86AB;
        padding-bottom: 5px;
        margin-top: 20px;
        margin-bottom: 15px;
    }
    
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin: 5px;
    }
    
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class CompanyDataProcessor:
    def __init__(self, csv_directory="scraper_csv_outputs"):
        self.csv_directory = csv_directory
        self.companies_data = {}
        self.load_all_company_data()
    
    def load_all_company_data(self):
        """Load data from all CSV files in the directory"""
        if not os.path.exists(self.csv_directory):
            st.error(f"Directory '{self.csv_directory}' not found!")
            return
        
        csv_files = glob.glob(os.path.join(self.csv_directory, "*.csv"))
        
        for csv_file in csv_files:
            try:
                company_name = self.extract_company_name(csv_file)
                data = self.parse_csv_file(csv_file)
                if data:
                    self.companies_data[company_name] = data
                    self.companies_data[company_name]['filename'] = os.path.basename(csv_file)
            except Exception as e:
                st.error(f"Error loading {csv_file}: {str(e)}")
    
    def extract_company_name(self, csv_file):
        """Extract company name from CSV filename"""
        filename = os.path.basename(csv_file)
        # Remove timestamp and extension
        company_name = re.sub(r'_complete_\d{8}_\d{6}\.csv$', '', filename)
        return company_name.upper()
    
    def parse_csv_file(self, csv_file):
        """Parse CSV file and extract structured data"""
        try:
            # Read the entire CSV file
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            data = {
                'summary': {},
                'links': [],
                'text_content': '',
                'file_path': csv_file,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(csv_file))
            }
            
            # Parse different sections
            current_section = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if not line:
                    continue
                
                # Parse CSV using pandas for proper handling
                if line.startswith('Company,'):
                    # Summary section
                    df_summary = pd.read_csv(csv_file, nrows=2)
                    if len(df_summary) > 1:
                        data['summary'] = {
                            'company': df_summary.iloc[1]['Company'],
                            'total_links': df_summary.iloc[1]['Total_Links'],
                            'text_length': df_summary.iloc[1]['Text_Length_Characters'],
                            'extraction_date': df_summary.iloc[1]['Extraction_Date'],
                            'status': df_summary.iloc[1]['Status']
                        }
                elif line == 'EXTRACTED_LINKS':
                    current_section = 'links'
                elif line == 'EXTRACTED_TEXT_CONTENT':
                    current_section = 'text'
                elif current_section == 'links' and ',' in line and not line.startswith('Link_Number'):
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        data['links'].append({
                            'number': parts[0],
                            'url': parts[1].strip('"')
                        })
                elif current_section == 'text' and ',' in line and not line.startswith('Content_Type'):
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        content = parts[1].strip('"')
                        if data['text_content']:
                            data['text_content'] += '\n\n' + content
                        else:
                            data['text_content'] = content
            
            return data
            
        except Exception as e:
            st.error(f"Error parsing {csv_file}: {str(e)}")
            return None
    
    def get_companies_list(self):
        """Get list of all companies"""
        return list(self.companies_data.keys())
    
    def get_company_data(self, company_name):
        """Get data for specific company"""
        return self.companies_data.get(company_name)
    
    def get_summary_stats(self):
        """Get overall summary statistics"""
        total_companies = len(self.companies_data)
        total_links = sum(len(data['links']) for data in self.companies_data.values())
        total_text_length = sum(len(data['text_content']) for data in self.companies_data.values())
        
        successful = sum(1 for data in self.companies_data.values() 
                        if data.get('summary', {}).get('status') == 'Completed')
        
        return {
            'total_companies': total_companies,
            'successful_extractions': successful,
            'total_links': total_links,
            'total_text_length': total_text_length,
            'success_rate': (successful / total_companies * 100) if total_companies > 0 else 0
        }

def main():
    # Initialize data processor
    processor = CompanyDataProcessor()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Dashboard", "Company Details"])
    
    if page == "Dashboard":
        show_dashboard(processor)
    elif page == "Company Details":
        show_company_details(processor)

def show_dashboard(processor):
    """Display main dashboard with company cards"""
    st.markdown("<h1 class='main-header'>Company Data Scraper Dashboard</h1>", unsafe_allow_html=True)
    
    # Summary statistics
    stats = processor.get_summary_stats()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Companies", stats['total_companies'])
    
    with col2:
        st.metric("Successful Extractions", stats['successful_extractions'])
    
    with col3:
        st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
    
    with col4:
        st.metric("Total Links", f"{stats['total_links']:,}")
    
    with col5:
        st.metric("Total Text Length", f"{stats['total_text_length']:,}")
    
    st.markdown("---")
    
    # Company cards
    st.markdown("<h2 class='section-header'>Company Data Cards</h2>", unsafe_allow_html=True)
    
    companies = processor.get_companies_list()
    
    if not companies:
        st.warning("No company data found. Please ensure CSV files are in the 'scraper_csv_outputs' directory.")
        return
    
    # Create cards in grid layout
    cols_per_row = 3
    for i in range(0, len(companies), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, company in enumerate(companies[i:i+cols_per_row]):
            with cols[j]:
                data = processor.get_company_data(company)
                
                # Determine status color
                status = data.get('summary', {}).get('status', 'Unknown')
                if status == 'Completed':
                    status_class = 'status-success'
                elif 'Error' in status:
                    status_class = 'status-error'
                else:
                    status_class = 'status-warning'
                
                # Create card
                card_html = f"""
                <div class="company-card">
                    <div class="card-title">{company}</div>
                    <div class="card-stats">
                        <p>Status: <span class="{status_class}">{status}</span></p>
                        <p>Links: {len(data.get('links', []))}</p>
                        <p>Text Length: {len(data.get('text_content', '')):,} chars</p>
                        <p>Updated: {data.get('last_modified', 'Unknown').strftime('%Y-%m-%d') if hasattr(data.get('last_modified'), 'strftime') else 'Unknown'}</p>
                    </div>
                </div>
                """
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Button to view details
                if st.button(f"View Details", key=f"btn_{company}"):
                    st.session_state.selected_company = company
                    st.session_state.page = "Company Details"
                    st.rerun()

def show_company_details(processor):
    """Display detailed view for selected company"""
    
    # Company selector
    companies = processor.get_companies_list()
    if not companies:
        st.error("No company data available")
        return
    
    selected_company = st.selectbox("Select Company", companies, 
                                   index=companies.index(st.session_state.get('selected_company', companies[0])) 
                                   if st.session_state.get('selected_company') in companies else 0)
    
    if st.button("← Back to Dashboard"):
        st.session_state.page = "Dashboard"
        st.rerun()
    
    data = processor.get_company_data(selected_company)
    
    if not data:
        st.error(f"No data found for {selected_company}")
        return
    
    # Company header
    st.markdown(f"<h1 class='main-header'>{selected_company} - Detailed View</h1>", unsafe_allow_html=True)
    
    # Summary information
    st.markdown("<h3 class='section-header'>Summary Information</h3>", unsafe_allow_html=True)
    
    summary = data.get('summary', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status", summary.get('status', 'Unknown'))
    with col2:
        st.metric("Total Links", summary.get('total_links', 0))
    with col3:
        st.metric("Text Length", f"{summary.get('text_length', 0):,}")
    with col4:
        st.metric("Extraction Date", summary.get('extraction_date', 'Unknown'))
    
    # Extracted Links Section
    st.markdown("<h3 class='section-header'>Extracted Links</h3>", unsafe_allow_html=True)
    
    links = data.get('links', [])
    if links:
        # Create DataFrame for links
        links_df = pd.DataFrame(links)
        
        # Search functionality
        search_term = st.text_input("Search links", placeholder="Enter URL or keyword to search...")
        
        if search_term:
            filtered_links = [link for link in links if search_term.lower() in link['url'].lower()]
        else:
            filtered_links = links
        
        st.write(f"Showing {len(filtered_links)} of {len(links)} links")
        
        # Display links in expandable format
        for link in filtered_links:
            with st.expander(f"{link['number']}: {link['url'][:100]}..."):
                st.markdown(f"**Full URL:** {link['url']}")
                st.markdown(f"[Open Link]({link['url']})")
        
        # Download links as CSV
        if st.button("Download Links as CSV"):
            csv_data = pd.DataFrame(links).to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{selected_company}_links.csv",
                mime="text/csv"
            )
    else:
        st.info("No links found for this company")
    
    # Extracted Text Content Section
    st.markdown("<h3 class='section-header'>Extracted Text Content</h3>", unsafe_allow_html=True)
    
    text_content = data.get('text_content', '')
    if text_content:
        # Text search
        text_search = st.text_input("Search in text content", placeholder="Enter keyword to search in text...")
        
        if text_search:
            # Highlight search terms
            highlighted_text = text_content.replace(
                text_search, 
                f"**{text_search}**"
            )
            st.markdown(highlighted_text)
        else:
            st.text_area("Content", text_content, height=400)
        
        # Text statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Characters", len(text_content))
        with col2:
            st.metric("Words", len(text_content.split()))
        with col3:
            st.metric("Lines", len(text_content.split('\n')))
        
        # Download text content
        if st.button("Download Text Content"):
            st.download_button(
                label="Download Text",
                data=text_content,
                file_name=f"{selected_company}_content.txt",
                mime="text/plain"
            )
    else:
        st.info("No text content found for this company")
    
    # Raw CSV Download
    st.markdown("<h3 class='section-header'>Raw Data</h3>", unsafe_allow_html=True)
    
    if os.path.exists(data['file_path']):
        with open(data['file_path'], 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        st.download_button(
            label="Download Complete CSV File",
            data=csv_content,
            file_name=data['filename'],
            mime="text/csv"
        )

if __name__ == "__main__":
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    main()
