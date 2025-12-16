from flask import Flask, request, jsonify
from flask_cors import CORS
from serpapi import GoogleSearch
import requests
import xmltodict
import feedparser
import os
import time
import re

app = Flask(__name__)
CORS(app)

# API Keys
SERPAPI_KEY = os.environ.get('SERPAPI_KEY', 'e5a02319422293028e05ee9f5a634d9d2c83e5b104feb0a5de3619e863a1e783')
SEMANTIC_SCHOLAR_KEY = os.environ.get('SEMANTIC_SCHOLAR_KEY', 'BOWwvouuaF8LHnmtbWvVL1g7onkJ2Bn4deKTwvdd')

# ============================================
# SEMANTIC SCHOLAR (FREE - 10,000/month)
# ============================================
def search_semantic_scholar(query, year_filter='all', limit=5):
    """Search Semantic Scholar API"""
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': f"{query} electric motor",
            'limit': limit,
            'fields': 'title,authors,year,abstract,citationCount,url,venue,publicationTypes'
        }
        
        if year_filter != 'all':
            params['year'] = f"{year_filter}-{year_filter}"
        
        headers = {}
        if SEMANTIC_SCHOLAR_KEY:
            headers['x-api-key'] = SEMANTIC_SCHOLAR_KEY
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        parsed_results = []
        
        for paper in data.get('data', []):
            # Safely get abstract (handle None)
            abstract = paper.get('abstract')
            if abstract is None:
                abstract = 'No abstract available'
            
            # Safely get authors
            authors_list = paper.get('authors', [])
            if authors_list:
                authors = ', '.join([a.get('name', '') for a in authors_list if a.get('name')])
            else:
                authors = 'Unknown'
            
            # Safely get publication types
            pub_types = paper.get('publicationTypes', [])
            if pub_types and 'Conference' in pub_types:
                pub_type = 'Conference Paper'
            else:
                pub_type = 'Journal Article'
            
            parsed_results.append({
                'title': paper.get('title', 'Untitled'),
                'authors': authors,
                'year': str(paper.get('year', '')),
                'journal': paper.get('venue', ''),
                'abstract': abstract,
                'citations': paper.get('citationCount', 0),
                'url': paper.get('url', '#'),
                'source': 'Semantic Scholar',
                'type': pub_type
            })
        
        return parsed_results
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []

# ============================================
# arXiv (FREE - UNLIMITED)
# ============================================
def search_arxiv(query, year_filter='all', limit=5):
    """Search arXiv API"""
    try:
        base_url = "http://export.arxiv.org/api/query"
        search_query = f"all:{query} AND all:electric AND all:motor"
        
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': limit,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = xmltodict.parse(response.content)
        entries = data.get('feed', {}).get('entry', [])
        
        if not isinstance(entries, list):
            entries = [entries] if entries else []
        
        parsed_results = []
        for entry in entries:
            published = entry.get('published', '')
            year = published[:4] if published else ''
            
            if year_filter != 'all' and year != year_filter:
                continue
            
            authors_data = entry.get('author', [])
            if not isinstance(authors_data, list):
                authors_data = [authors_data]
            authors = ', '.join([a.get('name', '') for a in authors_data])
            
            parsed_results.append({
                'title': entry.get('title', '').replace('\n', ' ').strip(),
                'authors': authors,
                'year': year,
                'journal': f"arXiv:{entry.get('id', '').split('/')[-1]}",
                'abstract': entry.get('summary', '').replace('\n', ' ').strip(),
                'citations': 0,
                'url': entry.get('id', '#'),
                'source': 'arXiv',
                'type': 'Preprint'
            })
        
        return parsed_results
    except Exception as e:
        print(f"arXiv error: {e}")
        return []

