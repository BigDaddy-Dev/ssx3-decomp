#!/bin/sh
# One writer on one function; see tools/agents/dispatch.py.
exec python3 "$(dirname "$0")/dispatch.py" "$@"
