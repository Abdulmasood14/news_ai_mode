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
        """Parse CSV file and extract structured data - FIXED FOR YOUR FORMAT"""
        try:
            # Read the entire CSV file
            with open(csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = {
                'summary': {},
                'links': [],
                'text_content': '',
                'file_path': csv_file,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(csv_file))
            }
            
            # Split into lines and remove Windows line endings
            lines = [line.rstrip('\r') for line in content.split('\n')]
            
            # Parse summary section
            if len(lines) >= 2 and lines[0].startswith('Company,Total_Links,Text_Length_Characters'):
                summary_parts = lines[1].split(',')
                if len(summary_parts) >= 5:
                    data['summary'] = {
                        'company': summary_parts[0],
                        'total_links': int(summary_parts[1]) if summary_parts[1].isdigit() else 0,
                        'text_length': int(summary_parts[2]) if summary_parts[2].isdigit() else 0,
                        'extraction_date': summary_parts[3],
                        'status': summary_parts[4]
                    }
            
            # Find section boundaries
            links_start = None
            text_start = None
            
            for i, line in enumerate(lines):
                if line.strip() == 'EXTRACTED_LINKS':
                    links_start = i
                elif line.strip() == 'EXTRACTED_TEXT_CONTENT':
                    text_start = i
            
            # Parse links section
            if links_start is not None:
                # Start from the line after "Link_Number,URL"
                links_data_start = links_start + 2
                links_end = text_start if text_start else len(lines)
                
                for i in range(links_data_start, links_end):
                    line = lines[i].strip()
                    if line and ',' in line:
                        # Parse CSV line properly
                        import csv
                        from io import StringIO
                        try:
                            csv_reader = csv.reader(StringIO(line))
                            parts = next(csv_reader, [])
                            if len(parts) >= 2:
                                data['links'].append({
                                    'number': parts[0],
                                    'url': parts[1]
                                })
                        except:
                            # Fallback parsing
                            comma_pos = line.find(',')
                            if comma_pos > 0:
                                link_num = line[:comma_pos]
                                link_url = line[comma_pos + 1:].strip('"')
                                data['links'].append({
                                    'number': link_num,
                                    'url': link_url
                                })
            
            # Parse text content section - THIS IS THE KEY FIX
            if text_start is not None:
                # Start from the line after "Content_Type,Content"
                text_data_start = text_start + 2
                text_lines = []
                
                # Collect all text content lines
                in_text_block = False
                current_text = ""
                
                for i in range(text_data_start, len(lines)):
                    line = lines[i]
                    
                    # Handle the first line which starts with "Complete_Text,"
                    if line.startswith('Complete_Text,'):
                        # Extract the text after the comma
                        text_part = line[len('Complete_Text,'):].strip('"')
                        current_text = text_part
                        in_text_block = True
                    elif in_text_block:
                        # This is continuation of the text content
                        if line.strip():  # Non-empty line
                            if line.strip() == '""':  # End marker
                                break
                            current_text += "\n\n" + line.strip()
                        else:
                            # Empty line - add as paragraph break
                            if current_text and not current_text.endswith("\n\n"):
                                current_text += "\n\n"
                
                # Clean up the text content
                if current_text:
                    # Remove trailing quote if present
                    current_text = current_text.rstrip('"')
                    data['text_content'] = current_text
            
            # If still no text content, try alternative extraction
            if not data['text_content']:
                self.extract_text_alternative(lines, data, text_start)
            
            return data
            
        except Exception as e:
            st.error(f"Error parsing {csv_file}: {str(e)}")
            return self.create_fallback_data(csv_file)
    
    def extract_text_alternative(self, lines, data, text_start):
        """Alternative text extraction method"""
        try:
            if text_start is None:
                return
            
            # Find all meaningful content after EXTRACTED_TEXT_CONTENT
            meaningful_lines = []
            
            for i in range(text_start + 1, len(lines)):
                line = lines[i].strip()
                
                # Skip headers and empty lines
                if (line and 
                    not line.startswith('Content_Type,') and
                    not line.startswith('Complete_Text,') and
                    len(line) > 10):
                    
                    # Clean the line
                    clean_line = line.strip('"').strip(',')
                    if clean_line:
                        meaningful_lines.append(clean_line)
            
            if meaningful_lines:
                data['text_content'] = '\n\n'.join(meaningful_lines)
        
        except Exception as e:
            pass
    
    def create_fallback_data(self, csv_file):
        """Create fallback data structure"""
        return {
            'summary': {
                'company': 'Error',
                'total_links': 0,
                'text_length': 0,
                'extraction_date': 'Unknown',
                'status': 'Parse Error'
            },
            'links': [],
            'text_content': 'Failed to parse CSV file',
            'file_path': csv_file,
            'last_modified': datetime.fromtimestamp(os.path.getmtime(csv_file))
        }
    
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
        total_text_length = sum(len(str(data['text_content'])) for data in self.companies_data.values())
        
        successful = sum(1 for data in self.companies_data.values() 
                        if str(data.get('summary', {}).get('status', '')).lower() == 'completed')
        
        return {
            'total_companies': total_companies,
            'successful_extractions': successful,
            'total_links': total_links,
            'total_text_length': total_text_length,
            'success_rate': (successful / total_companies * 100) if total_companies > 0 else 0
        }

