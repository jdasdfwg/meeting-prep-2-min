"""
Call-Prep Research Tool for B2B Sales Reps
A lightweight tool to generate company research summaries for sales calls.
"""

import os
import re
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Search queries organized by section - multiple variations to ensure results
SEARCH_QUERIES_BY_SECTION = {
    'snapshot': [
        '{company} company about overview',
        '{company} company what do they do business',
        '{company} Wikipedia',
        '{company} company profile description',
        '{company} company history founded',
        '{company} Inc company information',
        '{company} headquarters employees size',
        '{company} company industry sector',
    ],
    'structure': [
        '{company} parent company subsidiary',
        '{company} owned by acquisition',
        '{company} company subsidiaries divisions',
        '{company} acquired by merger',
        '{company} corporate structure ownership',
        '{company} brands portfolio companies',
    ],
    'financials': [
        '{company} funding round investment',
        '{company} revenue financials earnings',
        '{company} market cap stock price',
        '{company} valuation billion million',
        '{company} quarterly results annual report',
        '{company} financial performance 2024',
        '{company} IPO stock ticker',
    ],
    'priorities': [
        '{company} CEO strategy priorities',
        '{company} company goals initiatives 2024 2025',
        '{company} focus areas plans',
        '{company} news announcements recent',
        '{company} company strategy direction',
        '{company} growth plans expansion',
        '{company} company mission vision',
    ],
    'leadership': [
        '{company} CEO CTO CFO executives',
        '{company} leadership team management',
        '{company} executive appointed hired 2024',
        '{company} new CEO leadership changes',
        '{company} board directors officers',
        '{company} founder CEO chief executive',
    ],
}


def search_web(query, max_results=8):
    """Perform web search using DuckDuckGo HTML search (more reliable)."""
    results = []
    
    # Method 1: Try DuckDuckGo HTML search directly
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all result divs
            for result in soup.select('.result')[:max_results]:
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                link_elem = result.select_one('.result__url')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    body = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    href = ''
                    
                    # Get the actual URL
                    a_tag = title_elem.find('a')
                    if a_tag and a_tag.get('href'):
                        href = a_tag.get('href')
                        # DuckDuckGo wraps URLs, extract the actual URL
                        if 'uddg=' in href:
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if 'uddg' in parsed:
                                href = parsed['uddg'][0]
                    
                    results.append({
                        'title': title,
                        'body': body,
                        'href': href
                    })
            
            print(f"HTML search '{query[:40]}...' returned {len(results)} results")
            if results:
                return results
    except Exception as e:
        print(f"HTML search error: {e}")
    
    # Method 2: Fallback to DDGS library
    try:
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=max_results):
            results.append(r)
        print(f"DDGS library search returned {len(results)} results")
        return results
    except Exception as e:
        print(f"DDGS library error: {e}")
    
    return results


def extract_employee_count(text):
    """Extract employee count from text."""
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*(?:\+\s*)?employees',
        r'(\d{1,3}(?:,\d{3})*)\s*(?:\+\s*)?staff',
        r'team\s*(?:of\s*)?(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*people',
        r'workforce\s*(?:of\s*)?(\d{1,3}(?:,\d{3})*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1).replace(',', '')
    return None


def extract_funding_info(text):
    """Extract funding information from text."""
    funding_data = []
    # Pattern for funding amounts
    amount_pattern = r'\$(\d+(?:\.\d+)?)\s*(million|billion|M|B)'
    series_pattern = r'(Series\s*[A-Z]|Seed|Pre-Seed|Bridge)'
    
    amounts = re.findall(amount_pattern, text, re.IGNORECASE)
    series = re.findall(series_pattern, text, re.IGNORECASE)
    
    return amounts, series


def extract_market_cap(text):
    """Extract market cap from text."""
    pattern = r'market\s*cap(?:italization)?\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)\s*(million|billion|trillion|M|B|T)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return f"${match.group(1)} {match.group(2)}"
    return None


