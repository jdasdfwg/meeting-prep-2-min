# Call Prep - B2B Sales Research Tool

A lightweight tool that helps B2B sales reps quickly research companies before sales calls. Enter a company name and get a clean, skimmable summary in under 2 minutes.

## Features

- **Company Snapshot**: Employee count, industry, and company description
- **Financials**: Funding rounds, market cap, and valuation data
- **What They Care About**: Recent priorities from earnings calls, blogs, and press
- **Leadership Signals**: C-suite and senior leadership changes (last 12-18 months)
- **Sales Discovery Angles**: 3 tailored conversation starters based on company data

## Quick Start

### 1. Install Dependencies

```bash
cd call-prep-tool
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

### 3. Open in Browser

Navigate to `http://localhost:5000`

## Usage

1. Enter a company name (e.g., "Stripe", "Notion", "Figma")
2. Click "Research Company"
3. Wait 15-30 seconds for results
4. Review the summary before your call

## Output Sections

### Company Snapshot
- Estimated employee count (prioritizes LinkedIn data)
- Industry classification
- Brief company description

### Financials & Funding
- Recent funding rounds with dates, amounts, and lead investors
- Market cap for public companies
- Latest valuation data

### What They Care About
- Recently stated company priorities
- Insights from earnings calls, blogs, and press releases
- LinkedIn posts and executive interviews

### Leadership Signals
- Recent C-suite changes
- New executive hires
- Leadership promotions

### Sales Discovery Angles
Three tailored conversation starters that:
- Reference the company's specific situation
- Provide ready-to-use opening questions
- Are customized to growth stage and recent news

## Tips for Sales Reps

1. **Print/PDF**: Use the "Print / Save PDF" button to save research for offline reference
2. **Source Links**: Click source links for deeper context if needed
3. **Discovery Angles**: The hook questions are designed to be used verbatim
4. **Timing**: Run research 5-10 minutes before your call for fresh data

## Tech Stack

- **Backend**: Python/Flask
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Search**: DuckDuckGo Search API (no API key required)
- **Parsing**: BeautifulSoup4 for web scraping

## Customization

### Adding More Search Categories

Edit the `SEARCH_QUERIES` dictionary in `app.py`:

```python
SEARCH_QUERIES = {
    'company_info': '{company} company overview employees industry',
    'funding': '{company} funding round investment series valuation',
    # Add more categories here
}
```

### Adjusting Discovery Angles

Modify the `generate_discovery_angles()` function in `app.py` to customize the sales angles based on your product/industry.

## Limitations

- Search results depend on publicly available information
- Employee counts are estimates based on web data
- Private company financials may be limited
- Real-time data accuracy depends on source freshness

## License

MIT License - Free to use and modify.
