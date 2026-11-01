#!/bin/sh
# Install the game-material guard as this clone's pre-commit hook.
set -e
cd "$(git rev-parse --show-toplevel)"
ln -sf ../../tools/hooks/pre-commit "$(git rev-parse --git-common-dir)/hooks/pre-commit"
echo "pre-commit guard installed"
