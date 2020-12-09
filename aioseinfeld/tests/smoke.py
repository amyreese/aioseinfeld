# Copyright 2020 John Reese
# Licensed under the MIT license

from aiounittest import AsyncTestCase

from aioseinfeld import Seinfeld, Quote

DB = "seinfeld.db"


class SmokeTest(AsyncTestCase):
    """
    Tests dependent on having a copy of https://noswap.com/pub/seinfeld.db

    `make test` will fetch this artifact before running these tests.
    """

    maxDiff = None

    async def test_seasons(self):
        async with Seinfeld(DB) as seinfeld:
            seasons = await seinfeld.seasons()
            self.assertEqual(len(seasons), 9)

    async def test_episodes_per_season(self):
        expected = {
            1: 4,
            2: 12,
            3: 23,
            4: 24,
            5: 21,
            6: 22,
            7: 24,
            8: 22,
            9: 21,
        }
        async with Seinfeld(DB) as seinfeld:
            for season_number in expected:
                with self.subTest(f"season{season_number}"):
                    episodes = await seinfeld.episodes(season_number)
                    self.assertEqual(len(episodes), expected[season_number])

            with self.subTest("all"):
                episodes = await seinfeld.episodes()
                self.assertEqual(len(episodes), sum(expected.values()))

    async def test_quote_by_id(self):
        async with Seinfeld(DB) as seinfeld:
            episode = await seinfeld.episode(1)
            speaker = await seinfeld.speaker("george")

            expected = Quote(
                id=78,
                episode=episode,
                number=78,
                speaker=speaker,
                text="You're gonna overdry it.",
            )

            quote = await seinfeld.quote(78)
            self.assertEqual(quote, expected)

    async def test_search_specific(self):
        async with Seinfeld(DB) as seinfeld:
            episode = await seinfeld.episode(26)
            speaker = await seinfeld.speaker("george")
            expected = [
                Quote(
                    id=7485,
                    episode=episode,
                    number=222,
                    speaker=speaker,
                    text=(
                        "Mothers say things. "
                        "My mother goes babbling on and on like a crazy person."
                    ),
                )
            ]

            quotes = await seinfeld.search(
                speaker=speaker, subject="My mother goes babbling"
            )
            self.assertEqual(len(quotes), 1)
            self.assertEqual(quotes, expected)

    async def test_search_parking(self):
        async with Seinfeld(DB) as seinfeld:
            jerry = await seinfeld.speaker("Jerry")
            quotes = await seinfeld.search(speaker="jerry", subject="parking")
            for quote in quotes:
                self.assertEqual(quote.speaker, jerry)
                self.assertIn("parking", quote.text)

    async def test_random(self):
        async with Seinfeld(DB) as seinfeld:
            jerry = await seinfeld.speaker("jerry")
            for i in range(10):
                quote = await seinfeld.random(speaker="jerry")
                self.assertEqual(quote.speaker, jerry)
