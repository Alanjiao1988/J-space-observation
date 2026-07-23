git() {
    printf '%s\n' "${INTERPOSITION_SECRET:-interposition-ran}"
    if [[ -n "${INTERPOSITION_MARKER:-}" ]]; then
        printf 'interposed\n' >"${INTERPOSITION_MARKER}"
    fi
    return 99
}

python() {
    git "$@"
}

export -f git python
