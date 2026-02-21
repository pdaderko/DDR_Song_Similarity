# Creates a .csv file with a list of songs most similar to corresponding song.
# Uses AudioMuse-AI API to determine music similarity.  Requires .csv file with song library information.
# Tested with Navidrome to serve music to AudioMuse-AI, and for the database to generate the master .csv file.

import csv
import requests
import os
import argparse
import sys

def retrieve_similarity():
    # --- 1. COMMAND LINE ARGUMENT CONFIGURATION ---
    # Use argparse to handle input parameters such as server IP, file paths, and result counts.
    parser = argparse.ArgumentParser(description="Consolidate AudioMuse-AI similarities into a single master CSV.")
    
    # Required: The network address of your AudioMuse-AI server (e.g., localhost:8000)
    parser.add_argument("--server", required=True, help="Server IP and port (e.g., 192.168.1.10:8000)")
    
    # Required: The input CSV file containing your library metadata (must have: id, path, title, artist, album)
    parser.add_argument("--master_csv", required=True, help="Path to the input master CSV")
    
    # Required: The destination path for the single consolidated CSV result
    parser.add_argument("--output", required=True, help="Path for the generated output CSV file")
    
    # Optional: How many similar tracks to retrieve per source song (default is 10)
    parser.add_argument("--count", type=int, default=10, help="Number of similar tracks to retrieve per song")

    args = parser.parse_args()
    
    # Construct the base URL for the AudioMuse-AI API calls
    api_base = f"http://{args.server}/api"

    # Stop the script if the provided input file cannot be found on the system
    if not os.path.exists(args.master_csv):
        print(f"Error: Input CSV '{args.master_csv}' not found.")
        sys.exit(1)

    # --- 2. OUTPUT FILE INITIALIZATION ---
    try:
        # Open the output file immediately for streaming writes to avoid keeping everything in memory
        with open(args.output, mode='w', newline='', encoding='utf-8') as out_file:
            # Column headers: source info (the song being analyzed) and result info (the matches found)
            fieldnames = ['source_title', 'source_artist', 'source_album', 'rank', 'title', 'artist', 'album', 'distance']
            writer = csv.DictWriter(out_file, fieldnames=fieldnames)
            writer.writeheader()

            # --- 3. MASTER CSV PROCESSING ---
            # Open and read the library manifest file row by row
            with open(args.master_csv, mode='r', encoding='utf-8') as master_file:
                reader = csv.DictReader(master_file)
                
                for row in reader:
                    song_id = row['id']
                    # Capture source metadata from the input CSV to repeat on every output row
                    s_title = row['title']
                    s_artist = row['artist']
                    s_album = row['album']

                    print(f"Retrieving similarities for: {s_title}")

                    try:
                        # --- 4. API DATA RETRIEVAL ---
                        
                        # A. Retrieve 'n' similar tracks based on sonic fingerprints
                        sim_resp = requests.get(f"{api_base}/similar_tracks", params={'item_id': song_id, 'n': args.count, 'eliminate_duplicates': 'false', 'radius_similarity': 'false'}, timeout=10)
                        sim_resp.raise_for_status()
                        api_results = sim_resp.json()

                        # B. Retrieve the ID and numerical distance of the "most different" song in the library
                        max_dist_resp = requests.get(f"{api_base}/max_distance", params={'item_id': song_id}, timeout=10)
                        max_dist_resp.raise_for_status()
                        max_data = max_dist_resp.json()
                        
                        # C. Use the ID from step B to fetch human-readable metadata for the farthest song
                        farthest_id = max_data.get('farthest_item_id')
                        farthest_track_resp = requests.get(f"{api_base}/track", params={'item_id': farthest_id}, timeout=10)
                        farthest_track_resp.raise_for_status()
                        farthest_meta = farthest_track_resp.json()

                    except Exception as e:
                        # If the API fails for a song, log the error and move to the next item in the library
                        print(f"  API Error for ID {song_id} ({s_title}): {e}")
                        continue

                    # --- 5. CONSOLIDATED DATA WRITING ---
                    
                    # Write Similar Songs (Rank 1 to 'count')
                    rank_value = 1
                    for item in api_results:
                        writer.writerow({
                            'source_title': s_title,
                            'source_artist': s_artist,
                            'source_album': s_album,
                            'rank': rank_value,
                            'title': item.get('title'),
                            'artist': item.get('author'), # Map API 'author' key to 'artist' column
                            'album': item.get('album'),
                            'distance': item.get('distance')
                        })
                        rank_value += 1

                    # Write the Farthest Song (Rank -1)
                    writer.writerow({
                        'source_title': s_title,
                        'source_artist': s_artist,
                        'source_album': s_album,
                        'rank': -1,
                        'title': farthest_meta.get('title'),
                        'artist': farthest_meta.get('author'), # Map API 'author' key to 'artist' column
                        'album': farthest_meta.get('album'),
                        'distance': max_data.get('max_distance')
                    })
        
        print(f"\nSuccess! All similarities output to: {args.output}")

    except PermissionError:
        # Handle cases where the output file might be locked by another application
        print(f"Error: Could not write to {args.output}. Check file permissions.")

# Entry point for the script execution
if __name__ == "__main__":
    retrieve_similarity()

