import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import os

def scrape_nfl_schedule():
    """
    Scrape NFL schedule from operations.nfl.com
    """
    url = "https://operations.nfl.com/gameday/nfl-schedule/2025-nfl-schedule/"
    
    # Headers to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        print("Fetching NFL schedule...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Parse the schedule table
        games = parse_nfl_schedule_table(soup)
        
        if not games:
            # Fallback to text pattern extraction
            print("Table parsing failed, trying alternative methods...")
            games = extract_from_text_patterns(soup)
        
        print(f"Extracted {len(games)} games")
        return games
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the page: {e}")
        return []

def parse_nfl_schedule_table(soup):
    """
    Parse the NFL schedule from the specific table structure
    """
    games = []
    current_week = None
    current_date = None
    
    # Find all table rows
    rows = soup.find_all('tr')
    
    for row in rows:
        row_text = row.get_text(strip=True)
        
        # Check if this row contains week information
        if 'WEEK' in row_text and row_text.startswith('WEEK'):
            current_week = row_text
            continue
        
        # Check if this row contains date information
        if any(month in row_text for month in ['January', 'February', 'March', 'April', 'May', 'June',
                                              'July', 'August', 'September', 'October', 'November', 'December']) or \
           any(day in row_text for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
            current_date = row_text
            continue
        
        # Look for game rows (should have 4 columns)
        cells = row.find_all('td')
        if len(cells) == 4:
            try:
                matchup = cells[0].get_text(strip=True)
                local_time = cells[1].get_text(strip=True)
                et_time = cells[2].get_text(strip=True)
                network = cells[3].get_text(strip=True)
                
                # Skip if this doesn't look like a game
                if not matchup or len(matchup) < 10:
                    continue
                
                # Parse matchup to get teams
                away_team, home_team = parse_matchup(matchup)
                
                if away_team and home_team:
                    game = {
                        'week': current_week,
                        'date': current_date,
                        'matchup': matchup,
                        'away_team': away_team,
                        'home_team': home_team,
                        'local_time': local_time,
                        'et_time': et_time,
                        'network': network,
                        'game_type': 'Regular Season'
                    }
                    games.append(game)
                    
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
    
    return games

def parse_matchup(matchup):
    """
    Parse matchup string to extract away and home teams
    """
    try:
        # Handle different formats: "Team A at Team B", "Team A vs Team B (Location)"
        matchup = matchup.strip()
        
        if ' at ' in matchup:
            parts = matchup.split(' at ')
            away_team = parts[0].strip()
            home_team = parts[1].strip()
        elif ' vs ' in matchup:
            parts = matchup.split(' vs ')
            away_team = parts[0].strip()
            home_team = parts[1].strip()
            # Remove location info in parentheses
            if '(' in home_team:
                home_team = home_team.split('(')[0].strip()
        else:
            return None, None
        
        return away_team, home_team
        
    except Exception as e:
        print(f"Error parsing matchup '{matchup}': {e}")
        return None, None

def extract_from_text_patterns(soup):
    """
    Fallback method to extract games using text patterns
    """
    games = []
    text = soup.get_text()
    
    # Common NFL team abbreviations and names
    teams = [
        'Cardinals', 'Falcons', 'Ravens', 'Bills', 'Panthers', 'Bears', 'Bengals', 'Browns',
        'Cowboys', 'Broncos', 'Lions', 'Packers', 'Texans', 'Colts', 'Jaguars', 'Chiefs',
        'Raiders', 'Chargers', 'Rams', 'Dolphins', 'Vikings', 'Patriots', 'Saints',
        'Giants', 'Jets', 'Eagles', 'Steelers', '49ers', 'Seahawks', 'Buccaneers', 'Titans', 'Commanders'
    ]
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if any(team in line for team in teams) and ('vs' in line or '@' in line or 'at' in line):
            games.append({
                'raw_text': line,
                'parsed': False
            })
    
    return games

def save_schedule_xml(games, filename):
    """
    Save the scraped schedule to XML file
    """
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create root element
    root = ET.Element("nfl_schedule")
    root.set("season", "2025")
    root.set("scraped_date", datetime.now().isoformat())
    
    # Add metadata
    metadata = ET.SubElement(root, "metadata")
    ET.SubElement(metadata, "total_games").text = str(len(games))
    ET.SubElement(metadata, "source").text = "https://operations.nfl.com/gameday/nfl-schedule/2025-nfl-schedule/"
    ET.SubElement(metadata, "scraper_version").text = "2.0"
    
    # Add games container
    games_container = ET.SubElement(root, "games")
    
    for i, game in enumerate(games):
        game_element = ET.SubElement(games_container, "game")
        game_element.set("id", str(i + 1))
        
        # Add game data
        if isinstance(game, dict):
            for key, value in game.items():
                if value is not None:
                    element = ET.SubElement(game_element, key)
                    element.text = str(value)
        else:
            # If game is just a string
            ET.SubElement(game_element, "raw_text").text = str(game)
    
    # Create pretty XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    # Remove empty lines
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
    
    # Save to file
    filepath = f"data/{filename}"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"Schedule saved to {filepath}")
    return filepath

