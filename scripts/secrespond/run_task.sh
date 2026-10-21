#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
    cat <<'EOF'
Usage:
  run_task.sh <range> --output-dir <dir> [options]

Options:
  --model <provider/model>     OpenCode model. Uses the OpenCode default if omitted.
  --platform <linux|windows>   Override automatic platform selection.
  --data-dir <dir>             SecRespond data root (default: <repo>/data/secrespond).
  --disk-path <dir>            Override ranges/<range>/disk.
  --sas-path <dir>             Override ranges/<range>/sas-mock.
  --prepare-only               Render and validate the workspace without running a model.
  -h, --help                   Show this help.

Environment:
  SECRESPOND_DATA_DIR          Default for --data-dir.

This task runner uses only task-prompts/linux.md or task-prompts/windows.md.
EOF
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

info() {
    printf '==> %s\n' "$*"
}

need_value() {
    local flag="$1" remaining="$2"
    [[ "$remaining" -ge 2 ]] || die "$flag requires a value"
}

canonical_dir() {
    local path="$1" label="$2"
    [[ -d "$path" ]] || die "$label not found: $path"
    (cd "$path" && pwd -P)
}

canonical_file() {
    local path="$1" label="$2"
    local parent name
    [[ -f "$path" ]] || die "$label not found: $path"
    parent="$(cd "$(dirname "$path")" && pwd -P)"
    name="$(basename "$path")"
    printf '%s/%s\n' "$parent" "$name"
}

render_template() {
    local src="$1" dst="$2"
    shift 2

    [[ $(( $# % 2 )) -eq 0 ]] || die "render_template expects KEY VALUE pairs"
    cp "$src" "$dst"

    while [[ $# -ge 2 ]]; do
        local key="$1" value="$2" escaped tmp
        shift 2
        escaped="$(printf '%s\n' "$value" | sed 's/[&|\\]/\\&/g')"
        tmp="$(mktemp "${dst}.XXXXXX")"
        sed "s|{{${key}}}|${escaped}|g" "$dst" > "$tmp"
        mv "$tmp" "$dst"
    done

    local unresolved
    unresolved="$(LC_ALL=C grep -Eo '\{\{[A-Z_]+\}\}' "$dst" | sort -u | tr '\n' ' ' || true)"
    [[ -z "$unresolved" ]] || die "Unresolved placeholders in $dst: $unresolved"
}

range_platform() {
    case "$1" in
        aspnet-viewstate|rdp-service-abuse) printf 'windows\n' ;;
        *)                                 printf 'linux\n' ;;
    esac
}

main() {
    local range=""
    local output_dir=""
    local model=""
    local platform=""
    local data_dir="${SECRESPOND_DATA_DIR:-$REPO_ROOT/data/secrespond}"
    local disk_path=""
    local sas_path=""
    local prepare_only=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output-dir)
                need_value "$1" "$#"
                output_dir="$2"
                shift 2
                ;;
            --model)
                need_value "$1" "$#"
                model="$2"
                shift 2
                ;;
            --platform)
                need_value "$1" "$#"
                platform="$2"
                shift 2
                ;;
            --data-dir)
                need_value "$1" "$#"
                data_dir="$2"
                shift 2
                ;;
            --disk-path)
                need_value "$1" "$#"
                disk_path="$2"
                shift 2
                ;;
            --sas-path)
                need_value "$1" "$#"
                sas_path="$2"
                shift 2
                ;;
            --prepare-only)
                prepare_only=1
                shift
                ;;
            -h|--help)
                usage
                return 0
                ;;
            -*)
                die "Unknown flag: $1"
                ;;
            *)
                [[ -z "$range" ]] || die "Multiple ranges provided: $range and $1"
                range="$1"
                shift
                ;;
        esac
    done

    [[ -n "$range" ]] || die "Missing <range>. See --help."
    [[ "$range" =~ ^[A-Za-z0-9._-]+$ ]] || die "Invalid range name: $range"
    [[ -n "$output_dir" ]] || die "Missing --output-dir <dir>"

    data_dir="$(canonical_dir "$data_dir" "SecRespond data directory")"
    local range_dir="$data_dir/ranges/$range"
    range_dir="$(canonical_dir "$range_dir" "Range directory")"

    if [[ -z "$platform" ]]; then
        platform="$(range_platform "$range")"
    fi
    case "$platform" in
        linux|windows) ;;
        *) die "Invalid platform: $platform (expected linux or windows)" ;;
    esac

    [[ -n "$disk_path" ]] || disk_path="$range_dir/disk"
    [[ -n "$sas_path" ]] || sas_path="$range_dir/sas-mock"
    disk_path="$(canonical_dir "$disk_path" "Extracted forensic disk")"
    sas_path="$(canonical_dir "$sas_path" "SAS directory")"
    [[ -n "$(find "$disk_path" -mindepth 1 -maxdepth 1 -print -quit)" ]] \
        || die "Extracted forensic disk is empty: $disk_path"

    local prompt_path="$data_dir/task-prompts/$platform.md"
    prompt_path="$(canonical_file "$prompt_path" "Task prompt")"

    [[ ! -e "$output_dir" ]] || die "Output path already exists: $output_dir"
    mkdir -p "$output_dir"
    output_dir="$(canonical_dir "$output_dir" "Output directory")"

    render_template \
        "$prompt_path" \
        "$output_dir/CLAUDE.md" \
        "DISK_PATH" "$disk_path" \
        "SAS_PATH" "$sas_path" \
        "OUTPUT_PATH" "$output_dir"

    info "Range:      $range"
    info "Platform:   $platform"
    info "Prompt:     $prompt_path"
    info "Disk:       $disk_path"
    info "SAS:        $sas_path"
    info "Output:     $output_dir"
    [[ -z "$model" ]] || info "Model:      $model"

    if [[ "$prepare_only" -eq 1 ]]; then
        info "Prepared workspace only; model was not run."
        return 0
    fi

    command -v opencode >/dev/null 2>&1 || die "opencode not found in PATH"

    local -a command=(opencode run --auto --format json)
    [[ -z "$model" ]] || command+=(-m "$model")
    command+=(
        "Please read CLAUDE.md in the current directory and perform the incident-response task exactly as instructed."
    )

    local rc=0
    (
        cd "$output_dir"
        "${command[@]}" > session-events.jsonl
    ) || rc=$?

    local required=(
        progress.md
        intrusion-report.md
        vuln-report.md
        baseline-report.md
        remediation-plan.md
    )
    local missing=()
    local file
    for file in "${required[@]}"; do
        [[ -f "$output_dir/$file" ]] || missing+=("$file")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        printf 'WARN: Task outputs are incomplete; missing: %s\n' "${missing[*]}" >&2
        [[ "$rc" -ne 0 ]] || rc=4
    fi

    info "Task finished with exit code $rc."
    info "Workspace: $output_dir"
    return "$rc"
}

main "$@"
