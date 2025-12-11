from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app)

def search_google_scholar(query, year_filter='all', limit=10):
    full_query = f"{query} electric motor" if query else "electric motor"
    
    base_url = "https://scholar.google.com/scholar"
    params = {'q': full_query, 'hl': 'en'}
    
    if year_filter != 'all':
        params['as_ylo'] = year_filter
        params['as_yhi'] = year_filter
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for item in soup.select('.gs_ri')[:limit]:
            try:
                title_elem = item.select_one('.gs_rt')
                if not title_elem:
                    continue
                    
                title = re.sub(r'\[.*?\]', '', title_elem.get_text()).strip()
                link_elem = title_elem.select_one('a')
                url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else '#'
                
                authors_elem = item.select_one('.gs_a')
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
                
                abstract_elem = item.select_one('.gs_rs')
                abstract = abstract_elem.get_text() if abstract_elem else ''
                
                citations = 0
                cite_elem = item.select_one('.gs_fl a')
                if cite_elem:
                    cite_match = re.search(r'Cited by (\d+)', cite_elem.get_text())
                    if cite_match:
                        citations = int(cite_match.group(1))
                
                results.append({
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'journal': journal,
                    'abstract': abstract,
                    'citations': citations,
                    'url': url,
                    'type': 'Journal Article'
                })
            except:
                continue
        
        return results
    except:
        return []

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    year_filter = request.args.get('year', 'all')
    pub_type = request.args.get('type', 'all')
    
    results = search_google_scholar(query, year_filter)
    
    if pub_type != 'all':
        results = [r for r in results if r['type'] == pub_type]
    
    return jsonify({
        'success': True,
        'count': len(results),
        'results': results
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### **File 2: `requirements.txt`** (Save as .txt file)
```
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
beautifulsoup4==4.12.2