def extract_subsidiary_info(text, company_name):
    """Extract subsidiary/parent company information from text."""
    info = {'parent': None, 'subsidiaries': []}
    text_lower = text.lower()
    company_lower = company_name.lower()
    
    # Patterns for parent company
    parent_patterns = [
        rf'{company_lower}\s+(?:is\s+)?(?:a\s+)?subsidiary\s+of\s+([A-Z][A-Za-z\s&]+)',
        rf'{company_lower}\s+(?:is\s+)?owned\s+by\s+([A-Z][A-Za-z\s&]+)',
        rf'{company_lower}\s+(?:is\s+)?(?:a\s+)?(?:division|unit|part)\s+of\s+([A-Z][A-Za-z\s&]+)',
        r'parent\s+company[:\s]+([A-Z][A-Za-z\s&]+)',
        rf'([A-Z][A-Za-z\s&]+)\s+owns?\s+{company_lower}',
        rf'([A-Z][A-Za-z\s&]+)[\'"]?s?\s+subsidiary[,\s]+{company_lower}',
    ]
    
    for pattern in parent_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parent = match.group(1).strip()
            if len(parent) > 2 and len(parent) < 50 and parent.lower() != company_lower:
                info['parent'] = parent
                break
    
    # Patterns for subsidiaries
    subsidiary_patterns = [
        rf'{company_lower}\s+(?:owns?|acquired|bought)\s+([A-Z][A-Za-z\s&,]+)',
        rf'subsidiaries?\s+(?:include|of\s+{company_lower})[:\s]+([A-Za-z\s&,]+)',
        rf'{company_lower}[\'"]?s?\s+(?:subsidiaries?|portfolio|brands?)[:\s]+([A-Za-z\s&,]+)',
    ]
    
    for pattern in subsidiary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            subs = match.group(1).strip()
            # Split by commas and clean up
            for sub in re.split(r'[,;]', subs):
                sub = sub.strip()
                if len(sub) > 2 and len(sub) < 40 and sub.lower() != company_lower:
                    info['subsidiaries'].append(sub)
    
    return info


def check_sections_complete(data, min_items=2):
    """Check if all sections have minimum required items."""
    sections = ['snapshot', 'corporate_structure', 'financials', 'priorities', 'leadership']
    incomplete = []
    for section in sections:
        key = section if section != 'corporate_structure' else 'corporate_structure'
        if len(data[key]['items']) < min_items:
            incomplete.append(section)
    return incomplete


def add_result_to_section(data, section, result):
    """Add a search result to the appropriate section."""
    title = result.get('title', '')
    body = result.get('body', '')
    url = result.get('href', result.get('link', ''))
    
    if not body or len(body.strip()) < 20:
        return False
    
    clean_body = body.strip()
    
    # Check for duplicates
    existing_texts = [item['text'][:100] for item in data[section]['items']]
    if clean_body[:100] in existing_texts:
        return False
    
    # Extract employee count from any result
    if not data.get('employee_count'):
        emp_count = extract_employee_count(f"{title} {body}")
        if emp_count:
            data['employee_count'] = emp_count
    
    data[section]['items'].append({
        'text': clean_body,
        'title': title,
        'url': url
    })
    data[section]['sources'].append({'title': title, 'url': url})
    return True


