from flask import Flask, request, jsonify
from flask_cors import CORS
from serpapi import GoogleSearch
import requests
import xmltodict
import os
import time

app = Flask(__name__)
CORS(app)

# API Keys
SERPAPI_KEY = os.environ.get('SERPAPI_KEY', 'e5a02319422293028e05ee9f5a634d9d2c83e5b104feb0a5de3619e863a1e783')
SEMANTIC_SCHOLAR_KEY = os.environ.get('SEMANTIC_SCHOLAR_KEY', '')  # Optional, increases rate limit

# ============================================
# GOOGLE SCHOLAR via SerpAPI
# ============================================
def search_google_scholar(query, year_filter='all', limit=5):
    """Search Google Scholar using SerpAPI"""
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
# SEMANTIC SCHOLAR
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
            authors = ', '.join([a.get('name', '') for a in paper.get('authors', [])])
            parsed_results.append({
                'title': paper.get('title', ''),
                'authors': authors,
                'year': str(paper.get('year', '')),
                'journal': paper.get('venue', ''),
                'abstract': paper.get('abstract', 'No abstract available'),
                'citations': paper.get('citationCount', 0),
                'url': paper.get('url', '#'),
                'source': 'Semantic Scholar',
                'type': 'Conference Paper' if 'Conference' in paper.get('publicationTypes', []) else 'Journal Article'
            })
        
        return parsed_results
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []

# ============================================
# arXiv
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
            entries = [entries]
        
        parsed_results = []
        for entry in entries:
            # Extract year from published date
            published = entry.get('published', '')
            year = published[:4] if published else ''
            
            # Filter by year if specified
            if year_filter != 'all' and year != year_filter:
                continue
            
            # Extract authors
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
                'citations': 0,  # arXiv doesn't provide citation counts
                'url': entry.get('id', '#'),
                'source': 'arXiv',
                'type': 'Preprint'
            })
        
        return parsed_results
    except Exception as e:
        print(f"arXiv error: {e}")
        return []

# ============================================
# CORE
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
            
            # Filter by year if specified
            if year_filter != 'all' and year != year_filter:
                continue
            
            authors = ', '.join([a.get('name', '') for a in item.get('authors', [])])
            
            parsed_results.append({
                'title': item.get('title', ''),
                'authors': authors,
                'year': year,
                'journal': item.get('publisher', ''),
                'abstract': item.get('abstract', 'No abstract available')[:500],
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
# CROSSREF
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
            # Extract authors
            authors_data = item.get('author', [])
            authors = ', '.join([f"{a.get('given', '')} {a.get('family', '')}" for a in authors_data[:3]])
            
            # Extract year
            pub_date = item.get('published', {}).get('date-parts', [[]])[0]
            year = str(pub_date[0]) if pub_date else ''
            
            # Get abstract (if available)
            abstract = item.get('abstract', 'No abstract available')
            
            parsed_results.append({
                'title': item.get('title', [''])[0],
                'authors': authors,
                'year': year,
                'journal': item.get('container-title', [''])[0],
                'abstract': abstract[:500] if abstract else 'No abstract available',
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
# COMBINED SEARCH
# ============================================
def search_all_sources(query, year_filter='all', sources='all'):
    """Search multiple sources and combine results"""
    all_results = []
    
    source_list = sources.split(',') if sources != 'all' else ['google_scholar', 'semantic_scholar', 'arxiv', 'core', 'crossref']
    
    if 'google_scholar' in source_list and SERPAPI_KEY != 'YOUR_SERPAPI_KEY_HERE':
        print("Searching Google Scholar...")
        all_results.extend(search_google_scholar(query, year_filter))
        time.sleep(0.5)
    
    if 'semantic_scholar' in source_list:
        print("Searching Semantic Scholar...")
        all_results.extend(search_semantic_scholar(query, year_filter))
        time.sleep(0.5)
    
    if 'arxiv' in source_list:
        print("Searching arXiv...")
        all_results.extend(search_arxiv(query, year_filter))
        time.sleep(0.5)
    
    if 'core' in source_list:
        print("Searching CORE...")
        all_results.extend(search_core(query, year_filter))
        time.sleep(0.5)
    
    if 'crossref' in source_list:
        print("Searching CrossRef...")
        all_results.extend(search_crossref(query, year_filter))
    
    # Remove duplicates based on title similarity
    unique_results = []
    seen_titles = set()
    
    for result in all_results:
        title_lower = result['title'].lower()[:50]  # First 50 chars for comparison
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_results.append(result)
    
    # Sort by citations (descending)
    unique_results.sort(key=lambda x: x.get('citations', 0), reverse=True)
    
    return unique_results

# ============================================
# API ENDPOINTS
# ============================================
@app.route('/api/search', methods=['GET'])
def search():
    """Main search endpoint"""
    query = request.args.get('q', '')
    year_filter = request.args.get('year', 'all')
    sources = request.args.get('sources', 'all')  # Can specify: google_scholar,arxiv,semantic_scholar
    
    if not query:
        return jsonify({
            'success': True,
            'count': 0,
            'results': [],
            'sources_used': []
        })
    
    print(f"Search: {query}, Year: {year_filter}, Sources: {sources}")
    
    results = search_all_sources(query, year_filter, sources)
    
    # Get unique sources used
    sources_used = list(set([r['source'] for r in results]))
    
    return jsonify({
        'success': True,
        'count': len(results),
        'results': results,
        'sources_used': sources_used
    })

@app.route('/api/sources', methods=['GET'])
def list_sources():
    """List available sources"""
    return jsonify({
        'available_sources': [
            {'id': 'google_scholar', 'name': 'Google Scholar', 'status': 'active' if SERPAPI_KEY != 'YOUR_SERPAPI_KEY_HERE' else 'inactive'},
            {'id': 'semantic_scholar', 'name': 'Semantic Scholar', 'status': 'active'},
            {'id': 'arxiv', 'name': 'arXiv', 'status': 'active'},
            {'id': 'core', 'name': 'CORE', 'status': 'active'},
            {'id': 'crossref', 'name': 'CrossRef', 'status': 'active'}
        ]
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'message': 'CHESCO Multi-Source Backend',
        'serpapi': 'configured' if SERPAPI_KEY != 'YOUR_SERPAPI_KEY_HERE' else 'not configured'
    })

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'CHESCO Backend API - Multi-Source Research Search',
        'sources': ['Google Scholar', 'Semantic Scholar', 'arXiv', 'CORE', 'CrossRef'],
        'endpoints': {
            'health': '/api/health',
            'search': '/api/search?q=motor&year=2024&sources=all',
            'sources': '/api/sources'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
