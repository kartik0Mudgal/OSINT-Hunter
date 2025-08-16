#!/usr/bin/env python3
"""
OSINT Username Hunter - Flask Backend with Real Verification
Author: Your Name
Description: Backend API for verifying username existence across multiple platforms

Installation:
pip install flask flask-cors requests beautifulsoup4 user-agent

Run:
python osint_backend.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import time
import random
import logging
import os
from flask import Flask, request, jsonify, send_from_directory



# Try to import user-agent, fallback to manual user agents
try:
    from user_agent import generate_user_agent
except ImportError:
    def generate_user_agent():
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        return random.choice(agents)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'Frontend.html')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comprehensive platform database with verification signatures
PLATFORMS = {
    'Social Media': {
        'GitHub': {
            'url': 'https://github.com/{0}',
            'not_found_signatures': ['Not Found', 'Page not found', 'This is not the web page you are looking for'],
            'exists_signatures': ['Profile', 'repositories', 'contributions', 'followers', 'following']
        },
        'Instagram': {
            'url': 'https://www.instagram.com/{0}/',
            'not_found_signatures': ['Page Not Found', 'Sorry, this page isn\'t available', 'The link you followed may be broken'],
            'exists_signatures': ['posts', 'followers', 'following', 'Posts', 'Followers', 'Following']
        },
        'Twitter/X': {
            'url': 'https://twitter.com/{0}',
            'not_found_signatures': ['This account doesn\'t exist', 'Account suspended', 'page doesn\'t exist'],
            'exists_signatures': ['Tweets', 'Following', 'Followers', 'tweets', 'following', 'followers']
        },
        'Facebook': {
            'url': 'https://facebook.com/{0}',
            'not_found_signatures': ['Page Not Found', 'Content Not Found', 'This content isn\'t available'],
            'exists_signatures': ['Posts', 'Photos', 'About', 'posts', 'photos', 'about']
        },
        'LinkedIn': {
            'url': 'https://linkedin.com/in/{0}',
            'not_found_signatures': ['Page not found', 'This profile was not found'],
            'exists_signatures': ['Experience', 'Education', 'connections', 'experience', 'education']
        },
        'TikTok': {
            'url': 'https://tiktok.com/@{0}',
            'not_found_signatures': ['Couldn\'t find this account', 'User not found'],
            'exists_signatures': ['Following', 'Followers', 'Likes', 'following', 'followers', 'likes']
        },
        'Reddit': {
            'url': 'https://reddit.com/user/{0}',
            'not_found_signatures': ['page not found', 'there doesn\'t seem to be anything here', 'Sorry, nobody on Reddit goes by that name'],
            'exists_signatures': ['Post Karma', 'Comment Karma', 'Trophy Case', 'post karma', 'comment karma']
        },
        'Pinterest': {
            'url': 'https://pinterest.com/{0}',
            'not_found_signatures': ['Page not found', 'Sorry, we couldn\'t find that page'],
            'exists_signatures': ['followers', 'following', 'pins', 'Followers', 'Following', 'Pins']
        }
    },
    'Developer Platforms': {
        'GitLab': {
            'url': 'https://gitlab.com/{0}',
            'not_found_signatures': ['404 Not Found', 'Page Not Found', 'The page you\'re looking for could not be found'],
            'exists_signatures': ['Projects', 'Activity', 'Groups', 'projects', 'activity', 'groups']
        },
        'CodePen': {
            'url': 'https://codepen.io/{0}',
            'not_found_signatures': ['Page not found', '404 Not Found'],
            'exists_signatures': ['Pens', 'Posts', 'Collections', 'pens', 'posts', 'collections']
        },
        'Stack Overflow': {
            'url': 'https://stackoverflow.com/users/{0}',
            'not_found_signatures': ['User not found', 'Page Not Found'],
            'exists_signatures': ['reputation', 'answers', 'questions', 'Reputation', 'Answers', 'Questions']
        },
        'Replit': {
            'url': 'https://replit.com/@{0}',
            'not_found_signatures': ['Page not found', 'User not found'],
            'exists_signatures': ['Repls', 'Posts', 'Comments', 'repls', 'posts', 'comments']
        }
    },
    'Gaming': {
        'Steam': {
            'url': 'https://steamcommunity.com/id/{0}',
            'not_found_signatures': ['No profile could be found', 'The specified profile could not be found'],
            'exists_signatures': ['Level', 'Games', 'Screenshots', 'level', 'games', 'screenshots']
        },
        'Twitch': {
            'url': 'https://twitch.tv/{0}',
            'not_found_signatures': ['Sorry. Unless you\'ve got a time machine', 'Page Not Found'],
            'exists_signatures': ['Videos', 'Clips', 'About', 'videos', 'clips', 'about']
        }
    },
    'Professional': {
        'Behance': {
            'url': 'https://behance.net/{0}',
            'not_found_signatures': ['Page not found', '404 - Page not found'],
            'exists_signatures': ['Projects', 'Appreciations', 'Views', 'projects', 'appreciations', 'views']
        },
        'Dribbble': {
            'url': 'https://dribbble.com/{0}',
            'not_found_signatures': ['Page not found', 'Whoops, that page is gone'],
            'exists_signatures': ['Shots', 'Projects', 'Likes', 'shots', 'projects', 'likes']
        },
        'Medium': {
            'url': 'https://medium.com/@{0}',
            'not_found_signatures': ['Page not found', 'User not found'],
            'exists_signatures': ['Stories', 'Following', 'Followers', 'stories', 'following', 'followers']
        }
    },
    'Creative': {
        'YouTube': {
            'url': 'https://youtube.com/@{0}',
            'not_found_signatures': ['This channel doesn\'t exist', 'Page not found'],
            'exists_signatures': ['subscribers', 'videos', 'Home', 'Subscribers', 'Videos']
        },
        'SoundCloud': {
            'url': 'https://soundcloud.com/{0}',
            'not_found_signatures': ['Page not found', 'Sorry! Something went wrong'],
            'exists_signatures': ['followers', 'following', 'tracks', 'Followers', 'Following', 'Tracks']
        },
        'DeviantArt': {
            'url': 'https://{0}.deviantart.com',
            'not_found_signatures': ['Page Not Found', 'The page you were looking for doesn\'t exist'],
            'exists_signatures': ['Deviations', 'Gallery', 'Favourites', 'deviations', 'gallery', 'favourites']
        }
    }
}

def generate_variations(username):
    """Generate common username variations"""
    variations = {username}  # Use set to avoid duplicates
    
    # Basic variations
    variations.add(username.lower())
    variations.add(username.upper())
    variations.add(username.replace('.', ''))
    variations.add(username.replace('_', ''))
    variations.add(username.replace('-', ''))
    variations.add(username.replace(' ', ''))
    
    # Common suffixes
    for suffix in ['1', '123', '2023', '2024']:
        variations.add(username + suffix)
    
    # Common prefixes/suffixes
    variations.add('_' + username)
    variations.add(username + '_')
    
    return list(variations)[:5]  # Limit to prevent excessive requests

def verify_profile(username, platform_name, platform_info, timeout=10):
    """Verify if a profile exists on a platform"""
    url = platform_info['url'].format(username)
    
    result = {
        'platform': platform_name,
        'username': username,
        'url': url,
        'status': 'unknown',
        'response_time': 0,
        'confidence': 0,
        'note': ''
    }
    
    # Rotate user agents to avoid blocking
    headers = {
        'User-Agent': generate_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    start_time = time.time()
    
    try:
        # Add random delay to be respectful to servers
        time.sleep(random.uniform(0.5, 1.5))
        
        logger.info(f"Checking {platform_name} for username: {username}")
        
        response = requests.get(
            url, 
            headers=headers, 
            timeout=timeout, 
            allow_redirects=True,
            verify=True
        )
        
        result['response_time'] = int((time.time() - start_time) * 1000)
        status_code = response.status_code
        
        logger.info(f"{platform_name}/{username}: HTTP {status_code}")
        
        # Handle different status codes
        if status_code == 404:
            result['status'] = 'not_found'
            result['confidence'] = 95
            result['note'] = 'HTTP 404 - Profile does not exist'
            return result
        
        elif status_code == 403:
            result['status'] = 'blocked'
            result['confidence'] = 50
            result['note'] = 'HTTP 403 - Access forbidden (may exist but blocked)'
            return result
        
        elif status_code == 429:
            result['status'] = 'rate_limited'
            result['confidence'] = 0
            result['note'] = 'HTTP 429 - Rate limited, try again later'
            return result
        
        elif status_code >= 500:
            result['status'] = 'error'
            result['confidence'] = 0
            result['note'] = f'HTTP {status_code} - Server error'
            return result
        
        elif status_code != 200:
            result['status'] = 'error'
            result['confidence'] = 0
            result['note'] = f'HTTP {status_code} - Unexpected response'
            return result
        
        # Analyze page content for better accuracy
        try:
            content = response.text.lower()
            
            # Check for "not found" signatures
            not_found_signatures = platform_info.get('not_found_signatures', [])
            for signature in not_found_signatures:
                if signature.lower() in content:
                    result['status'] = 'not_found'
                    result['confidence'] = 90
                    result['note'] = f'Found "not found" signature: {signature}'
                    logger.info(f"{platform_name}/{username}: Not found via signature")
                    return result
            
            # Check for "exists" signatures
            exists_signatures = platform_info.get('exists_signatures', [])
            exists_count = 0
            found_signatures = []
            
            for signature in exists_signatures:
                if signature.lower() in content:
                    exists_count += 1
                    found_signatures.append(signature)
            
            if exists_count > 0:
                result['status'] = 'found'
                result['confidence'] = min(70 + (exists_count * 10), 95)
                result['note'] = f'Found {exists_count} existence indicators: {", ".join(found_signatures[:3])}'
                logger.info(f"{platform_name}/{username}: Found via {exists_count} signatures")
                return result
            
            # If we get here, page loaded but no clear indicators
            result['status'] = 'likely_exists'
            result['confidence'] = 60
            result['note'] = 'Page loaded successfully, likely exists'
            logger.info(f"{platform_name}/{username}: Likely exists (page loaded)")
            
        except Exception as e:
            result['status'] = 'found'  # If we can't parse, assume it exists since we got 200
            result['confidence'] = 70
            result['note'] = f'Page loaded (parsing error: {str(e)[:50]})'
            logger.warning(f"{platform_name}/{username}: Parsing error: {e}")
        
        return result
        
    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['confidence'] = 0
        result['note'] = 'Request timed out'
        result['response_time'] = timeout * 1000
        logger.warning(f"{platform_name}/{username}: Timeout")
        
    except requests.exceptions.ConnectionError:
        result['status'] = 'connection_error'
        result['confidence'] = 0
        result['note'] = 'Connection failed'
        logger.warning(f"{platform_name}/{username}: Connection error")
        
    except requests.exceptions.RequestException as e:
        result['status'] = 'error'
        result['confidence'] = 0
        result['note'] = f'Request error: {str(e)[:50]}'
        logger.warning(f"{platform_name}/{username}: Request error: {e}")
    
    except Exception as e:
        result['status'] = 'error'
        result['confidence'] = 0
        result['note'] = f'Unexpected error: {str(e)[:50]}'
        logger.error(f"{platform_name}/{username}: Unexpected error: {e}")
    
    return result

@app.route('/api/search', methods=['POST'])
def search_username():
    """Main API endpoint for username search"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        include_variations = data.get('includeVariations', False)
        
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        
        logger.info(f"Starting search for username: {username}")
        
        # Generate variations if requested
        usernames_to_check = [username]
        if include_variations:
            usernames_to_check = generate_variations(username)
            logger.info(f"Generated {len(usernames_to_check)} variations")
        
        all_results = []
        
        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_info = {}
            
            # Submit all verification tasks
            for category, platforms in PLATFORMS.items():
                for platform_name, platform_info in platforms.items():
                    for username_variant in usernames_to_check:
                        future = executor.submit(verify_profile, username_variant, platform_name, platform_info)
                        future_to_info[future] = {
                            'category': category,
                            'platform': platform_name,
                            'username': username_variant
                        }
            
            # Collect results as they complete
            for future in as_completed(future_to_info):
                try:
                    result = future.result()
                    result['category'] = future_to_info[future]['category']
                    all_results.append(result)
                except Exception as e:
                    # Handle individual task failures
                    info = future_to_info[future]
                    error_result = {
                        'platform': info['platform'],
                        'category': info['category'],
                        'username': info['username'],
                        'url': '',
                        'status': 'error',
                        'response_time': 0,
                        'confidence': 0,
                        'note': f'Task failed: {str(e)[:50]}'
                    }
                    all_results.append(error_result)
                    logger.error(f"Task failed for {info['platform']}/{info['username']}: {e}")
        
        # Filter and organize results - only show high confidence results
        verified_results = [r for r in all_results if r['status'] in ['found', 'likely_exists'] and r['confidence'] >= 60]
        
        # Calculate statistics
        total_found = len(verified_results)
        platforms_checked = len(set(r['platform'] for r in all_results))
        response_times = [r['response_time'] for r in all_results if r['response_time'] > 0]
        avg_response_time = int(sum(response_times) / max(len(response_times), 1))
        
        logger.info(f"Search complete: {total_found} verified profiles found across {platforms_checked} platforms")
        
        return jsonify({
            'username': username,
            'total_found': total_found,
            'platforms_checked': platforms_checked,
            'avg_response_time': avg_response_time,
            'results': verified_results,
            'debug_info': {
                'total_checks': len(all_results),
                'variations_used': len(usernames_to_check),
                'include_variations': include_variations
            }
        })
    
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'message': 'OSINT Username Hunter API is running',
        'platforms': sum(len(platforms) for platforms in PLATFORMS.values()),
        'version': '1.0.0'
    })