def research_company(company_name):
    """
    Conduct comprehensive research on a company.
    Keeps searching until ALL sections have data.
    """
    research_data = {
        'company_name': company_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'snapshot': {'items': [], 'sources': []},
        'financials': {'items': [], 'sources': []},
        'priorities': {'items': [], 'sources': []},
        'leadership': {'items': [], 'sources': []},
        'corporate_structure': {'items': [], 'sources': []},
        'discovery_angles': [],
        'employee_count': None
    }
    
    section_key_map = {
        'snapshot': 'snapshot',
        'structure': 'corporate_structure',
        'financials': 'financials',
        'priorities': 'priorities',
        'leadership': 'leadership',
    }
    
    print(f"\n{'='*50}")
    print(f"Researching: {company_name}")
    print(f"{'='*50}")
    
    max_rounds = 3  # Maximum search rounds
    min_items_per_section = 2  # Minimum items needed per section
    
    for round_num in range(max_rounds):
        print(f"\n--- Round {round_num + 1} ---")
        
        # Check which sections need more data
        for section_name, queries in SEARCH_QUERIES_BY_SECTION.items():
            data_key = section_key_map[section_name]
            
            # Skip if section already has enough items
            if len(research_data[data_key]['items']) >= min_items_per_section + round_num:
                continue
            
            # Try queries for this section
            for query_template in queries:
                # Skip if we have enough now
                if len(research_data[data_key]['items']) >= min_items_per_section + round_num:
                    break
                
                query = query_template.format(company=company_name)
                results = search_web(query, max_results=10)
                time.sleep(0.4)  # Rate limiting
                
                # Add results to section
                for result in results:
                    if len(research_data[data_key]['items']) >= 5:
                        break
                    add_result_to_section(research_data, data_key, result)
        
        # Check if all sections are complete
        incomplete = check_sections_complete(research_data, min_items_per_section)
        
        print(f"After round {round_num + 1}:")
        print(f"  Snapshot: {len(research_data['snapshot']['items'])} items")
        print(f"  Structure: {len(research_data['corporate_structure']['items'])} items")
        print(f"  Financials: {len(research_data['financials']['items'])} items")
        print(f"  Priorities: {len(research_data['priorities']['items'])} items")
        print(f"  Leadership: {len(research_data['leadership']['items'])} items")
        
        if not incomplete:
            print(f"\nAll sections complete!")
            break
        else:
            print(f"Incomplete sections: {incomplete}")
    
    # Final pass - use general search if any section still empty
    for section_name, data_key in section_key_map.items():
        if len(research_data[data_key]['items']) == 0:
            print(f"Final attempt for {section_name}...")
            query = f"{company_name} company {section_name} information"
            results = search_web(query, max_results=10)
            for result in results:
                if len(research_data[data_key]['items']) >= 3:
                    break
                add_result_to_section(research_data, data_key, result)
            time.sleep(0.3)
    
    # Generate discovery angles
    research_data['discovery_angles'] = generate_discovery_angles(research_data)
    
    print(f"\n{'='*50}")
    print(f"Research complete for: {company_name}")
    print(f"{'='*50}")
    
    return research_data


def generate_discovery_angles(data):
    """Generate tailored sales discovery angles based on research."""
    angles = []
    
    # Angle based on company size/growth
    emp_count = data.get('employee_count')
    if emp_count:
        try:
            emp_num = int(str(emp_count).replace(',', ''))
            if emp_num < 50:
                angles.append({
                    'title': 'Early-Stage Growth Focus',
                    'suggestion': 'As a growing team, they likely need scalable solutions. Ask about their infrastructure challenges.',
                    'hook': '"As you grow from [X] to [2X] employees, what processes are you finding hardest to scale?"'
                })
            elif emp_num < 500:
                angles.append({
                    'title': 'Mid-Market Efficiency',
                    'suggestion': 'Mid-sized companies often struggle with tool sprawl. Explore consolidation opportunities.',
                    'hook': '"Many companies at your stage tell us they have 3-4 tools doing the same thing. Is that something you\'re seeing?"'
                })
            else:
                angles.append({
                    'title': 'Enterprise Optimization',
                    'suggestion': 'Large organizations focus on efficiency gains and cost optimization. Lead with ROI.',
                    'hook': '"What would a 10% efficiency improvement in [their key area] mean for your annual targets?"'
                })
        except:
            pass
    
    # Angle based on funding/financials
    if data['financials']['items']:
        angles.append({
            'title': 'Financial Health & Investment',
            'suggestion': 'Companies with recent funding or strong financials have capital to deploy. Connect your solution to growth objectives.',
            'hook': '"What\'s the #1 area you\'re investing in to hit your growth targets this year?"'
        })
    
    # Angle based on leadership
    if data['leadership']['items']:
        angles.append({
            'title': 'Leadership Priorities',
            'suggestion': 'Executives set the strategic direction. Reference leadership initiatives to align your pitch.',
            'hook': '"What priorities has leadership been focusing on recently?"'
        })
    
    # Angle based on stated priorities
    if data['priorities']['items']:
        angles.append({
            'title': 'Aligned with Stated Strategy',
            'suggestion': 'Reference their publicly stated priorities to show you\'ve done your homework.',
            'hook': '"I read about your focus on [specific initiative]. How is that progressing?"'
        })
    
    # Default angles to ensure we always have 3
    default_angles = [
        {
            'title': 'Competitive Landscape',
            'suggestion': 'Understand their competitive pressures and how they\'re differentiating.',
            'hook': '"What\'s the one thing your competitors are doing that keeps you up at night?"'
        },
        {
            'title': 'Current Pain Points',
            'suggestion': 'Focus on understanding their day-to-day operational challenges.',
            'hook': '"If you could wave a magic wand and fix one thing about [relevant area], what would it be?"'
        },
        {
            'title': 'Decision-Making Process',
            'suggestion': 'Understand how they evaluate and adopt new solutions.',
            'hook': '"When you\'ve brought in new solutions before, what made the difference between success and failure?"'
        }
    ]
    
    for angle in default_angles:
        if len(angles) < 3:
            angles.append(angle)
    
    return angles[:3]


