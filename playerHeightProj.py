import json
from bs4 import BeautifulSoup
import sqlite3
import time
import http.client
import matplotlib.pyplot as plt
import unittest

api_key = "9ue32uspqx8cdhzd2a379c49"

# ------------------------------------------------------------------------------
def getTeamIDs(api_key, cacheDict, fileName):
    if len(cacheDict) == 0:
        print('Fetching Team IDs from Sportradar...')
        print('-'*40)
        conn = http.client.HTTPSConnection("api.sportradar.us")
        conn.request("GET", "/nba/trial/v5/en/league/hierarchy.xml?api_key={}".format(api_key))
        res = conn.getresponse()
        data = res.read()
        data2 = data.decode("utf-8")
        data3 = BeautifulSoup(data2, features='xml')
        teams = data3.find_all('team')
        for team in teams:
            id = team.get('id')
            tName = team.get('market') + ' ' + team.get('name')
            cacheDict[tName] = id
        dump_cache = json.dumps(cacheDict)
        outfile = open(fileName, 'w')
        outfile.write(dump_cache)
        outfile.close()

    elif len(cacheDict) > 0:
        print('Retrieving Team IDs from cache...')
        print('-'*40)


    return cacheDict

# ------------------------------------------------------------------------------

def getPlayerInfo(api_key, teamIDDict, conn, cur):
    cur.execute('CREATE TABLE IF NOT EXISTS Players (team TEXT, name TEXT, position TEXT, height INTEGER)')
    db = cur.execute('SELECT * FROM Players')
    dbl = len(db.fetchall())
    if dbl == 0:
        print('Fetching data from Sportradar and creating database.\nThis will take a couple minutes...')
        print('-'*40)
        for v in teamIDDict.values():
            sr_conn = http.client.HTTPSConnection("api.sportradar.us")
            sr_conn.request("GET", "/nba/trial/v5/en/teams/{}/profile.xml?api_key={}".format(v, api_key))
            res = sr_conn.getresponse()
            data = res.read()
            data2 = data.decode("utf-8")
            data3 = BeautifulSoup(data2, features='xml')
            player_tuples = []
            players = data3.find_all('player')
            team_info = data3.find('team')
            team_name = team_info.get('market') + ' ' + team_info.get('name')
            for player in players:
                pName = player.get('full_name')
                pHeight = player.get('height')
                pTeam = team_name
                pPosition = player.get('primary_position')
                pTuple = (pTeam, pName, pPosition, pHeight)
                player_tuples.append(pTuple)
                cur.execute('INSERT INTO Players (team, name, position, height) VALUES (?, ?, ?, ?)', (pTeam, pName, pPosition, int(pHeight)))
                conn.commit()
            print('Data for {} players has been fetched and entered into database'.format(team_name))
            time.sleep(2)
    elif dbl > 0:
        print('Database already exists and contains all necessary player information.')
        print('-'*40)

# ------------------------------------------------------------------------------

def getPositionHeightInfo(cur):
    positions = [('Point Guard (PG)','PG'), ('Shooting Guard (SG)','SG'), ('Small Forward (SF)','SF'), ('Power Forward (PF)','PF'), ('Center (C)','C')]
    position_dict = {}
    for p in positions:
        cur.execute('SELECT * FROM Players WHERE position = ?', (p[1], ))
        height_list = [row[3] for row in cur]
        position_dict[p[0]] = height_list
    return position_dict

# ------------------------------------------------------------------------------

