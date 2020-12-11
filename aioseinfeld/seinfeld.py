# Copyright 2020 John Reese
# Licensed under the MIT License


from contextlib import AsyncExitStack
from functools import wraps
from pathlib import Path
from typing import TypeVar, Callable, Awaitable, Optional, Union, Dict, Any, cast, List

import aiosqlite

from .types import (
    Speaker,
    Episode,
    Season,
    Quote,
    Passage,
    Speakers,
    Episodes,
    Seasons,
    Name,
)

T = TypeVar("T")
Coro = Callable[..., Awaitable[T]]


def cached(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    cache: Optional[T] = None

    @wraps(fn)
    async def wrapper(*args):
        nonlocal cache
        if cache is None:
            cache = await fn(*args)
        return cache

    return wrapper


class CacheLater(Awaitable[T]):
    def __init__(self, coro: Coro, **kwargs):
        self.coro: Optional[Coro] = coro
        self.kwargs: Dict[str, Any] = kwargs
        self.result: Optional[T] = None

    def __await__(self):
        return self.fetch().__await__()

    async def fetch(self) -> T:
        if self.coro is not None:
            self.result = await self.coro(**self.kwargs)
            self.coro = None

        return cast(T, self.result)


class Seinfeld:
    def __init__(self, db_path: Union[str, Path]):
        self.db: aiosqlite.Connection
        self.db_path: Path = Path(db_path)
        if not self.db_path.is_file():
            raise ValueError(f"db_path {db_path!r} does not exist")

        self.stack = AsyncExitStack()

    async def __aenter__(self) -> "Seinfeld":
        self.db = await self.stack.enter_async_context(aiosqlite.connect(self.db_path))
        self.db.row_factory = aiosqlite.Row

        await self.db.execute(
            """
            CREATE TEMPORARY VIEW IF NOT EXISTS quote AS
            SELECT u.id, u.episode_id, u.utterance_number,
            u.speaker, group_concat(s.text, " ") text
            FROM utterance u
            JOIN sentence s ON u.id = s.utterance_id
            GROUP BY u.id
            ORDER BY u.episode_id asc, u.utterance_number asc,
            s.sentence_number asc
        """
        )

        return self

    async def __aexit__(self, *args) -> None:
        await self.stack.aclose()

    @cached
    async def speakers(self) -> Speakers:
        async with self.db.execute("select distinct speaker from utterance") as cursor:
            ids = [row["speaker"] async for row in cursor]
            return {id.casefold(): Speaker(id, Name(id.capitalize())) for id in ids}

    async def speaker(self, name: str) -> Speaker:
        spkr = (await self.speakers()).get(name.casefold(), None)
        if spkr is None:
            return Speaker(name, Name(name.capitalize()))
        return spkr

    @cached
    async def seasons(self) -> Seasons:
        async with self.db.execute(
            "select distinct season_number from episode order by season_number asc"
        ) as cursor:
            return {
                row["season_number"]: Season(
                    number=row["season_number"],
                    episodes=CacheLater(
                        self.episodes, season_number=row["season_number"]
                    ),
                )
                async for row in cursor
            }

    async def season(self, number: int) -> Optional[Season]:
        return (await self.seasons()).get(number, None)

    async def episodes(self, season_number: Optional[int] = None) -> Episodes:
        where = ""
        params = []
        if season_number:
            where = "where season_number = ?"
            params = [season_number]

        async with self.db.execute(
            f"""
            select id, season_number, episode_number, title, the_date, writer, director
            from episode
            {where}
            order by season_number asc, episode_number asc
            """,
            params,
        ) as cursor:
            return [
                Episode(
                    id=row["id"],
                    season=Season(
                        row["season_number"],
                        CacheLater(self.episodes, season_number=row["season_number"]),
                    ),
                    number=row["episode_number"],
                    title=row["title"],
                    date=row["the_date"],
                    writers=[w.strip().capitalize() for w in row["writer"].split(",")],
                    director=row["director"].capitalize(),
                )
                async for row in cursor
            ]

    async def episode(self, id: int) -> Optional[Episode]:
        async with self.db.execute(
            """
            select id, season_number, episode_number, title, the_date, writer, director
            from episode
            where id = ?
            """,
            [id],
        ) as cursor:
            row = await cursor.fetchone()
            if row is not None:
                return Episode(
                    id=row["id"],
                    season=Season(
                        row["season_number"],
                        CacheLater(self.episodes, season_number=row["season_number"]),
                    ),
                    number=row["episode_number"],
                    title=row["title"],
                    date=row["the_date"],
                    writers=[w.strip().capitalize() for w in row["writer"].split(",")],
                    director=row["director"].capitalize(),
                )
            return None

    async def quote(self, id: int) -> Optional[Quote]:
        async with self.db.execute(
            """
            select id, episode_id, utterance_number, speaker, text
            from quote
            where id = ?
            """,
            [id],
        ) as cursor:
            row = await cursor.fetchone()
            if row is not None:
                episode = await self.episode(row["episode_id"])
                if episode is None:
                    raise ValueError(f"episode_id {row['episode_id']} not found")
                return Quote(
                    id=row["id"],
                    episode=episode,
                    number=row["utterance_number"],
                    speaker=await self.speaker(row["speaker"]),
                    text=row["text"],
                )
            return None

    async def passage(self, quote: Quote, length: int = 5) -> Passage:
        half = length // 2
        middle = quote.number
        start = middle - half if middle > half else 1
        end = start + length - 1

        query = """
            select id, episode_id, utterance_number, speaker, text
            from quote
            where episode_id = ? and
                utterance_number >= ? and utterance_number <= ?
            order by utterance_number
        """

        async with self.db.execute(query, (quote.episode.id, start, end)) as cursor:
            quotes = [
                Quote(
                    id=row["id"],
                    episode=quote.episode,
                    number=row["utterance_number"],
                    speaker=await self.speaker(row["speaker"]),
                    text=row["text"],
                )
                async for row in cursor
            ]
            return Passage(quote.id, quote.episode, quotes)

    async def search(
        self,
        speaker: Union[Speaker, str, None] = None,
        subject: Optional[str] = None,
        limit: int = 10,
        reverse: bool = False,
        random: bool = False,
    ) -> List[Quote]:
        query = """
            select id, episode_id, utterance_number, speaker, text
            from quote
        """

        wheres = []
        params: List[Any] = []

        if speaker:
            wheres.append("speaker = ?")
            if isinstance(speaker, Speaker):
                params.append(speaker.id)
            else:
                params.append((await self.speaker(speaker)).id)

        if subject:
            wheres.append("text like ?")
            params.append(f"%{subject}%")

        if wheres:
            where = " and ".join(wheres)
            query += f" where {where}"

        if random:
            query += " order by RANDOM()"
        elif reverse:
            query += " order by episode_id desc, utterance_number desc"
        else:
            query += " order by episode_id asc, utterance_number asc"

        if limit > 0:
            query += " limit ?"
            params.append(limit)

        results: List[Quote] = []
        async with self.db.execute(query, params) as cursor:
            async for row in cursor:
                episode = await self.episode(row["episode_id"])
                if episode is None:
                    raise ValueError(f"episode_id {row['episode_id']} not found")
                results.append(
                    Quote(
                        id=row["id"],
                        episode=episode,
                        number=row["utterance_number"],
                        speaker=await self.speaker(row["speaker"]),
                        text=row["text"],
                    )
                )

        return results

    async def random(
        self, speaker: Union[Speaker, str, None] = None, subject: Optional[str] = None
    ) -> Optional[Quote]:
        quotes = await self.search(
            speaker=speaker, subject=subject, limit=1, random=True
        )

        if quotes:
            return quotes[0]
        return None