def format_text(text, max_length=300):
    """Format text to be clean and readable, not cut off mid-word."""
    if not text:
        return ""
    
    # Clean up the text
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    if len(text) <= max_length:
        return text
    
    # Find a good breaking point (end of sentence or word)
    truncated = text[:max_length]
    
    # Try to break at sentence end
    last_period = truncated.rfind('. ')
    if last_period > max_length * 0.6:
        return truncated[:last_period + 1]
    
    # Otherwise break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.7:
        return truncated[:last_space] + "..."
    
    return truncated + "..."


def format_research_summary(data):
    """Format research data into a clean, skimmable summary."""
    summary = {
        'company_name': data['company_name'],
        'generated_at': data['timestamp'],
        'sections': {}
    }
    
    # Company Snapshot - 3-5 concise bullet points
    snapshot_items = []
    
    # Add employee count if found
    if data.get('employee_count'):
        snapshot_items.append(f"Approximately {data['employee_count']} employees")
    
    # Add items from snapshot search
    for item in data['snapshot']['items'][:4]:
        formatted = format_text(item['text'], 280)
        if formatted and formatted not in snapshot_items:
            snapshot_items.append(formatted)
    
    summary['sections']['company_snapshot'] = {
        'title': 'Company Snapshot',
        'items': snapshot_items[:5],
        'sources': data['snapshot']['sources'][:3]
    }
    
    # Corporate Structure
    structure_items = []
    for item in data['corporate_structure']['items'][:4]:
        formatted = format_text(item['text'], 280)
        if formatted:
            structure_items.append(formatted)
    
    summary['sections']['corporate_structure'] = {
        'title': 'Corporate Structure',
        'items': structure_items[:4],
        'sources': data['corporate_structure']['sources'][:3]
    }
    
    # Financials
    financial_items = []
    for item in data['financials']['items'][:4]:
        formatted = format_text(item['text'], 280)
        if formatted:
            financial_items.append(formatted)
    
    summary['sections']['financials'] = {
        'title': 'Financials & Funding',
        'items': financial_items[:4],
        'sources': data['financials']['sources'][:3]
    }
    
    # What They Care About (Priorities)
    priority_items = []
    for item in data['priorities']['items'][:4]:
        formatted = format_text(item['text'], 300)
        if formatted:
            priority_items.append(formatted)
    
    summary['sections']['priorities'] = {
        'title': 'What They Care About',
        'items': priority_items[:4],
        'sources': data['priorities']['sources'][:3]
    }
    
    # Leadership Signals
    leadership_items = []
    for item in data['leadership']['items'][:4]:
        formatted = format_text(item['text'], 280)
        if formatted:
            leadership_items.append(formatted)
    
    summary['sections']['leadership'] = {
        'title': 'Leadership Signals',
        'items': leadership_items[:4],
        'sources': data['leadership']['sources'][:3]
    }
    
    # Discovery Angles
    summary['discovery_angles'] = data['discovery_angles']
    
    return summary


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/research', methods=['POST'])
def research():
    """API endpoint to research a company."""
    data = request.get_json()
    company_name = data.get('company_name', '').strip()
    
    if not company_name:
        return jsonify({'error': 'Company name is required'}), 400
    
    try:
        # Perform research
        research_data = research_company(company_name)
        
        # Format summary
        summary = format_research_summary(research_data)
        
        return jsonify(summary)
    except Exception as e:
        print(f"Research error: {e}")
        return jsonify({'error': f'Research failed: {str(e)}'}), 500


# For Vercel serverless deployment
application = app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
