#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2
import bleach


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def deleteMatches():
    """Remove all the match records from the database."""
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE from matches")
    conn.commit()
    conn.close()


def deletePlayers():
    """Remove all the player records from the database."""
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE from players")
    conn.commit()
    conn.close()


def countPlayers():
    """Returns the number of players currently registered."""
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT count(name) AS num FROM players")
    count = int(c.fetchone()[0])
    conn.commit()
    conn.close()
    return count


def registerPlayer(name):
    """Adds a player to the tournament database.

    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)

    Args:
      name: the player's full name (need not be unique).
    """
    conn = connect()
    c = conn.cursor()
    q = "INSERT INTO players (name) VALUES (%s)"
    cName = bleach.clean(name)
    d = (cName,)
    c.execute(q, d)
    conn.commit()
    conn.close()


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a player
    tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
    """
    conn = connect()
    c = conn.cursor()
    q ='''\
        SELECT 
        winstable.id, winstable.name, winstable.wins, matchtable.matches 
        FROM 
            (SELECT 
            players.id, players.name, count(matches.winner) as wins
            FROM players LEFT JOIN matches 
            ON players.id = matches.winner 
            GROUP BY players.id) as winstable 
        LEFT JOIN 
            (SELECT 
            players.id, count(matches.id) as matches 
            FROM players LEFT JOIN matches 
            ON players.id = matches.player1 OR players.id = matches.player2 
            GROUP BY players.id) as matchtable
            ON winstable.id = matchtable.id
        ORDER BY winstable.wins DESC
        '''
    c.execute(q)
    standings = c.fetchall()
    conn.commit()
    conn.close()
    return standings


def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    conn = connect()
    c = conn.cursor()
    q = "INSERT INTO matches (player1, player2, winner) VALUES (%s, %s, %s)"
    cWinner = bleach.clean(winner)
    cLoser = bleach.clean(loser)
    d = ((cWinner,), (cLoser,), (cWinner,))
    c.execute(q, d)
    conn.commit()
    conn.close()


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.

    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.

    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    standings = playerStandings()
    pairings = []
    for i, (id, name, wins, matches) in enumerate(standings):
        if i % 2 == 0:
            pairings.append((id, name))
        else:
            pairings[(i-1)/2] += (id, name)    

    return pairings