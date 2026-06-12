#!/usr/bin/env bash
# Build the /mufc-update prompt for unattended cloud runs and invoke claude.
# Env: EDITOR_MODE=baseline|breaking, WATCHER_HEADLINES (breaking only),
#      CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token` - subscription auth).
set -euo pipefail

PROMPT="/mufc-update UNATTENDED RUN: never wait for user input. The account's \
goal is DAILY engagement on every platform, and the editor in Telegram \
approves every video before posting - so on slow days render ONE evergreen \
story (ACADEMY, nostalgia, or United players at the World Cup) instead of \
posting nothing; a weak video gets rejected on the phone, a missing video \
cannot. Mix categories - this is not a transfers-only account: MATCHDAY, \
CLUB and ACADEMY stories score on their own merits per the playbook. Render \
both platform versions of any selected story."

if [ "${EDITOR_MODE:-baseline}" = "breaking" ]; then
  PROMPT="$PROMPT BREAKING MODE: the news watcher triggered this run for these \
new headlines - verify their dates and prioritise them, applying the playbook \
surge bar (score >= 6): ${WATCHER_HEADLINES:-unknown}"
fi

claude -p "$PROMPT" --model claude-sonnet-4-6 \
  --allowedTools "WebFetch,WebSearch,Read,Glob,Grep,Write,Bash(python tiktok/render.py:*),Bash(curl:*)"
