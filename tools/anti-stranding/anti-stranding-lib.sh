#!/bin/zsh
# Shared fail-closed ownership gate for anti-stranding push/PR/merge consumers.

anti_stranding_github_owner() {  # $1 remote URL; prints owner on success
  emulate -L zsh
  local remote="$1" rest authority user host remote_path owner repository host_lower

  case "$remote" in
    https://*)
      rest=${remote#https://}
      [[ "$rest" == */* ]] || return 1
      authority=${rest%%/*}
      remote_path=${rest#*/}
      host=${authority##*@}
      ;;
    ssh://*)
      rest=${remote#ssh://}
      [[ "$rest" == */* ]] || return 1
      authority=${rest%%/*}
      remote_path=${rest#*/}
      [[ "$authority" == *@* ]] || return 1
      user=${authority%@*}
      [ "$user" = "git" ] || return 1
      host=${authority##*@}
      ;;
    git@*:*)
      authority=${remote%%:*}
      remote_path=${remote#*:}
      user=${authority%@*}
      [ "$user" = "git" ] || return 1
      host=${authority##*@}
      ;;
    *) return 1;;
  esac

  # URL-form colons after the host are explicit ports. The scp-like colon
  # above was already consumed as its path separator.
  [[ "$host" != *:* ]] || return 1
  host_lower=$(print -rn -- "$host" | tr '[:upper:]' '[:lower:]')
  [ "$host_lower" = "github.com" ] || return 1

  [[ "$remote_path" == */* ]] || return 1
  owner=${remote_path%%/*}
  repository=${remote_path#*/}
  [[ "$repository" != */* ]] || return 1
  repository=${repository%.git}
  case "$owner" in ""|*[!A-Za-z0-9-]*) return 1;; esac
  case "$repository" in ""|*[!A-Za-z0-9._-]*) return 1;; esac

  print -r -- "$owner"
}

anti_stranding_remote_owner_ok() {  # $1 repo path; $2 expected GitHub login
  emulate -L zsh
  local repo="$1" expected="$2" effective_output raw_output raw_status owner
  local expected_lower owner_lower
  local -a effective_urls

  [ -n "$repo" ] && [ -n "$expected" ] || return 1
  effective_output=$(git -C "$repo" remote get-url --push --all origin 2>/dev/null) \
    || return 1
  [ -n "$effective_output" ] || return 1
  effective_urls=("${(@f)effective_output}")
  [ "${#effective_urls[@]}" -gt 0 ] || return 1

  # An absent configured pushurl is normal: Git falls back to the fetch URL.
  # When pushurls do exist, the raw and effective target lists must agree.
  raw_output=$(git -C "$repo" config --get-all remote.origin.pushurl 2>/dev/null)
  raw_status=$?
  if [ "$raw_status" = "0" ]; then
    [ -n "$raw_output" ] && [ "$raw_output" = "$effective_output" ] || return 1
  elif [ "$raw_status" != "1" ]; then
    return 1
  fi

  expected_lower=$(print -rn -- "$expected" | tr '[:upper:]' '[:lower:]')
  for remote in "${effective_urls[@]}"; do
    [ -n "$remote" ] || return 1
    owner=$(anti_stranding_github_owner "$remote") || return 1
    owner_lower=$(print -rn -- "$owner" | tr '[:upper:]' '[:lower:]')
    [ "$owner_lower" = "$expected_lower" ] || return 1
  done
}
