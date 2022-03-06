.DEFAULT_GOAL = help
PYTHON ?= python3.8
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

ifneq ($(wildcard $(ROOT_DIR)/.venv/.),)
	VENV_PYTHON = $(ROOT_DIR)/.venv/bin/python
else
	VENV_PYTHON = $(PYTHON)
endif

define HELP_BODY
Usage:
	make <command>

Commands:
	reformat	Reformat all the python files in the workspace
	newenv		Create a new env for the workspace
endef
export HELP_BODY

reformat:
	$(VENV_PYTHON) -m black -l 99 $(ROOT_DIR)
	$(VENV_PYTHON) -m isort -l 99 $(ROOT_DIR)

newenv:
	$(PYTHON) -m venv --clear .venv
	.venv/bin/python -m pip install -U pip setuptools wheel black isort git+https://github.com/Rapptz/discord.py@master mypy databases databases[sqlite]

help:
	@echo "$$HELP_BODY"