def main():
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Initialize data processor
    processor = CompanyDataProcessor()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Handle button clicks from dashboard
    if st.session_state.get('selected_company'):
        st.session_state.page = "Company Details"
    
    page = st.sidebar.selectbox("Choose a page", ["Dashboard", "Company Details"], 
                               index=0 if st.session_state.page == "Dashboard" else 1)
    
    if page == "Dashboard":
        st.session_state.page = "Dashboard"
        show_dashboard(processor)
    elif page == "Company Details":
        st.session_state.page = "Company Details"
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
                
                # Safely get status and convert to string
                status_raw = data.get('summary', {}).get('status', 'Unknown')
                status = str(status_raw) if status_raw is not None else 'Unknown'
                
                # Determine status color
                if status.lower() == 'completed':
                    status_class = 'status-success'
                elif 'error' in status.lower():
                    status_class = 'status-error'
                else:
                    status_class = 'status-warning'
                
                # Get last modified date
                last_modified = data.get('last_modified', 'Unknown')
                if hasattr(last_modified, 'strftime'):
                    last_modified_str = last_modified.strftime('%Y-%m-%d')
                else:
                    last_modified_str = 'Unknown'
                
                # Create card
                card_html = f"""
                <div class="company-card">
                    <div class="card-title">{company}</div>
                    <div class="card-stats">
                        <p>Status: <span class="{status_class}">{status}</span></p>
                        <p>Links: {len(data.get('links', []))}</p>
                        <p>Text Length: {len(str(data.get('text_content', ''))):,} chars</p>
                        <p>Updated: {last_modified_str}</p>
                    </div>
                </div>
                """
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Button to view details
                if st.button(f"View Details", key=f"btn_{company}"):
                    st.session_state.selected_company = company
                    st.rerun()

