# Tournament Planner

## Getting Started
1. Install [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/)
1. Clone this repository.
1. In the terminal, change directory to where you cloned the repository with `cd`. Then change directory to **vagrant** directory.
1. Run the command `vagrant up`. This will cause Vagrant to download the Linux operating system and install it. This may take quite a while (many minutes) depending on how fast your Internet connection is.
1. When `vagrant up` is finished running, you will get your shell prompt back. At this point, you can run `vagrant ssh` to log in to your newly installed Linux VM!
1. `cd` into `/vagrant/tournament`.
1. Launch the database with `psql` and import `tournament.sql`. This creates a database named `tournament` with two tables: `players` and `matches`.
```
vagrant@trusty32: psql
vagrant@trusty32: vagrant => \i tournament.sql;
```

## Running the test suite
1. At the `/vagrant/tournament` directory, run `python tournament_test.py`.
1. You should be able to see the following output:
```
vagrant@trusty32: python tournament_test.py
1. countPlayers() returns 0 after initial deletePlayers() execution.
2. countPlayers() returns 1 after one player is registered.
3. countPlayers() returns 2 after two players are registered.
4. countPlayers() returns zero after registered players are deleted.
5. Player records successfully deleted.
6. Newly registered players appear in the standings with no matches.
7. After a match, players have updated standings.
8. After match deletion, player standings are properly reset.
9. Matches are properly deleted.
10. After one match, players with one win are properly paired.
Success!  All tests pass!
```