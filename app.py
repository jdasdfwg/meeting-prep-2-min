"""
Call-Prep Research Tool for B2B Sales Reps
A lightweight tool to generate company research summaries for sales calls.
"""

import os
import re
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Search categories for comprehensive research
SEARCH_QUERIES = {
    'company_info': '{company} company overview employees industry',
    'funding': '{company} funding round investment series valuation',
    'financials': '{company} revenue market cap financials',
    'priorities': '{company} company priorities strategy 2024 2025 earnings',
    'leadership': '{company} CEO CTO CFO leadership executive hire promotion',
    'news': '{company} company news announcement press release',
    'linkedin': 'site:linkedin.com {company} company',
}


def search_web(query, max_results=5):
    """Perform web search using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except Exception as e:
        print(f"Search error: {e}")
        return []


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


def research_company(company_name):
    """
    Conduct comprehensive research on a company.
    Returns structured data for the call-prep summary.
    """
    research_data = {
        'company_name': company_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'snapshot': {
            'employee_count': None,
            'industry': None,
            'sub_industry': None,
            'description': None,
            'sources': []
        },
        'financials': {
            'funding_rounds': [],
            'market_cap': None,
            'valuation': None,
            'sources': []
        },
        'priorities': {
            'items': [],
            'sources': []
        },
        'leadership': {
            'changes': [],
            'current_leaders': [],
            'sources': []
        },
        'discovery_angles': [],
        'raw_results': {}
    }
    
    # Perform searches for each category
    for category, query_template in SEARCH_QUERIES.items():
        query = query_template.format(company=company_name)
        results = search_web(query, max_results=5)
        research_data['raw_results'][category] = results
        
        # Process results based on category
        for result in results:
            title = result.get('title', '')
            body = result.get('body', '')
            url = result.get('href', '')
            combined_text = f"{title} {body}"
            
            if category == 'company_info':
                # Extract employee count
                if not research_data['snapshot']['employee_count']:
                    emp_count = extract_employee_count(combined_text)
                    if emp_count:
                        research_data['snapshot']['employee_count'] = emp_count
                        research_data['snapshot']['sources'].append({
                            'title': title,
                            'url': url
                        })
                
                # Try to identify industry
                if not research_data['snapshot']['description'] and body:
                    research_data['snapshot']['description'] = body[:300]
                    
            elif category == 'funding':
                amounts, series = extract_funding_info(combined_text)
                if amounts or series:
                    funding_info = {
                        'text': body[:200] if body else title,
                        'url': url,
                        'title': title
                    }
                    research_data['financials']['funding_rounds'].append(funding_info)
                    research_data['financials']['sources'].append({
                        'title': title,
                        'url': url
                    })
                    
            elif category == 'financials':
                market_cap = extract_market_cap(combined_text)
                if market_cap and not research_data['financials']['market_cap']:
                    research_data['financials']['market_cap'] = market_cap
                    research_data['financials']['sources'].append({
                        'title': title,
                        'url': url
                    })
                    
            elif category == 'priorities':
                # Add relevant priority information
                if any(kw in combined_text.lower() for kw in ['priority', 'focus', 'strategy', 'initiative', 'goal', 'plan']):
                    research_data['priorities']['items'].append({
                        'text': body[:250] if body else title,
                        'url': url,
                        'title': title
                    })
                    research_data['priorities']['sources'].append({
                        'title': title,
                        'url': url
                    })
                    
            elif category == 'leadership':
                # Look for leadership changes
                leadership_keywords = ['ceo', 'cto', 'cfo', 'coo', 'vp', 'president', 'chief', 'hire', 'appoint', 'promote', 'join']
                if any(kw in combined_text.lower() for kw in leadership_keywords):
                    research_data['leadership']['changes'].append({
                        'text': body[:200] if body else title,
                        'url': url,
                        'title': title
                    })
                    research_data['leadership']['sources'].append({
                        'title': title,
                        'url': url
                    })
    
    # Generate discovery angles based on research
    research_data['discovery_angles'] = generate_discovery_angles(research_data)
    
    return research_data


def generate_discovery_angles(data):
    """Generate tailored sales discovery angles based on research."""
    angles = []
    
    # Angle based on company size/growth
    emp_count = data['snapshot'].get('employee_count')
    if emp_count:
        emp_num = int(emp_count.replace(',', ''))
        if emp_num < 50:
            angles.append({
                'title': 'Early-Stage Growth Focus',
                'suggestion': 'As a growing team, they likely need scalable solutions. Ask about their infrastructure challenges and what\'s slowing them down as they scale.',
                'hook': '"As you grow from [X] to [2X] employees, what processes are you finding hardest to scale?"'
            })
        elif emp_num < 500:
            angles.append({
                'title': 'Mid-Market Efficiency',
                'suggestion': 'Mid-sized companies often struggle with tool sprawl and process standardization. Explore consolidation opportunities.',
                'hook': '"Many companies at your stage tell us they have 3-4 tools doing the same thing. Is that something you\'re seeing?"'
            })
        else:
            angles.append({
                'title': 'Enterprise Optimization',
                'suggestion': 'Large organizations focus on efficiency gains and cost optimization. Lead with ROI and enterprise-grade capabilities.',
                'hook': '"What would a 10% efficiency improvement in [their key area] mean for your annual targets?"'
            })
    
    # Angle based on funding
    if data['financials']['funding_rounds']:
        angles.append({
            'title': 'Post-Funding Priorities',
            'suggestion': 'Recently funded companies are in growth mode with capital to deploy. Connect your solution to their stated growth objectives.',
            'hook': '"After your recent funding, what\'s the #1 area you\'re investing in to hit your growth targets?"'
        })
    
    # Angle based on leadership changes
    if data['leadership']['changes']:
        angles.append({
            'title': 'New Leadership Agenda',
            'suggestion': 'New executives typically bring fresh initiatives and are open to new vendors. They want quick wins to establish credibility.',
            'hook': '"I noticed [Name] recently joined as [Title]. What priorities has the new leadership been focusing on?"'
        })
    
    # Angle based on stated priorities
    if data['priorities']['items']:
        angles.append({
            'title': 'Aligned with Stated Strategy',
            'suggestion': 'Reference their publicly stated priorities to show you\'ve done your homework and align your pitch accordingly.',
            'hook': '"I read about your focus on [specific initiative]. How is that progressing, and what\'s been the biggest challenge?"'
        })
    
    # Default angle if we don't have enough specific data
    if len(angles) < 3:
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
                'hook': '"When you\'ve brought in new [type of solution] before, what made the difference between success and failure?"'
            }
        ]
        for angle in default_angles:
            if len(angles) < 3:
                angles.append(angle)
    
    return angles[:3]


def format_research_summary(data):
    """Format research data into a clean, skimmable summary."""
    summary = {
        'company_name': data['company_name'],
        'generated_at': data['timestamp'],
        'sections': {}
    }
    
    # Company Snapshot
    snapshot_items = []
    if data['snapshot']['employee_count']:
        snapshot_items.append(f"~{data['snapshot']['employee_count']} employees")
    if data['snapshot']['description']:
        snapshot_items.append(data['snapshot']['description'])
    
    summary['sections']['company_snapshot'] = {
        'title': 'Company Snapshot',
        'items': snapshot_items,
        'sources': data['snapshot']['sources'][:3]
    }
    
    # Financials
    financial_items = []
    if data['financials']['market_cap']:
        financial_items.append(f"Market Cap: {data['financials']['market_cap']}")
    for funding in data['financials']['funding_rounds'][:3]:
        financial_items.append(funding['text'])
    
    summary['sections']['financials'] = {
        'title': 'Financials & Funding',
        'items': financial_items,
        'sources': data['financials']['sources'][:3]
    }
    
    # What They Care About
    priority_items = [p['text'] for p in data['priorities']['items'][:4]]
    summary['sections']['priorities'] = {
        'title': 'What They Care About',
        'items': priority_items,
        'sources': data['priorities']['sources'][:3]
    }
    
    # Leadership Signals
    leadership_items = [l['text'] for l in data['leadership']['changes'][:4]]
    summary['sections']['leadership'] = {
        'title': 'Leadership Signals',
        'items': leadership_items,
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
