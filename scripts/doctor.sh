#!/usr/bin/env sh
set -eu

expected_python="${PYTHON_VERSION:-3.13}"
expected_node="${NODE_VERSION:-24}"
# A floor, not a pin. CI installs an exact uv so its runs are reproducible, but a
# developer machine only needs a uv new enough to read uv.lock -- and Homebrew
# ships a newer one than the CI pin, so demanding equality here fails every brew
# install forever. Python and Node below are already checked loosely; this matches.
minimum_uv="${UV_VERSION:-0.12.13}"
errors=0

pass() {
    printf 'ok  %s\n' "$1"
}

fail() {
    printf 'ERR %s\n' "$1" >&2
    errors=$((errors + 1))
}

# True when $1 is an older version than $2, comparing dot-separated numbers.
# Field-by-field, so 0.12.9 correctly sorts before 0.12.13 where a string
# comparison would not. Missing trailing fields count as zero.
version_lt() {
    awk -v have="$1" -v want="$2" '
        BEGIN {
            n_have = split(have, a, ".")
            n_want = split(want, b, ".")
            n = (n_have > n_want ? n_have : n_want)
            for (i = 1; i <= n; i++) {
                x = (i <= n_have ? a[i] + 0 : 0)
                y = (i <= n_want ? b[i] + 0 : 0)
                if (x < y) exit 0
                if (x > y) exit 1
            }
            exit 1
        }'
}

require_command() {
    command_name="$1"
    if command -v "$command_name" >/dev/null 2>&1; then
        pass "$command_name is available"
    else
        fail "$command_name is missing"
    fi
}

for command_name in git uv node npm docker make; do
    require_command "$command_name"
done

if command -v uv >/dev/null 2>&1; then
    actual_uv="$(uv --version | awk '{print $2}')"
    if version_lt "$actual_uv" "$minimum_uv"; then
        fail "uv $actual_uv is older than the required $minimum_uv (run: uv self update)"
    else
        pass "uv version is $actual_uv (minimum $minimum_uv)"
    fi

    if python_path="$(uv python find "$expected_python" 2>/dev/null)"; then
        actual_python="$($python_path -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        if [ "$actual_python" = "$expected_python" ]; then
            pass "Python version is $actual_python ($python_path)"
        else
            fail "Python $actual_python found at $python_path; expected $expected_python"
        fi
    else
        fail "Python $expected_python is not installed (run: uv python install $expected_python)"
    fi
fi

if command -v node >/dev/null 2>&1; then
    actual_node="$(node --version | sed 's/^v//' | cut -d. -f1)"
    if [ "$actual_node" = "$expected_node" ]; then
        pass "Node major version is $actual_node"
    else
        fail "Node major version is $actual_node; expected $expected_node"
    fi
fi

if command -v docker >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1; then
        pass "Docker Compose is available"
    else
        fail "Docker Compose plugin is unavailable"
    fi
fi

for required_file in uv.lock frontend/package-lock.json compose.yaml .env.example; do
    if [ -f "$required_file" ]; then
        pass "$required_file exists"
    else
        fail "$required_file is missing"
    fi
done

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    if docker compose config --quiet; then
        pass "compose.yaml is valid"
    else
        fail "compose.yaml is invalid"
    fi
fi

if [ "$errors" -ne 0 ]; then
    printf '\nDoctor found %s problem(s). Use the dev container or install the pinned tools.\n' "$errors" >&2
    exit 1
fi

printf '\nDevelopment environment is ready.\n'
