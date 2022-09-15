.DEFAULT_GOAL := all
sources = dnserver tests

.PHONY: install
install:
	pip install -U pip
	pip install -r requirements/all.txt
	pip install -e .
	pre-commit install

.PHONY: format
format:
	pyupgrade --py37-plus --exit-zero-even-if-changed `find $(sources) -name "*.py" -type f`
	isort $(sources)
	black $(sources)

.PHONY: lint
lint:
	flake8 $(sources)
	isort $(sources) --check-only --df
	black $(sources) --check --diff

.PHONY: test
test:
	coverage run -m pytest

.PHONY: testcov
testcov: test
	@echo "building coverage html"
	@coverage html

.PHONY: mypy
mypy:
	mypy dnserver

.PHONY: all
all: lint mypy testcov

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
