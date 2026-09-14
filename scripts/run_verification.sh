#!/usr/bin/env bash
# Interactive-safe wrapper. Use verify_project.py directly for an exit-code CI gate.
capstone_verify() {
  local capstone_root
  capstone_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || return 1
  python3 "$capstone_root/scripts/verify_project.py" "$@"
  return $?
}
capstone_verify "$@"
capstone_verify_status=$?
if [ "$capstone_verify_status" -ne 0 ]; then
  printf 'Verification returned status %s. Read the error above.\n' "$capstone_verify_status"
fi
true
