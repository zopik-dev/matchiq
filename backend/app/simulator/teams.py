"""Invented teams, players and stadium for MatchIQ synthetic matches.

Everything here is fictional. No real clubs, players, stadiums or branding.
Rosters are fixed so matches are comparable; match-to-match variation comes
from the seeded generator, not from roster changes.
"""

from app.models.events import Player, Position, Team

STADIUM = "Meridian Park"


def _players(prefix: str, names: list[tuple[str, int, Position]]) -> list[Player]:
    return [
        Player(id=f"{prefix}_{number}", name=name, number=number, position=position)
        for name, number, position in names
    ]


HOME_STARTERS: list[tuple[str, int, Position]] = [
    ("Bram Calloway", 1, Position.GK),
    ("Dane Whitfield", 2, Position.DF),
    ("Kellan Marsh", 4, Position.DF),
    ("Rhys Calder", 5, Position.DF),
    ("Owen Pritchard", 3, Position.DF),
    ("Finn Gallagher", 6, Position.MF),
    ("Theo Ashford", 8, Position.MF),
    ("Jude Merritt", 10, Position.MF),
    ("Cole Dempsey", 7, Position.FW),
    ("Harvey Quinn", 9, Position.FW),
    ("Ellis Thornton", 11, Position.FW),
]

HOME_SUBS: list[tuple[str, int, Position]] = [
    ("Mason Kettle", 13, Position.GK),
    ("Aiden Frost", 14, Position.DF),
    ("Rory Beckett", 16, Position.MF),
    ("Callum Driscoll", 18, Position.FW),
    ("Niall Fenwick", 20, Position.MF),
]

AWAY_STARTERS: list[tuple[str, int, Position]] = [
    ("Stefan Novak", 1, Position.GK),
    ("Petar Kovac", 2, Position.DF),
    ("Tomas Lindqvist", 4, Position.DF),
    ("Marek Zielinski", 5, Position.DF),
    ("Jonas Weber", 3, Position.DF),
    ("Pavel Horvat", 6, Position.MF),
    ("Luka Benedikt", 7, Position.MF),
    ("Emil Sorensen", 8, Position.MF),
    ("Viktor Aldane", 11, Position.MF),
    ("Dario Mensah", 9, Position.FW),
    ("Felix Okafor", 10, Position.FW),
]

AWAY_SUBS: list[tuple[str, int, Position]] = [
    ("Gregor Falken", 13, Position.GK),
    ("Sasha Petrov", 15, Position.DF),
    ("Milan Djuric", 16, Position.MF),
    ("Anton Heller", 17, Position.MF),
    ("Kristof Lang", 19, Position.FW),
]


def build_teams() -> tuple[Team, Team]:
    """Return the two fixed invented teams (home, away)."""
    home = Team(
        id="NGU",
        name="Northgate United",
        formation="4-3-3",
        roster=_players("NGU", HOME_STARTERS + HOME_SUBS),
    )
    away = Team(
        id="EVR",
        name="Eastvale Rovers",
        formation="4-4-2",
        roster=_players("EVR", AWAY_STARTERS + AWAY_SUBS),
    )
    return home, away
