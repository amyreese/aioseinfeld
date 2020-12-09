.venv:
	python -m venv .venv
	source .venv/bin/activate && make setup dev
	echo 'run `source .venv/bin/activate` to develop aioseinfeld'

venv: .venv

setup:
	python -m pip install -Ur requirements.txt
	python -m pip install -Ur requirements-dev.txt

dev:
	flit install --symlink

release: lint test clean
	flit publish

format:
	python -m usort format aioseinfeld
	python -m black aioseinfeld

lint:
	python -m usort check aioseinfeld
	python -m black --check aioseinfeld

seinfeld.db:
	python -c "import urllib.request; urllib.request.urlretrieve('https://noswap.com/pub/seinfeld.db', 'seinfeld.db')"

test: seinfeld.db
	python -m coverage run -m aioseinfeld.tests
	python -m coverage report
	python -m mypy aioseinfeld/*.py

clean:
	rm -rf build dist html README MANIFEST *.egg-info

distclean: clean
	rm -rf .venv
