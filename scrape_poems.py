import requests
from lxml import html
import json
from typing import Dict, List
import duckdb

def scrape_poem_analysis(url: str) -> Dict:
    """
    Scrape poem analysis page and extract header and blockquote elements.
    For headers: extract poem name and writer name
    For blockquotes: extract only the poem text
    """
    # Send GET request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}
    
    # Parse HTML
    tree = html.fromstring(response.content)
    
    results = {
        "poems": []
    }
    
    # Find all post divs using the pattern from user's XPath
    # The user provided: //*[@id="post-2612935"]/div/header and //*[@id="post-2612935"]/div/blockquote
    # So we need to find all elements with id starting with "post-"
    all_post_ids = tree.xpath('//*[starts-with(@id, "post-")]/@id')
    
    for post_id in all_post_ids:
        # Build XPath for header and blockquote based on the pattern
        header_xpath = f'//*[@id="{post_id}"]/div/header'
        blockquote_xpath = f'//*[@id="{post_id}"]/div/blockquote'
        
        headers = tree.xpath(header_xpath)
        blockquotes = tree.xpath(blockquote_xpath)
        
        # Process each header-blockquote pair
        for header in headers:
            # Extract poem name from h2.entry-title
            poem_name = ""
            poem_title_elem = header.xpath('.//h2[@class="entry-title"]/a')
            if poem_title_elem:
                poem_name = poem_title_elem[0].text_content().strip()
            
            # Extract writer name from h6.poet-name
            writer_name = ""
            poet_name_elem = header.xpath('.//h6[@class="poet-name"]')
            if poet_name_elem:
                full_text = poet_name_elem[0].text_content().strip()
                # Try to extract from link first
                link = poet_name_elem[0].xpath('.//a')
                if link:
                    writer_name = link[0].text_content().strip()
                elif "by " in full_text:
                    writer_name = full_text.split("by ", 1)[1].strip()
                else:
                    writer_name = full_text
            
            # Find corresponding blockquote (should be in same post)
            for blockquote in blockquotes:
                # Extract only the poem text from <p> tags
                poem_lines = []
                p_tags = blockquote.xpath('.//p')
                for p in p_tags:
                    line = p.text_content().strip()
                    if line:
                        poem_lines.append(line)
                
                poem_text = "\n".join(poem_lines)
                
                # Only add if we have all the data
                if poem_name and writer_name and poem_text:
                    results["poems"].append({
                        "poem_name": poem_name,
                        "writer_name": writer_name,
                        "poem_text": poem_text
                    })
                    break  # Found matching blockquote, move to next header
    
    # If no results with exact pattern, try alternative approach
    if not results["poems"]:
        # Try finding all headers and blockquotes separately and match them
        all_headers = tree.xpath('//header[@class="entry-header"]')
        all_blockquotes = tree.xpath('//blockquote[@class="entry-quote"]')
        
        # Match headers with blockquotes (assuming they appear in order)
        for i, header in enumerate(all_headers):
            if i < len(all_blockquotes):
                blockquote = all_blockquotes[i]
                
                # Extract poem name
                poem_name = ""
                poem_title_elem = header.xpath('.//h2[@class="entry-title"]/a')
                if poem_title_elem:
                    poem_name = poem_title_elem[0].text_content().strip()
                
                # Extract writer name
                writer_name = ""
                poet_name_elem = header.xpath('.//h6[@class="poet-name"]')
                if poet_name_elem:
                    full_text = poet_name_elem[0].text_content().strip()
                    link = poet_name_elem[0].xpath('.//a')
                    if link:
                        writer_name = link[0].text_content().strip()
                    elif "by " in full_text:
                        writer_name = full_text.split("by ", 1)[1].strip()
                    else:
                        writer_name = full_text
                
                # Extract poem text
                poem_lines = []
                p_tags = blockquote.xpath('.//p')
                for p in p_tags:
                    line = p.text_content().strip()
                    if line:
                        poem_lines.append(line)
                
                poem_text = "\n".join(poem_lines)
                
                if poem_name and writer_name and poem_text:
                    results["poems"].append({
                        "poem_name": poem_name,
                        "writer_name": writer_name,
                        "poem_text": poem_text
                    })
    
    return results