# ============================================
# CORE (FREE - 1,000/day)
# ============================================
def search_core(query, year_filter='all', limit=5):
    """Search CORE API"""
    try:
        url = "https://api.core.ac.uk/v3/search/works"
        params = {
            'q': f"{query} electric motor",
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        parsed_results = []
        
        for item in data.get('results', []):
            year = str(item.get('yearPublished', ''))
            
            if year_filter != 'all' and year != year_filter:
                continue
            
            authors = ', '.join([a.get('name', '') for a in item.get('authors', [])])
            
            parsed_results.append({
                'title': item.get('title', ''),
                'authors': authors,
                'year': year,
                'journal': item.get('publisher', ''),
                'abstract': (item.get('abstract') or 'No abstract available')[:500],
                'citations': item.get('citationCount', 0),
                'url': item.get('downloadUrl') or item.get('sourceFulltextUrls', ['#'])[0],
                'source': 'CORE',
                'type': 'Open Access'
            })
        
        return parsed_results
    except Exception as e:
        print(f"CORE error: {e}")
        return []

# ============================================
# CROSSREF (FREE - UNLIMITED)
# ============================================
def search_crossref(query, year_filter='all', limit=5):
    """Search CrossRef API"""
    try:
        url = "https://api.crossref.org/works"
        params = {
            'query': f"{query} electric motor",
            'rows': limit,
            'sort': 'relevance'
        }
        
        if year_filter != 'all':
            params['filter'] = f"from-pub-date:{year_filter},until-pub-date:{year_filter}"
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        parsed_results = []
        
        for item in data.get('message', {}).get('items', []):
            authors_data = item.get('author', [])
            authors = ', '.join([f"{a.get('given', '')} {a.get('family', '')}" for a in authors_data[:3]])
            
            pub_date = item.get('published', {}).get('date-parts', [[]])[0]
            year = str(pub_date[0]) if pub_date else ''
            
            abstract = item.get('abstract')
            if not abstract:
                abstract = 'No abstract available'
            
            parsed_results.append({
                'title': item.get('title', [''])[0],
                'authors': authors,
                'year': year,
                'journal': item.get('container-title', [''])[0],
                'abstract': (abstract[:500] if abstract else 'No abstract available'),
                'citations': item.get('is-referenced-by-count', 0),
                'url': item.get('URL', '#'),
                'source': 'CrossRef',
                'type': item.get('type', 'journal-article').replace('-', ' ').title()
            })
        
        return parsed_results
    except Exception as e:
        print(f"CrossRef error: {e}")
        return []

# ============================================
# GOOGLE SCHOLAR via SerpAPI (Backup Only)
# ============================================
def search_google_scholar(query, year_filter='all', limit=5):
    """Search Google Scholar - USE SPARINGLY"""
    try:
        params = {
            "engine": "google_scholar",
            "q": f"{query} electric motor",
            "api_key": SERPAPI_KEY,
            "num": limit
        }
        
        if year_filter != 'all':
            params['as_ylo'] = year_filter
            params['as_yhi'] = year_filter
        
        search = GoogleSearch(params)
        results_data = search.get_dict()
        
        if 'error' in results_data:
            return []
        
        parsed_results = []
        for item in results_data.get('organic_results', []):
            pub_info = item.get('publication_info', {})
            parsed_results.append({
                'title': item.get('title', ''),
                'authors': ', '.join([a.get('name', '') for a in pub_info.get('authors', [])]),
                'year': pub_info.get('summary', '').split(',')[-1].strip()[:4] if pub_info.get('summary') else '',
                'journal': pub_info.get('summary', ''),
                'abstract': item.get('snippet', ''),
                'citations': item.get('inline_links', {}).get('cited_by', {}).get('total', 0),
                'url': item.get('link', '#'),
                'source': 'Google Scholar',
                'type': 'Journal Article'
            })
        return parsed_results
    except Exception as e:
        print(f"Google Scholar error: {e}")
        return []

# ============================================
# COMBINED SEARCH - FREE FIRST!
# ============================================
def search_all_sources(query, year_filter='all'):
    """Search FREE sources first, SerpAPI as backup"""
    all_results = []
    
    print(f"Searching FREE sources for: {query}")
    
    # FREE sources (80% of the work)
    all_results.extend(search_semantic_scholar(query, year_filter, limit=3))
    time.sleep(0.3)
    
    all_results.extend(search_arxiv(query, year_filter, limit=3))
    time.sleep(0.3)
    
    all_results.extend(search_core(query, year_filter, limit=3))
    time.sleep(0.3)
    
    all_results.extend(search_crossref(query, year_filter, limit=3))
    time.sleep(0.3)
    
    # Only use SerpAPI if we have less than 5 results
    if len(all_results) < 5 and SERPAPI_KEY:
        print("Adding Google Scholar (SerpAPI)...")
        all_results.extend(search_google_scholar(query, year_filter, limit=5))
    
    # Remove duplicates
    unique_results = []
    seen_titles = set()
    
    for result in all_results:
        title_lower = result['title'].lower()[:50]
        if title_lower not in seen_titles and result['title']:
            seen_titles.add(title_lower)
            unique_results.append(result)
    
    unique_results.sort(key=lambda x: x.get('citations', 0), reverse=True)
    
    return unique_results

# ============================================
# NEWS - Simplified (No feedparser needed)
# ============================================
@app.route('/api/news', methods=['GET'])
def news():
    """Get latest electric motor news - Static fallback"""
    
    # Static news that always works
    news_items = [
        {
            'title': 'Electric Vehicle Market Continues Strong Growth',
            'url': 'https://www.reuters.com/business/autos-transportation/electric-vehicles/',
            'source': 'Reuters',
            'published': '2024-12-17'
        },
        {
            'title': 'New Advances in Electric Motor Efficiency',
            'url': 'https://spectrum.ieee.org/electric-motors',
            'source': 'IEEE Spectrum',
            'published': '2024-12-16'
        },
        {
            'title': 'Hybrid Electric Systems for Commercial Vehicles',
            'url': 'https://www.autoweek.com/news/green-cars/',
            'source': 'Autoweek',
            'published': '2024-12-15'
        },
        {
            'title': 'Battery Technology Improvements Drive EV Adoption',
            'url': 'https://www.technologyreview.com/topic/battery-technology/',
            'source': 'MIT Technology Review',
            'published': '2024-12-14'
        },
        {
            'title': 'Electric Motor Research at Leading Universities',
            'url': 'https://news.mit.edu/topic/electric-vehicles',
            'source': 'MIT News',
            'published': '2024-12-13'
        }
    ]
    
    return jsonify({
        'success': True,
        'count': len(news_items),
        'news': news_items
    })
# ============================================
# API ENDPOINTS
# ============================================
@app.route('/api/search', methods=['GET'])
def search():
    """Main search endpoint"""
    query = request.args.get('q', '')
    year_filter = request.args.get('year', 'all')
    
    if not query:
        return jsonify({'success': True, 'count': 0, 'results': []})
    
    print(f"Search request: {query}, Year: {year_filter}")
    
    results = search_all_sources(query, year_filter)
    
    return jsonify({
        'success': True,
        'count': len(results),
        'results': results
    })

@app.route('/api/sources', methods=['GET'])
def list_sources():
    """List available sources"""
    return jsonify({
        'available_sources': [
            {'id': 'semantic_scholar', 'name': 'Semantic Scholar', 'status': 'active', 'cost': 'FREE'},
            {'id': 'arxiv', 'name': 'arXiv', 'status': 'active', 'cost': 'FREE'},
            {'id': 'core', 'name': 'CORE', 'status': 'active', 'cost': 'FREE'},
            {'id': 'crossref', 'name': 'CrossRef', 'status': 'active', 'cost': 'FREE'},
            {'id': 'google_scholar', 'name': 'Google Scholar', 'status': 'backup', 'cost': 'Limited (100/month)'}
        ]
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'message': 'CHESCO Multi-Source Backend',
        'free_sources': ['Semantic Scholar', 'arXiv', 'CORE', 'CrossRef'],
        'serpapi_status': 'configured' if SERPAPI_KEY else 'not configured'
    })

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'CHESCO Backend API - Multi-Source Research Search',
        'version': '2.0',
        'sources': {
            'free': ['Semantic Scholar (10,000/month)', 'arXiv (unlimited)', 'CORE (1,000/day)', 'CrossRef (unlimited)'],
            'backup': ['Google Scholar via SerpAPI (100/month)']
        },
        'endpoints': {
            'health': '/api/health',
            'search': '/api/search?q=motor&year=2024',
            'news': '/api/news',
            'sources': '/api/sources'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