def show_company_details(processor):
    """Display detailed view for selected company"""
    
    # Company selector
    companies = processor.get_companies_list()
    if not companies:
        st.error("No company data available")
        return
    
    # Default to first company if none selected
    default_company = st.session_state.get('selected_company', companies[0] if companies else None)
    if default_company not in companies:
        default_company = companies[0]
    
    selected_company = st.selectbox("Select Company", companies, 
                                   index=companies.index(default_company))
    
    if st.button("← Back to Dashboard"):
        st.session_state.page = "Dashboard"
        if 'selected_company' in st.session_state:
            del st.session_state.selected_company
        st.rerun()
    
    data = processor.get_company_data(selected_company)
    
    if not data:
        st.error(f"No data found for {selected_company}")
        return
    
    # Enhanced Debug section
    with st.expander("Debug Information (Click to expand)", expanded=False):
        st.write("Raw data structure:")
        st.json({
            'summary': data.get('summary', {}),
            'links_count': len(data.get('links', [])),
            'text_content_length': len(str(data.get('text_content', ''))),
            'text_content_preview': str(data.get('text_content', ''))[:500] + "..." if len(str(data.get('text_content', ''))) > 500 else str(data.get('text_content', ''))
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Show Raw CSV Content"):
                try:
                    with open(data['file_path'], 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    st.text_area("Raw CSV File Content", raw_content, height=300)
                except Exception as e:
                    st.error(f"Could not read file: {e}")
        
        with col2:
            if st.button("Re-parse with Alternative Method"):
                # Force alternative parsing
                try:
                    with open(data['file_path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract all meaningful content
                    lines = content.split('\n')
                    all_text = []
                    all_links = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Skip headers
                        if (line.startswith('Company,') or 
                            line.startswith('Link_Number,') or 
                            line.startswith('Content_Type,') or
                            line in ['EXTRACTED_LINKS', 'EXTRACTED_TEXT_CONTENT']):
                            continue
                        
                        # Extract URLs
                        if 'http' in line:
                            all_links.append(line)
                        
                        # Extract meaningful text (longer than 20 characters)
                        elif len(line) > 20:
                            # Remove CSV formatting
                            clean_line = line.strip('"').strip(',')
                            if clean_line and not clean_line.startswith('Link_') and not clean_line.isdigit():
                                all_text.append(clean_line)
                    
                    st.write(f"Alternative parsing found:")
                    st.write(f"- {len(all_links)} potential links")
                    st.write(f"- {len(all_text)} text segments")
                    
                    if all_text:
                        st.text_area("All extracted text", '\n\n'.join(all_text), height=400)
                    
                    if all_links:
                        st.write("All potential links:")
                        for i, link in enumerate(all_links[:20]):  # Show first 20
                            st.write(f"{i+1}. {link}")
                
                except Exception as e:
                    st.error(f"Alternative parsing failed: {e}")
    
    # Company header
    st.markdown(f"<h1 class='main-header'>{selected_company} - Detailed View</h1>", unsafe_allow_html=True)
    
    # Summary information
    st.markdown("<h3 class='section-header'>Summary Information</h3>", unsafe_allow_html=True)
    
    summary = data.get('summary', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status", str(summary.get('status', 'Unknown')))
    with col2:
        st.metric("Total Links", summary.get('total_links', len(data.get('links', []))))
    with col3:
        st.metric("Text Length", f"{summary.get('text_length', len(str(data.get('text_content', '')))):,}")
    with col4:
        st.metric("Extraction Date", str(summary.get('extraction_date', 'Unknown')))
    
    # Extracted Links Section
    st.markdown("<h3 class='section-header'>Extracted Links</h3>", unsafe_allow_html=True)
    
    links = data.get('links', [])
    if links:
        # Search functionality
        search_term = st.text_input("Search links", placeholder="Enter URL or keyword to search...")
        
        if search_term:
            filtered_links = [link for link in links if search_term.lower() in str(link.get('url', '')).lower()]
        else:
            filtered_links = links
        
        st.write(f"Showing {len(filtered_links)} of {len(links)} links")
        
        # Display links in a table format for better readability
        if filtered_links:
            # Create DataFrame for display
            links_display = []
            for link in filtered_links:
                links_display.append({
                    'Number': link.get('number', 'N/A'),
                    'URL': link.get('url', 'N/A')
                })
            
            links_df = pd.DataFrame(links_display)
            st.dataframe(links_df, use_container_width=True, height=min(400, len(filtered_links) * 35 + 50))
            
            # Show clickable links
            st.subheader("Clickable Links")
            for link in filtered_links[:10]:  # Show first 10 to avoid overwhelming
                link_url = str(link.get('url', 'No URL'))
                link_number = str(link.get('number', 'Unknown'))
                
                if link_url.startswith('http'):
                    st.markdown(f"[{link_number}: {link_url[:100]}...]({link_url})")
                else:
                    st.text(f"{link_number}: {link_url}")
            
            if len(filtered_links) > 10:
                st.info(f"Showing first 10 clickable links. Total: {len(filtered_links)} links")
        
        # Download links as CSV
        if st.button("Download Links as CSV"):
            links_df = pd.DataFrame(links)
            csv_data = links_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{selected_company}_links.csv",
                mime="text/csv"
            )
    else:
        st.info("No links found for this company")
        st.write("Troubleshooting:")
        st.write("- Check the Debug Information section above")
        st.write("- Try the 'Re-parse with Alternative Method' button")
        st.write("- Ensure your CSV file contains an EXTRACTED_LINKS section")
    
    # Extracted Text Content Section
    st.markdown("<h3 class='section-header'>Extracted Text Content</h3>", unsafe_allow_html=True)
    
    text_content = str(data.get('text_content', ''))
    if text_content and text_content.strip() and len(text_content) > 10:
        # Text search
        text_search = st.text_input("Search in text content", placeholder="Enter keyword to search in text...")
        
        display_text = text_content
        if text_search:
            # Highlight search terms
            import re
            pattern = re.compile(re.escape(text_search), re.IGNORECASE)
            display_text = pattern.sub(f"**{text_search}**", text_content)
        
        # Show content in expandable sections for better readability
        text_paragraphs = [p.strip() for p in display_text.split('\n\n') if p.strip()]
        
        # Show first paragraph in main view with reduced height
        if text_paragraphs:
            st.text_area("Content Preview", text_paragraphs[0], height=80)
        
        # Show all content in expandable section with compact display
        with st.expander("View Full Content", expanded=False):
            # Use columns to show content more compactly
            if len(text_paragraphs) > 1:
                # Split into chunks for better display
                chunk_size = 3
                for i in range(0, len(text_paragraphs), chunk_size):
                    chunk = text_paragraphs[i:i+chunk_size]
                    for para in chunk:
                        st.markdown(f"**•** {para}")
                        if para != chunk[-1]:  # Don't add space after last item
                            st.write("")
            else:
                st.markdown(display_text)
        
        # Text statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Characters", len(text_content))
        with col2:
            st.metric("Words", len(text_content.split()))
        with col3:
            st.metric("Lines", len(text_content.split('\n')))
        with col4:
            st.metric("Paragraphs", len([p for p in text_content.split('\n\n') if p.strip()]))
        
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
        st.write("Troubleshooting:")
        st.write("- Check the Debug Information section above")
        st.write("- Try the 'Re-parse with Alternative Method' button") 
        st.write("- Ensure your CSV file contains an EXTRACTED_TEXT_CONTENT section")
        st.write("- Your CSV might have a different format than expected")
    
    # Raw CSV Download
    st.markdown("<h3 class='section-header'>Raw Data</h3>", unsafe_allow_html=True)
    
    if os.path.exists(data['file_path']):
        with open(data['file_path'], 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="Download Complete CSV File",
                data=csv_content,
                file_name=data['filename'],
                mime="text/csv"
            )
        
        with col2:
            st.metric("File Size", f"{len(csv_content):,} characters")

if __name__ == "__main__":
    main()
