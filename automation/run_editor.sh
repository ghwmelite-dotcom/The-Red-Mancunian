#!/usr/bin/env bash
# Build the /mufc-update prompt for unattended cloud runs and invoke claude.
# Env: EDITOR_MODE=baseline|breaking, WATCHER_HEADLINES (breaking only),
#      CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token` - subscription auth).
set -euo pipefail

PROMPT="/mufc-update UNATTENDED RUN: never wait for user input. On slow days do \
not render evergreen content - write the recommendation in your summary \
instead. Render both platform versions of any selected story."

if [ "${EDITOR_MODE:-baseline}" = "breaking" ]; then
  PROMPT="$PROMPT BREAKING MODE: the news watcher triggered this run for these \
new headlines - verify their dates and prioritise them, applying the playbook \
surge bar (score >= 6): ${WATCHER_HEADLINES:-unknown}"
fi

claude -p "$PROMPT" --model claude-sonnet-4-6 \
  --allowedTools "WebFetch,WebSearch,Read,Glob,Grep,Write,Bash(python tiktok/render.py:*),Bash(curl:*)"
