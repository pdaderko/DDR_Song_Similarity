# Traverses StepMania songs directory and adds/replaces tags for all .ogg and
# .mp3 files corresponding to the associated .sm or .ssc file

import os
import re
import argparse
import glob
import sys
from mutagen.oggvorbis import OggVorbis
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

# FIX: Force the terminal output (stdout) to use UTF-8 encoding.
# This prevents 'charmap' errors on Windows when printing song titles 
# containing Japanese, Cyrillic, or other special characters.
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def get_album_name(file_path):
    """
    Determines the 'Album' name by looking at the folder structure.
    Returns the name of the directory two layers up from the audio file.
    Example: /Songs/Pack_Name/Song_Folder/song.ogg -> returns 'Pack_Name'
    """
    parent_dir = os.path.dirname(file_path)
    grandparent_dir = os.path.dirname(parent_dir)
    return os.path.basename(grandparent_dir)

def parse_metadata_file(file_path):
    """
    Reads a .sm or .ssc file and extracts TITLE, SUBTITLE, and ARTIST using Regex.
    Uses 'errors=ignore' to bypass encoding issues in the source text file.
    The pattern #TAG:([^;]*); captures all text between the colon and the first semicolon.
    """
    tags = {}
    patterns = {
        'title': re.compile(r'#TITLE:([^;]*);', re.IGNORECASE),
        'subtitle': re.compile(r'#SUBTITLE:([^;]*);', re.IGNORECASE),
        'artist': re.compile(r'#ARTIST:([^;]*);', re.IGNORECASE)
    }
    try:
        # StepMania files often have mixed encodings; UTF-8 with ignore is the safest approach.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for key, pattern in patterns.items():
                match = pattern.search(content)
                if match:
                    # .strip() removes accidental leading/trailing whitespace or newlines
                    tags[key] = match.group(1).strip()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return tags

def apply_tags(audio_path, meta_path):
    """
    Wipes all existing metadata and writes new tags from the source simfile.
    Appends SUBTITLE to the TITLE tag if it exists.
    """
    # glob.glob returns a list; we take the first available file found in the folder
    actual_meta_file = meta_path[0] if isinstance(meta_path, list) else meta_path
    new_tags = parse_metadata_file(actual_meta_file)
    album_name = get_album_name(audio_path)
    
    # Combine Title and Subtitle into one string (e.g., "Song Name [Remix]")
    final_title = new_tags.get('title', '')
    subtitle = new_tags.get('subtitle', '')
    if subtitle:
        final_title = f"{final_title} {subtitle}".strip()

    _, ext = os.path.splitext(audio_path)
    ext = ext.lower()

    try:
        if ext == '.ogg':
            # Ogg Vorbis metadata handling
            audio = OggVorbis(audio_path)
            audio.delete()  # Completely strip existing Vorbis comments
            if final_title: audio['title'] = final_title
            if 'artist' in new_tags: audio['artist'] = new_tags['artist']
            audio['album'] = album_name
            audio.save()

        elif ext == '.mp3':
            # MP3 ID3 metadata handling via EasyID3
            audio = MP3(audio_path, ID3=EasyID3)
            
            # Reset tags to avoid the 'ID3 tag already exists' error
            if audio.tags is not None:
                audio.delete()
                audio.tags = None 
            
            # Re-initialize a fresh tag header if it was wiped
            if audio.tags is None:
                audio.add_tags()
            
            if final_title: audio['title'] = final_title
            if 'artist' in new_tags: audio['artist'] = new_tags['artist']
            audio['album'] = album_name
            audio.save()

        # Success message; UTF-8 reconfiguration above ensures this won't crash on special chars
        print(f"Tagged [{ext.upper()}]: {os.path.basename(audio_path)} (Title: {final_title})")
    except Exception as e:
        # Final safety catch for console printing errors
        try:
            print(f"Failed to process {os.path.basename(audio_path)}: {e}")
        except UnicodeEncodeError:
            print(f"Failed to process a file due to unprintable characters in its name or tags.")

def main():
    # Setup CLI: allows running 'python script.py /path/to/folder'
    parser = argparse.ArgumentParser(description="Re-tag OGG/MP3 files using any .sm or .ssc in the folder.")
    parser.add_argument("directory", help="Path to the music root folder")
    args = parser.parse_args()

    # Validate the user-provided directory path
    target_dir = os.path.abspath(args.directory)
    if not os.path.isdir(target_dir):
        print(f"Error: '{args.directory}' is not a valid directory.")
        return

    # os.walk scans the root and all subdirectories recursively
    for root, _, files in os.walk(target_dir):
        # Flags for detecting folders containing both .mp3 and .ogg
        found_ogg = found_mp3 = False
        
        # glob.escape ensures folders with brackets [ ] aren't treated as regex patterns
        # include_hidden=True ensures dot-prefixed simfiles are found
        escaped_root = glob.escape(root)
        ssc_list = glob.glob(os.path.join(escaped_root, "*.ssc"), include_hidden=True)
        sm_list = glob.glob(os.path.join(escaped_root, "*.sm"), include_hidden=True)
        
        # Priority: Use .ssc files first, fall back to .sm, or None if neither exist
        source_meta_list = ssc_list if ssc_list else (sm_list if sm_list else None)

        # First pass: Check for mixed formats in the current directory
        for file in files:
            ext_check = os.path.splitext(file)[1].lower()
            if ext_check == '.ogg': found_ogg = True
            if ext_check == '.mp3': found_mp3 = True
            
            # Second pass logic: Process the audio file if it is OGG or MP3
            if ext_check in ['.ogg', '.mp3']:
                audio_path = os.path.join(root, file)
                
                # Apply tags if a simfile metadata source was found in this folder
                if source_meta_list:
                    apply_tags(audio_path, source_meta_list)
                else:
                    # Log a warning if the audio file has no accompanying stepfile (.ssc/.sm)
                    print(f"WARNING: No tags applied to '{file}'. No .ssc or .sm found in {root}")

        # Alert the user if a folder contains redundant audio formats
        if found_ogg and found_mp3:
            print(f"WARNING: Mixed formats detected in {root} (both .ogg and .mp3 present)")

if __name__ == "__main__":
    main()
