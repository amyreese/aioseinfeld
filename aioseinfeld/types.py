# Copyright 2020 John Reese
# Licensed under the MIT License

import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional, Awaitable, Dict, NewType

Name = NewType("Name", str)


@dataclass
class Speaker:
    id: str
    name: Name


@dataclass
class Season:
    number: int
    episodes: Awaitable["Episodes"] = field(compare=False)


@dataclass
class Episode:
    id: int
    season: Season
    number: int
    title: str
    date: dt.date
    writers: List[Name]
    director: Name


@dataclass
class Quote:
    """One or more sentences from a single speaker in a single episode"""

    id: int
    episode: Episode
    number: int
    speaker: Speaker
    text: str


@dataclass
class Passage:
    """One or more quotes from a single episode"""

    id: int
    episode: Episode
    quotes: List[Quote]


Speakers = Dict[str, Speaker]
Episodes = List[Episode]
Seasons = Dict[int, Season]
