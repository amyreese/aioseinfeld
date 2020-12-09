aioseinfeld
===========

What's the deal with asyncio?


Install
-------

aioseinfeld requires Python 3.7 or newer. It can be installed from PyPI:

```shell-session
$ pip install aioseinfeld
```

aioseinfeld also depends on having a copy of the script database generated using 
[scripts by Colin Pollick](https://github.com/colinpollock/seinfeld-scripts).
You can build your own copy using those scripts, or download a prebuilt copy with
the following command:

```shell-session
$ wget https://noswap.com/pub/seinfeld.db
```


Usage
-----

aioseinfeld uses context managers to wrap the underlying sqlite database connection.
Create the `Seinfeld` object by passing the path to the `seinfeld.db` database:

```python
from aioseinfeld import Seinfeld

async with Seinfeld(db_path) as seinfeld:
    ...
```

Get information on individual episodes or seasons:

```python
async with Seinfeld(db_path) as seinfeld:
    season = await seinfeld.season(1)
    episodes = await season.episodes
    episodes[0].title  # "Good News, Bad News"
    episodes[0].writers # ["Jerry Seinfeld"]
    episodes[0].date  # date(1990, 6, 14)
```

Quotes can be retrieved by unique ID:

```python
async with Seinfeld(db_path) as seinfeld:
    quote = await seinfeld.quote(34665)
    quote.speaker.name  # "George"
    quote.episode.title  # "The Pitch"
    quote.text  # "The show is about nothing."
```

Quotes can also be found by searching:

```python
async with Seinfeld(db_path) as seinfeld:
    await seinfeld.search(speaker="Jerry", subject="keys")  # [Quote(...), ...]
```

You can even get random quotes with optional search parameters:

```python
async with Seinfeld(db_path) as seinfeld:
    await seinfeld.random()  # Quote(...)
    await seinfeld.random(subject="parking")  # Quote(...)
```

If you want more context around a quote, passages help:

```python
async with Seinfeld(db_path) as seinfeld:
    quote = await seinfeld.random()
    passage = await seinfeld.passage(quote, length=5)
    passage.quotes # [Quote(...), ...]
```


License
-------

aiomultiprocess is copyright [John Reese](https://jreese.sh), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.