@app.route('/', methods=['GET'])
def home():
    """Basic home endpoint"""
    return jsonify({
        'message': 'OSINT Username Hunter API',
        'version': '1.0.0',
        'endpoints': {
            '/api/health': 'Health check',
            '/api/search': 'POST - Search usernames'
        },
        'platforms_supported': sum(len(platforms) for platforms in PLATFORMS.values())
    })

if __name__ == '__main__':
    import os
    
    # Check if we're running on Render or locally
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('RENDER') is not None
    
    if not is_production:
        # Local development messages
        print("🚀 Starting OSINT Username Hunter Backend...")
        print(f"📊 Platforms configured: {sum(len(platforms) for platforms in PLATFORMS.values())}")
        print("🌐 Server starting on http://localhost:5000")
        print("💡 Frontend should connect automatically")
        print("\n📋 Required packages:")
        print("   pip install flask flask-cors requests beautifulsoup4 user-agent")
        print("\n🔍 Usage:")
        print("   1. Keep this running")
        print("   2. Open index.html in your browser")
        print("   3. Start searching usernames!")
        print("\n" + "="*60)
    else:
        # Production messages
        print("🚀 OSINT Username Hunter Backend starting on Render...")
        print(f"📊 Platforms configured: {sum(len(platforms) for platforms in PLATFORMS.values())}")
    
    try:
        # Use 0.0.0.0 host for production, debug=False for production
        app.run(debug=not is_production, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n👋 OSINT Username Hunter stopped.")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        if not is_production:
            print("Make sure port 5000 is available.")