#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="${TMPDIR:-/tmp}/pattern_matching_sweep"
mkdir -p "$TMP_DIR"

read -r -a NS <<< "${N_VALUES:-32 64 128 256}"
read -r -a MS <<< "${M_VALUES:-8 16}"
read -r -a KS <<< "${K_VALUES:-1 8 16}"
read -r -a CASES <<< "${CASE_VALUES:-exact wildcard approximate}"

make_text() {
    local n="$1"
    local out="$2"
    local alphabet="abcdefghijklmnopqrstuvwxyz"
    local idx
    : > "$out"
    for ((idx = 0; idx < n; idx++)); do
        printf "%s" "${alphabet:idx%${#alphabet}:1}" >> "$out"
    done
}

repeat_char() {
    local ch="$1"
    local count="$2"
    local idx
    for ((idx = 0; idx < count; idx++)); do
        printf "%s" "$ch"
    done
}

make_patterns() {
    local case_name="$1"
    local text_file="$2"
    local m="$3"
    local k="$4"
    local out="$5"
    local text
    text="$(cat "$text_file")"
    local exact_pattern="${text:$((${#text} - m)):m}"
    local target_pattern="$exact_pattern"

    if [[ "$case_name" == "wildcard" ]]; then
        target_pattern="${exact_pattern:0:2}*${exact_pattern:3}"
    elif [[ "$case_name" == "approximate" ]]; then
        local replacement="z"
        if [[ "${exact_pattern:2:1}" == "z" ]]; then
            replacement="y"
        fi
        target_pattern="${exact_pattern:0:2}${replacement}${exact_pattern:3}"
    fi

    : > "$out"
    local idx
    for ((idx = 1; idx < k; idx++)); do
        repeat_char "Q" "$m" >> "$out"
        printf "\n" >> "$out"
    done
    printf "%s\n" "$target_pattern" >> "$out"
}

cmake --build "$ROOT_DIR/build"

for n in "${NS[@]}"; do
    text_file="$TMP_DIR/text_n${n}.txt"
    make_text "$n" "$text_file"

    for m in "${MS[@]}"; do
        if (( m >= n )); then
            continue
        fi

        for k in "${KS[@]}"; do
            for case_name in "${CASES[@]}"; do
                pattern_file="$TMP_DIR/patterns_${case_name}_n${n}_m${m}_k${k}.txt"
                make_patterns "$case_name" "$text_file" "$m" "$k" "$pattern_file"

                echo
                echo "============================================================"
                echo "case=$case_name n=$n m=$m K=$k"
                echo "============================================================"

                if [[ "$case_name" == "approximate" ]]; then
                    "$ROOT_DIR/build/pattern_matching" \
                        --text "$text_file" \
                        --pattern "$pattern_file" \
                        --threshold "$((m - 1))" \
                        --quiet
                else
                    "$ROOT_DIR/build/pattern_matching" \
                        --text "$text_file" \
                        --pattern "$pattern_file" \
                        --quiet
                fi
            done
        done
    done
done
