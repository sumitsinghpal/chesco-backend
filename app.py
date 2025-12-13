from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)
CORS(app)

def search_google_scholar(query, year_filter='all', limit=10):
    """Search Google Scholar with better scraping"""
    full_query = f"{query} electric motor" if query else "electric motor"
    
    base_url = "https://scholar.google.com/scholar"
    params = {
        'q': full_query,
        'hl': 'en',
        'as_sdt': '0,5'
    }
    
    if year_filter != 'all':
        params['as_ylo'] = year_filter
        params['as_yhi'] = year_filter
    
    # Better headers to avoid blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 429:
            return []  # Rate limited
        
        if response.status_code != 200:
            print(f"Error: Status {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find all search result divs
        search_results = soup.find_all('div', class_='gs_ri')
        print(f"Found {len(search_results)} results in HTML")
        
        for item in search_results[:limit]:
            try:
                # Extract title
                title_elem = item.find('h3', class_='gs_rt')
                if not title_elem:
                    continue
                
                # Remove [PDF] [HTML] tags
                for tag in title_elem.find_all('span', class_='gs_ctg2'):
                    tag.decompose()
                
                title = title_elem.get_text().strip()
                
                # Extract link
                link = title_elem.find('a')
                url = link['href'] if link and 'href' in link.attrs else '#'
                
                # Extract authors and publication info
                authors_elem = item.find('div', class_='gs_a')
                authors_text = authors_elem.get_text() if authors_elem else ''
                
                authors = ''
                year = ''
                journal = ''
                
                if authors_text:
                    parts = authors_text.split(' - ')
                    if len(parts) > 0:
                        authors = parts[0].strip()
                    if len(parts) > 1:
                        year_match = re.search(r'\b(19|20)\d{2}\b', parts[1])
                        if year_match:
                            year = year_match.group()
                        journal = parts[1].strip()
                
                # Extract abstract/snippet
                abstract_elem = item.find('div', class_='gs_rs')
                abstract = abstract_elem.get_text().strip() if abstract_elem else ''
                
                # Extract citation count
                citations = 0
                cite_elem = item.find('div', class_='gs_fl')
                if cite_elem:
                    cite_link = cite_elem.find('a', string=re.compile('Cited by'))
                    if cite_link:
                        cite_match = re.search(r'Cited by (\d+)', cite_link.get_text())
                        if cite_match:
                            citations = int(cite_match.group(1))
                
                # Determine publication type
                pub_type = 'Journal Article'
                if journal and ('conference' in journal.lower() or 'proceedings' in journal.lower()):
                    pub_type = 'Conference Paper'
                
                results.append({
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'journal': journal,
                    'abstract': abstract,
                    'citations': citations,
                    'url': url,
                    'type': pub_type
                })
                
            except Exception as e:
                print(f"Error parsing result: {e}")
                continue
        
        print(f"Returning {len(results)} parsed results")
        return results
        
    except Exception as e:
        print(f"Error fetching from Google Scholar: {e}")
        return []

@app.route('/api/search', methods=['GET'])
def search():
    """API endpoint for searching publications"""
    query = request.args.get('q', '')
    year_filter = request.args.get('year', 'all')
    pub_type = request.args.get('type', 'all')
    
    print(f"Search request - Query: {query}, Year: {year_filter}, Type: {pub_type}")
    
    # Fetch results from Google Scholar
    results = search_google_scholar(query, year_filter)
    
    # Filter by publication type if needed
    if pub_type != 'all':
        results = [r for r in results if r['type'] == pub_type]
    
    return jsonify({
        'success': True,
        'count': len(results),
        'results': results
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'CHESCO Backend is running'})

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'CHESCO Backend API',
        'endpoints': {
            'health': '/api/health',
            'search': '/api/search?q=query&year=2024'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
