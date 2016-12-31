-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.


DROP DATABASE IF EXISTS tournament;
CREATE DATABASE tournament;
\c tournament;
DROP TABLE IF EXISTS players, matches;
CREATE TABLE players(
	id serial primary key,
	name text
);
CREATE TABLE matches(
	id serial primary key,
	winner serial references players(id),
	loser serial references players(id)
);