def init_duckdb(db_path: str = "poems.db") -> duckdb.DuckDBPyConnection:
    """
    Initialize DuckDB database and create poems table if it doesn't exist.
    
    Args:
        db_path: Path to the DuckDB database file
        
    Returns:
        DuckDB connection object
    """
    conn = duckdb.connect(db_path)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS poems (
            id INTEGER PRIMARY KEY,
            poem_name VARCHAR NOT NULL,
            writer_name VARCHAR NOT NULL,
            poem_text TEXT NOT NULL,
            mood_type VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create sequence for auto-incrementing ID if needed
    # DuckDB handles this automatically, but we ensure the table structure is correct
    
    return conn

def insert_poems_to_duckdb(poems: List[Dict], mood_type: str, db_path: str = "poems.db") -> int:
    """
    Insert scraped poems into DuckDB database.
    
    Args:
        poems: List of poem dictionaries with poem_name, writer_name, and poem_text
        mood_type: Mood type to associate with these poems
        db_path: Path to the DuckDB database file
        
    Returns:
        Number of successfully inserted poems
    """
    if not poems:
        print("No poems to insert.")
        return 0
    
    # Initialize database
    conn = init_duckdb(db_path)
    
    inserted_count = 0
    failed_count = 0
    
    try:
        for poem in poems:
            poem_name = poem.get("poem_name", "").strip()
            writer_name = poem.get("writer_name", "").strip()
            poem_text = poem.get("poem_text", "").strip()
            
            if not poem_name or not writer_name or not poem_text:
                print(f"Skipping incomplete poem: {poem_name or 'Unknown'}")
                failed_count += 1
                continue
            
            try:
                # Get next ID
                max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM poems").fetchone()
                next_id = (max_id_result[0] if max_id_result else 0) + 1
                
                # Insert poem into database
                conn.execute("""
                    INSERT INTO poems (id, poem_name, writer_name, poem_text, mood_type)
                    VALUES (?, ?, ?, ?, ?)
                """, [next_id, poem_name, writer_name, poem_text, mood_type])
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting poem '{poem_name}': {str(e)}")
                failed_count += 1
        
        # Commit the transaction
        conn.commit()
        
        print(f"\nInsertion complete:")
        print(f"  Successfully inserted: {inserted_count} poems")
        print(f"  Failed: {failed_count} poems")
        
    except Exception as e:
        print(f"Error during insertion: {str(e)}")
        conn.rollback()
    finally:
        conn.close()
    
    return inserted_count

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape poems from poemanalysis.com and store in DuckDB")
    parser.add_argument("--mood-type", type=str, default="new-life", 
                       help="Mood type to associate with poems (default: new-life)")
    parser.add_argument("--url", type=str, default="https://poemanalysis.com/themes/new-life/",
                       help="URL to scrape poems from")
    parser.add_argument("--db-path", type=str, default="poems.db",
                       help="Path to DuckDB database file (default: poems.db)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode (saves HTML for inspection)")
    parser.add_argument("--no-insert", action="store_true",
                       help="Skip database insertion, only print JSON")
    
    args = parser.parse_args()
    
    url = args.url
    mood_type = args.mood_type
    db_path = args.db_path
    
    if args.debug:
        # Save HTML for inspection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved HTML to debug_page.html for inspection")
        
        # Also print some stats
        tree = html.fromstring(response.content)
        post_ids = tree.xpath('//*[starts-with(@id, "post-")]/@id')
        headers_found = tree.xpath('//header[@class="entry-header"]')
        blockquotes_found = tree.xpath('//blockquote[@class="entry-quote"]')
        print(f"Found {len(post_ids)} post IDs")
        print(f"Found {len(headers_found)} headers")
        print(f"Found {len(blockquotes_found)} blockquotes")
    
    # Scrape poems
    print(f"Scraping poems from: {url}")
    print(f"Mood type: {mood_type}")
    results = scrape_poem_analysis(url)
    
    if "error" in results:
        print(f"Error: {results['error']}")
        sys.exit(1)
    
    # Print JSON format
    print(f"\nScraped {len(results['poems'])} poems:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Insert into DuckDB if not skipped
    if not args.no_insert and results["poems"]:
        print("\n" + "="*50)
        print(f"Inserting poems into DuckDB (mood_type: {mood_type})...")
        print("="*50)
        insert_poems_to_duckdb(results["poems"], mood_type=mood_type, db_path=db_path)
    elif args.no_insert:
        print("\nSkipping database insertion (--no-insert flag set)")
    elif not results["poems"]:
        print("\nNo poems found to insert.")

