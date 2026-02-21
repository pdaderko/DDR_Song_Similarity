# DDR Song Similarity
I've recently gotten back into DDR/StepMania after ~20 years.  Back then, I played a lot of DDR Ultramix on the original XBOX, so I find myself mostly playing those songs, since they're familiar to me.  I have a much larger library now, so I thought it'd be nice to branch out and try some other songs similar to my favorites.

I found [AudioMuse-AI](https://github.com/NeptuneHub/AudioMuse-AI), which will analyze a music library for sonic similarity.  This isn't perfect, since it doesn't tell anything about how similar the step charts are, but it's a good start.

If you just want song suggestions, this repo contains a [.csv file](/suggestions.csv) with pre-computed song similarities for a StepMania library of DDR and ITG songs.

Otherwise, you can use the instructions below to generate one for your own library.  Setting this up isn't too difficult if you're familiar with Linux, networking, etc., though processing your song library can take hours or even days.

## Instructions for using this with your own library

Note: These instructions assume you somewhat know what you're doing.  This walks you through the steps, but it doesn't hold your hand, explain how to use the terminal, etc.

Tested on an Ubuntu 22.04 LTS VM

0. Requirements: Python3, Docker, and SQLite3  
Python3 is needed for the scripts I wrote  
Docker is needed for the Navidrome and AudioMuse-AI containers (Podman should work as well, though I didn't test it, and would require some changes to the below instructions)  
SQLite3 is needed to export Navidrome database fields to a .csv file  
1. **I'd recommend backing up your songs, or working from a separate copy, in case something gets corrupted, etc.**
2. Tag your songs - I found many of the .ogg and .mp3 files in the simfiles aren't properly tagged, or are tagged differently than displayed in StepMania.  The media server (Navidrome) will use the information from the tags, so you want them to match StepMania.  
I created a [Python script](/retag_sm.py) to traverse your music library and re-tag .ogg and .mp3 files from the corresponding .sm or .ssc file (and the Group, .e.g. DDR 1st Mix, is tagged as Album).  
Run: ```python3 retag_sm.py <path to songs directory>```  
Check for warnings/errors.  Particularly, if a directory has both .ogg and .mp3 (in which case you'll have duplicate songs in your music library, which will probably cause duplicate suggestions)  
3. Install the Navidrome media server container  
Follow the instructions here: https://www.navidrome.org/docs/installation/docker/  
I personally used the docker command line tool, instead of docker-compose, though I expect either one works.  
Note that you need to change ```/path/to/music``` to your StepMania songs directory, and ```/path/to/data``` to wherever you'd like Navidrome to store its data.  
AudioMuse-AI should support Jellyfin, Navidrome, Lyrion, and Emby.  I personally tried Jellyfin and had problems getting to to work.  Navidrome immediately worked, and that's what these instruction will assume you're using.  I haven't tried the others.  
5. Set up Navidrome  
Follow the instructions here: https://www.navidrome.org/docs/getting-started/  
Browse to ```http://<your IP address>:4533/``` to make sure your music library looks correct  
6. Once your media server is running, you're ready to get the AudioMuse-AI container  
Follow the instructions here: https://github.com/NeptuneHub/AudioMuse-AI?tab=readme-ov-file#quick-start-deployment  
Note that you're using Navidrome, so edit the .env corresponding to the Navidrome instructions (with your IP address, username, and password), and start the container with: ```docker compose -f deployment/docker-compose-navidrome.yaml up -d```  
7. Once the AudioMuse-AI container is running, start using it by browsing to ```http://<your IP address>:8000```  
You first need to run "Start Analysis".  This will take hours to days, depending on the speed of your PC and number of songs.  
Tip: you can change "Number of Recent Albums" to a small number (e.g. 5) to quickly make sure everything is working before attempting to process your entire library.  
Once that finishes, you need to run "Start Clustering".  This takes a while, but not as long as the initial analysis.  
When that's complete, go to the "Playlist from Similar Song" page from the menu on the left.  
Begin typing an artist or title and make sure it auto-completes.  Select a song and click "Find Similar Tracks".  If this shows a list of similar songs, then everything should be working correctly.  

**You can stop here and use the AudioMuse-AI web interface directly if you're happy with the functionality**  
**Otherwise, continue below to create a suggestions .csv file for your entire library**

7. Export your Navidrome library to a .csv file, which will be needed for batch processing  
cd to the Navidrome data directory that you specified earlier and run: ```sqlite3 -header -csv navidrome.db "SELECT id, path, title, artist, album FROM media_file;" > library.csv```  
8. To batch process your library, I created a [Python script](/similar_csv.py) to use AudioMuse-AI's API.  Run (using your IP address and the correct path to the library.csv file that you exported): ```python3 similar_csv.py --server <your IP address>:8000 --master_csv library.csv --output suggestions.csv --count 30```  
Of course you can change the output file and the number of suggestions to your liking.  This is fairly quick, depending on the size of your library.  
9. Once your .csv file is generated, you can open it in LibreOffice, Excel, etc.  
Use the AutoFilter on the first row, then filter as desired (e.g. by song/artist/album)  
Note that the rank for each song is shown from 1 to \<count\>, plus a final one with a rank of -1, which is the most different song.

![example](/butterfly.png)

The Python scripts were created with the help of Google Gemini - it writes Python better and faster than I do. ;-)
