import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os

def check_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)

def render(url:str) -> BeautifulSoup:
    ''' Render the URL using requests and bs4 object'''

    # define the headers user-agent
    headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}

    # make a get request to the URL
    res = requests.get(url,headers=headers)

    # if response status code was good, parse the HTML as bs4 object
    if res.status_code == 200:
        res = BeautifulSoup(res.text,'html.parser')
        return res

def clean_bracket(string:str) -> str:
    ''' Remove brackets'''

    result = re.sub("\((.*?)\)","",string)
    return result.strip()

def sort_event(player: dict) -> dict:
    ''' Sort player event time and event data'''

    # collect numeric value and it's index
    li = []
    for i,et in enumerate(player['Event Time']):
        li.append([et,i])
        
    # sort the li variable
        li.sort()

    # get the index only from li variable
    index = []
    for l in li:
        index.append(l[-1])

    # sort event time and event data based on sorted index
    player['Event Time'] = [player['Event Time'][x] for x in index]
    player['Event'] = [player['Event'][x] for x in index]
    return player

def get_match(url:str, context:dict) -> dict:

    # render the html as bs4 object
    html = render(url)

    # empty variables
    data = {
        "Matchday": context.get("Matchday"),
        "Date": context.get("Date"),
        "Kick off Time": context.get("Kick off Time"),
        "Competition": context.get("Competition"),
        "Season": context.get("Season"),
        "Opposition": context.get("Opponent"),
        "Place": context.get("Place"),
        "Stadium": None,
        "Manager": None,
        "Referee": None,
        "Result": None,
        "For": context.get("For"),
        "Against": context.get("Against"),
        "Attendance": None,
        "Matrix": {"MatrixBlock": []}
    }

    # find tables
    tables = html.find_all('table',class_='standard_tabelle')

    ## get home away position
    clubs = [a.text.strip() for a in tables[0].select("a")]
    clubs = list(filter(lambda x: x != "",clubs))
    for idx,club in enumerate(clubs):
        if data['Opposition'] == club:
            opponent = idx

    # find stadium name, refree name, and number of attendance
    ''' Assume the stadium name, refree name, and number of attendance always represent with image '''

    rows = tables[-1].find_all("tr")
    img_title = [row.find("img").get("title") for row in rows] 
    img_title = list(map(lambda s: s.title(),img_title))
    for key,row in zip(img_title,rows):
        value = row.find_all("td")[-1].text.strip()
        data[key] = clean_bracket(value)
        if key == "Attendance":
            data[key] = data[key].replace(".","")

    # find player tables
    players_table = []
    goals_table = {}
    for table in tables:
        rows = table.select("tr")

        # get goals table
        if len(rows) > 0:
            is_goal_table = rows[0].find("td")
            if is_goal_table and is_goal_table.text == "goals":
                for row in rows:
                    td = row.select("td")
                    if len(td) == 2:
                        player_name = td[-1].find("a").text.strip()
                        event_time = re.search("\d+",td[-1].text).group()
                        if player_name not in goals_table:
                            goals_table.update({player_name: [int(event_time)]})
                        else:
                            goals_table[player_name].append(int(event_time))
        
        # get players table
        players = []
        player_status = "startingXi"
        for row in rows:
            td = row.select("td")
            sub = row.select("td.ueberschrift b")

            # define the subtitution
            if len(sub) > 0:
                player_status = "bench"

            # find players name
            if len(td) == 3:
                player_name = td[1].find('a')
                cards = td[1].find_all("img")
                subbed = td[2].find_all("span")

                if len(subbed) > 1:
                    subbed = re.search("\d+",subbed[-1].text)
                    if subbed:
                        subbed = int(subbed.group())
                else:
                    subbed = None

                if player_name:
                    player_name = player_name.get('title')
                    player = {
                        "Type": "Player",
                        "Status": player_status,
                        "Player": player_name,
                    }

                    # define player card issued
                    if cards:
                        for card in cards:
                            card_title = card.get("title")
                            minute_str = re.search("\d+",card.find_next("span").text)
                            if minute_str:
                                card_minute = int(minute_str.group())
                            else:
                                card_minute = -1
                            
                            if "Event" in player:
                                player['Event Time'].append(card_minute)
                                player['Event'].append(card_title)
                            else:
                                player['Event Time'] = [card_minute]
                                player['Event'] = [card_title]


                    # define player with goal
                    if player_name in goals_table:
                        if "Event" in player:
                            player['Event Time'].extend(goals_table[player_name])
                            for _ in range(len(goals_table[player_name])):
                                player['Event'].append("goal")
                        else:
                            player['Event Time'] = [x for x in goals_table[player_name]]
                            player['Event'] = ["goals" for _ in range(len(goals_table[player_name]))]

                    # define player with subtitution
                    if subbed:
                        if player_status == "startingXi":
                            sub_status = "subbedOff"
                        else:
                            sub_status = "subbedOn"

                        if "Event" in player:
                            player['Event Time'].append(subbed)
                            player['Event'].append(sub_status)
                        else:
                            player['Event Time'] = [subbed]
                            player['Event'] = [sub_status]

                    players.append(player)

        if len(players) > 0:
            players_table.append(players)
            players_table = list(filter(lambda t: len(t) > 0,players_table))

    # find managers
    ''' Assume all the managers name font weight was in bold '''

    rows = tables[-2].select("tr td")
    managers = []
    for i,td in enumerate(rows):
        top = td.get("valign")
        if top:
            manager = td.find("a")
            if manager:
                manager = manager.get("title")
            managers.append(manager)

    for i,player_table in enumerate(players_table):
        if i != opponent:
            for player in player_table:
                if "Event Time" in player and  len(player['Event Time']) > 1:
                    player = sort_event(player)
            data['Matrix']['MatrixBlock'] = player_table
            data['Manager'] = managers[i]

    # define the match result
    home = int(data['For'])
    away = int(data['Against'])
    if home > away:
        match_result = "W"
    elif home < away:
        match_result = "L"
    else:
        match_result = "D"

    data['Result'] = match_result

    return data

if __name__ == "__main__":

    import json

    match_url = "https://www.worldfootball.net/report/premier-league-2019-2020-newcastle-united-tottenham-hotspur/"
    context = {
        'Opponent': 'Newcastle United',
        'For': '1',
        'Against': '3'
    }
    match_data = get_match(match_url,context)

    json.dump(
        match_data,
        open("example-output.json","w",encoding="utf-8"),
        indent=4
    )