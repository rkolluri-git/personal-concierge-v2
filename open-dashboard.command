#!/bin/zsh
set -eu
cd "${0:A:h}"
key=$(<config/dashboard-access.key)
# Fragment is exchanged for an HttpOnly session, then removed from browser history.
open "http://localhost:8000/auth/login#access=$key"