def makePositionDistribution(dict):
    print('-- POSITION INFO --\n')
    for d in dict:
        print('Position: {}\nMax Height: {} inches\nMin Height: {} inches\nAvg Height: {} inches'.format(d, max(dict[d]), min(dict[d]), round(sum(dict[d])/len(dict[d]), 2)))
        print('')
    sorted_dict = sorted(dict.items(), key=lambda x: min(x[1]))
    figure = plt.figure(1)
    ax = figure.add_subplot(111)
    boxplot1 = ax.boxplot([x[1] for x in sorted_dict], labels=['PG', 'SG', 'SF', 'PF', 'C'], patch_artist=True)
    for b in boxplot1['boxes']:
        b.set(color='#ecaef0')
        b.set(facecolor='#aef0ec')
    for m in boxplot1['medians']:
        m.set(color='#f0aeb2', linewidth=2)
    for w in boxplot1['whiskers']:
        w.set(color='#ecaef0')
    for c in boxplot1['caps']:
        c.set(color='#ecaef0')
    for f in boxplot1['fliers']:
        f.set(color='#aef0ec', alpha=0.5)
    plt.xlabel('Positions')
    plt.ylabel('Height (in inches)')
    plt.title('Boxplot Distributions of Heights for NBA positions')
    plt.show()
    plt.savefig('position_boxplots.png')

# ------------------------------------------------------------------------------

def getTeamHeightAvg(teamIDDict, cur):
    teams = [t for t in teamIDDict.keys()]
    team_dict = {}
    for team in teams:
        cur.execute('SELECT * FROM Players WHERE team = ?', (team,))
        height_list = [row[3] for row in cur]
        team_dict[team] = height_list
    team_tuples = []
    for tup in team_dict.items():
        avg_height = sum(tup[1])/len(tup[1])
        team_tuples.append((tup[0], avg_height))
    return team_tuples

# ------------------------------------------------------------------------------

def makeTeamHeightDistribution(tupList):
    sorted_teams = sorted(tupList, key=lambda x: x[1])
    teams = [x[0] for x in sorted_teams]
    averages = [x[1] for x in sorted_teams]
    print('Tallest team in the NBA on average: {} - {} inches\n'.format(sorted_teams[-1][0], round(sorted_teams[-1][1], 2)))
    print('Shortest team in the NBA on average: {} - {} inches\n'.format(sorted_teams[0][0], round(sorted_teams[0][1], 2)))
    print('Average height in the NBA: {} inches'.format(round(sum(averages)/len(averages), 2)))
    plt.barh(teams, averages, color=(0.5, 0.8, 0.2, 0.6))
    plt.xlim(77,80.5)
    plt.ylabel('NBA Teams')
    plt.xlabel('Average Height (in inches)')
    plt.title('Average Player Heights for all NBA teams')
    plt.show()
    plt.savefig('TeamHeightDist.png')


# ------------------------------------------------------------------------------

def runAll(api_key):
    print("Welcome! Ever been curious about NBA players' heights? Let's collect some data about it!")
    print("="*40)
    time.sleep(1)
    CACHE_FNAME = 'TeamIDCache.json'
    try:
        cache_file = open(CACHE_FNAME, 'r')
        cache_data = cache_file.read()
        cache_dict = json.loads(cache_data)
        cache_file.close()
    except:
        cache_dict = {}
    team_ids = getTeamIDs(api_key, cache_dict, CACHE_FNAME)
    conn = sqlite3.connect('NBA_players.sqlite')
    cur = conn.cursor()
    user_input = input("Enter '1' to see the side-by-side boxplots and summary of NBA players' heights based on their position. Enter '2' to see the bar graph and summary of heights based on NBA teams.\nNOTE: the database must already exist in order to select '2'.\nIf it is not already created, please enter '1' first and then run the code again.\nEnter here: ")
    if user_input == '1':
        print("Now showing a summary and distribution for height based on position...\n")
        time.sleep(1)
        player_info = getPlayerInfo(api_key, team_ids, conn, cur)
        position_info = getPositionHeightInfo(cur)
        makePositionDistribution(position_info)
    elif user_input == '2':
        print("Now showing a summary and graph for average height based on team...\n")
        time.sleep(1)
        team_info = getTeamHeightAvg(team_ids, cur)
        makeTeamHeightDistribution(team_info)
    print("Thanks for stopping by! Hopefully you learned something new.")


runAll(api_key)
