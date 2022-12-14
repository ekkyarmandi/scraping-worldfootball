### import necessary libraries
from func import render, get_match, check_folder
from urllib.parse import urlparse
import json
import time
import sys, traceback
import re
import os

# define the target url
url = "https://www.worldfootball.net/teams/tottenham-hotspur/1992/3/"

# get the URL reference
ref = "https://" + urlparse(url).netloc

# render the URL
html = render(url)

# find the table and collect the match data
table = html.find("table",class_="standard_tabelle")
rows = table.select("tr")
data = []
get_season = True
for row in rows:
    match_url = ""
    tds = row.select("td")
    if len(tds) == 1:
        season_league = tds[0].find("a").get("title")
        season = re.search("\d+\/\d+|\d+",season_league)
        if season:
            season = season.group()
            league = season_league.replace(season,"").strip()
            if get_season:
                get_season = False
                filename_season = season
                if "/" in filename_season:
                    a,b = filename_season.split("/")
                    filename_season = f"{a}-{b[2:]}"

            # convert season year from XXXX/XXXX into XXXX/XX
            ''' Assume the year format is XXXX/XXXX '''
            if "/" in season:
                a,b = season.split("/")
                season = f"{a}/{b[2:]}"

    elif len(tds) > 1:
        try:
            results = tds[6].find("a")

            opponent = tds[5].find("a").text.strip()
            match_url = results.get("href")
            if ref not in match_url:
                match_url = ref + match_url

            for_against = re.search("\d+:\d+",results.text).group().split(":")
            matchday = tds[0].find("a").text.strip()
            if matchday == "Round":
                matchday = "1"
            context = {
                'Matchday': matchday,
                'Date': tds[1].find("a").text.strip(),
                'Kick off Time': tds[2].text.strip(),
                'Place': tds[3].text.strip(),
                'Opponent': opponent,
                "Competition": league,
                "Season": season,
                "For": for_against[0],
                "Against": for_against[1],
            }
            
            print(match_url)
            if match_url:
                match_data = get_match(match_url,context)
                data.append(match_data)
                # time.sleep(1)

        except Exception as E:
            # _, _, tb = sys.exc_info()
            # traceback.print_tb(tb)
            print({
                "url": match_url,
                "opponent": opponent,
                "error": E,
            })

# dump the data as JSON file
root = "output"
check_folder(root)
filename = os.path.join(root,filename_season+".json")
json.dump(
    data,
    open(filename,"w",encoding="utf-8"),
    indent=4
)