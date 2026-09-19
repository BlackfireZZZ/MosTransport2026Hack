#!/usr/bin/env sh
set -eu

usage() {
    cat >&2 <<'EOF'
Usage:
  scripts/agent-env.sh env ID
  scripts/agent-env.sh path ID
  scripts/agent-env.sh create ID [REF]
  scripts/agent-env.sh remove ID

IDs must contain lowercase ASCII letters, digits, or hyphens and must start
with a letter or digit. Worktree removal refuses uncommitted changes and keeps
the agent branch intact.
EOF
    exit 2
}

validate_id() {
    id="$1"
    case "$id" in
        ''|*[!a-z0-9-]*|-*|*-)
            printf 'Invalid agent ID: %s\n' "$id" >&2
            exit 2
            ;;
    esac
    if [ "${#id}" -gt 40 ]; then
        printf 'Agent ID is too long (maximum: 40): %s\n' "$id" >&2
        exit 2
    fi
}

primary_worktree() {
    git worktree list --porcelain | awk '/^worktree / { sub(/^worktree /, ""); print; exit }'
}

worktree_path() {
    primary="$(primary_worktree)"
    base="${TRAMFLOW_WORKTREE_ROOT:-$(dirname "$primary")/$(basename "$primary")-worktrees}"
    printf '%s/%s\n' "$base" "$1"
}

print_env() {
    id="$1"
    checksum="$(printf '%s' "$id" | cksum | awk '{print $1}')"
    slot=$((checksum % 10000))
    postgres_port=$((20000 + slot))
    backend_port=$((30000 + slot))
    frontend_port=$((40000 + slot))

    printf "export COMPOSE_PROJECT_NAME='tramflow-agent-%s'\n" "$id"
    printf "export POSTGRES_PORT='%s'\n" "$postgres_port"
    printf "export BACKEND_PORT='%s'\n" "$backend_port"
    printf "export FRONTEND_PORT='%s'\n" "$frontend_port"
    printf "export BACKEND_CORS_ORIGINS='[\"http://localhost:5173\",\"http://localhost:%s\"]'\n" "$frontend_port"
}

create_worktree() {
    id="$1"
    ref="${2:-HEAD}"
    path="$(worktree_path "$id")"
    branch="agent/$id"

    if ! git rev-parse --verify "${ref}^{commit}" >/dev/null 2>&1; then
        printf 'Cannot create a worktree: ref %s is not a commit. Commit the reviewed baseline first.\n' "$ref" >&2
        exit 1
    fi
    if [ -e "$path" ]; then
        printf 'Worktree path already exists: %s\n' "$path" >&2
        exit 1
    fi

    mkdir -p "$(dirname "$path")"
    if git show-ref --verify --quiet "refs/heads/$branch"; then
        git worktree add "$path" "$branch"
    else
        git worktree add -b "$branch" "$path" "$ref"
    fi

    printf 'Created %s on branch %s\n' "$path" "$branch"
    print_env "$id"
}

remove_worktree() {
    id="$1"
    path="$(worktree_path "$id")"

    if [ ! -d "$path" ]; then
        printf 'Worktree does not exist: %s\n' "$path" >&2
        exit 1
    fi
    if [ -n "$(git -C "$path" status --porcelain)" ]; then
        printf 'Refusing to remove dirty worktree: %s\n' "$path" >&2
        printf 'Commit, stash, or manually resolve its changes first.\n' >&2
        exit 1
    fi

    git worktree remove "$path"
    printf 'Removed worktree %s; branch agent/%s was preserved.\n' "$path" "$id"
}

[ "$#" -ge 2 ] || usage
command_name="$1"
id="$2"
validate_id "$id"

case "$command_name" in
    env)
        [ "$#" -eq 2 ] || usage
        print_env "$id"
        ;;
    path)
        [ "$#" -eq 2 ] || usage
        worktree_path "$id"
        ;;
    create)
        [ "$#" -le 3 ] || usage
        create_worktree "$id" "${3:-HEAD}"
        ;;
    remove)
        [ "$#" -eq 2 ] || usage
        remove_worktree "$id"
        ;;
    *)
        usage
        ;;
esac