def create_sample_xml():
    """
    Create a sample XML file with expected NFL schedule structure
    """
    # Sample data structure based on the actual NFL schedule format
    sample_games = [
        {
            'week': 'WEEK 1',
            'date': 'Thursday, Sept. 4, 2025',
            'matchup': 'Dallas Cowboys at Philadelphia Eagles',
            'away_team': 'Dallas Cowboys',
            'home_team': 'Philadelphia Eagles',
            'local_time': '8:20p (ET)',
            'et_time': '8:20p',
            'network': 'NBC',
            'game_type': 'Regular Season'
        },
        {
            'week': 'WEEK 1',
            'date': 'Friday, Sept. 5, 2025',
            'matchup': 'Kansas City Chiefs vs Los Angeles Chargers (Sao Paulo)',
            'away_team': 'Kansas City Chiefs',
            'home_team': 'Los Angeles Chargers',
            'local_time': '9:00p (BRT)',
            'et_time': '8:00p',
            'network': 'YouTube',
            'game_type': 'Regular Season'
        },
        {
            'week': 'WEEK 1',
            'date': 'Sunday, Sept. 07, 2025',
            'matchup': 'Tampa Bay Buccaneers at Atlanta Falcons',
            'away_team': 'Tampa Bay Buccaneers',
            'home_team': 'Atlanta Falcons',
            'local_time': '1:00p (ET)',
            'et_time': '1:00p',
            'network': 'FOX',
            'game_type': 'Regular Season'
        },
        {
            'week': 'WEEK 1',
            'date': 'Sunday, Sept. 07, 2025',
            'matchup': 'Baltimore Ravens at Buffalo Bills',
            'away_team': 'Baltimore Ravens',
            'home_team': 'Buffalo Bills',
            'local_time': '8:20p (ET)',
            'et_time': '8:20p',
            'network': 'NBC',
            'game_type': 'Regular Season'
        }
    ]
    
    return sample_games

def print_sample_games(games, limit=10):
    """
    Print a sample of the scraped games
    """
    print(f"\nSample of {min(limit, len(games))} games:")
    print("-" * 50)
    
    for i, game in enumerate(games[:limit]):
        if isinstance(game, dict) and 'away_team' in game:
            print(f"{i+1}. {game['away_team']} at {game['home_team']} - {game.get('et_time', 'TBD')} ({game.get('network', 'TBD')})")
        else:
            print(f"{i+1}. {game.get('raw_text', str(game))}")

def test_with_sample_html():
    """
    Test the parser with sample HTML
    """
    sample_html = '''<tbody>
<tr style="height: 62px;">
<td colspan="4" style="width: 100.035%; height: 62px;">
<p style="text-align: center;"><strong>WEEK 1</strong></p>
</td>
</tr>
<tr style="height: 68px;">
<td colspan="4" width="543" valign="top" style="width: 100.035%; height: 68px;">
<p style="text-align: center;"><strong>Thursday, Sept. 4, 2025</strong></p>
</td>
</tr>
<tr style="height: 88px;">
<td width="307" valign="top" style="width: 54.5274%; height: 88px;">
<p align="left">Dallas Cowboys at Philadelphia Eagles</p>
</td>
<td width="89" valign="top" style="width: 15.9892%; height: 88px;">
<p align="left">8:20p (ET)</p>
</td>
<td width="72" valign="top" style="width: 12.9144%; height: 88px;">
<p>8:20p</p>
</td>
<td width="74" valign="top" style="width: 16.6042%; height: 88px;">
<p>NBC</p>
</td>
</tr>
<tr style="height: 62px;">
<td colspan="4" width="543" valign="top" style="width: 100.035%; height: 62px;">
<p style="text-align: center;"><strong>Friday, Sept. 5, 2025</strong></p>
</td>
</tr>
<tr style="height: 88px;">
<td width="307" valign="top" style="width: 54.5274%; height: 88px;">
<p align="left">Kansas City Chiefs vs Los Angeles Chargers (Sao Paulo)</p>
</td>
<td width="89" valign="top" style="width: 15.9892%; height: 88px;">
<p align="left">9:00p (BRT)</p>
</td>
<td width="72" valign="top" style="width: 12.9144%; height: 88px;">
<p>8:00p</p>
</td>
<td width="74" valign="top" style="width: 16.6042%; height: 88px;">
<p>YouTube</p>
</td>
</tr>
</tbody>'''
    
    soup = BeautifulSoup(sample_html, 'html.parser')
    games = parse_nfl_schedule_table(soup)
    
    print("Test results from sample HTML:")
    print(f"Found {len(games)} games")
    for game in games:
        print(f"  {game['away_team']} at {game['home_team']} - {game['et_time']} ({game['network']})")
    
    return games

if __name__ == "__main__":
    print("NFL Schedule Scraper - XML Only")
    print("=" * 40)
    
    # Test with sample HTML first
    print("Testing parser with sample HTML...")
    test_games = test_with_sample_html()
    
    if test_games:
        print("✅ Parser working correctly!")
        # Save both XML files with test data
        save_schedule_xml(test_games, "schedule_nfl_2025.xml")
        save_schedule_xml(test_games, "bu_schedule_nfl_2025.xml")
    
    print("\n" + "=" * 40)
    
    # Ask user if they want to scrape live data
    response = input("\nDo you want to scrape live data from NFL.com? (y/n): ").lower().strip()
    
    if response == 'y':
        # Scrape the schedule
        schedule = scrape_nfl_schedule()
        
        if schedule:
            print_sample_games(schedule)
            
            # Save both XML files with scraped data
            save_schedule_xml(schedule, "schedule_nfl_2025.xml")
            save_schedule_xml(schedule, "bu_schedule_nfl_2025.xml")
            
            print(f"\nTotal games found: {len(schedule)}")
            print("Both XML files created successfully!")
        else:
            print("No schedule data was extracted. Creating sample XML files...")
            sample_games = create_sample_xml()
            save_schedule_xml(sample_games, "schedule_nfl_2025.xml")
            save_schedule_xml(sample_games, "bu_schedule_nfl_2025.xml")
    else:
        print("Creating sample XML files...")
        sample_games = create_sample_xml()
        save_schedule_xml(sample_games, "schedule_nfl_2025.xml")
        save_schedule_xml(sample_games, "bu_schedule_nfl_2025.xml")
        print("Both XML files created with sample data!")