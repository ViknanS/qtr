#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
    cat <<'EOF'
Usage:
  run_evaluation.sh <range> --reports-dir <dir> --output-dir <dir> [options]

Options:
  --model <provider/model>     OpenCode model. Uses the OpenCode default if omitted.
  --data-dir <dir>             SecRespond data root (default: <repo>/data/secrespond).
  --prepare-only               Render and validate the workspace without running a model.
  -h, --help                   Show this help.

Environment:
  SECRESPOND_DATA_DIR          Default for --data-dir.

The evaluator receives the concrete checklist, report, Skill, and output paths
through evaluation/prompt.md.
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

main() {
    local range=""
    local reports_dir=""
    local output_dir=""
    local model=""
    local data_dir="${SECRESPOND_DATA_DIR:-$REPO_ROOT/data/secrespond}"
    local prepare_only=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --reports-dir)
                need_value "$1" "$#"
                reports_dir="$2"
                shift 2
                ;;
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
            --data-dir)
                need_value "$1" "$#"
                data_dir="$2"
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
    [[ -n "$reports_dir" ]] || die "Missing --reports-dir <dir>"
    [[ -n "$output_dir" ]] || die "Missing --output-dir <dir>"

    data_dir="$(canonical_dir "$data_dir" "SecRespond data directory")"
    local range_dir="$data_dir/ranges/$range"
    range_dir="$(canonical_dir "$range_dir" "Range directory")"
    reports_dir="$(canonical_dir "$reports_dir" "Detection reports directory")"

    local required_reports=(
        progress.md
        intrusion-report.md
        vuln-report.md
        baseline-report.md
        remediation-plan.md
    )
    local missing=()
    local file
    for file in "${required_reports[@]}"; do
        [[ -f "$reports_dir/$file" ]] || missing+=("$file")
    done
    [[ ${#missing[@]} -eq 0 ]] \
        || die "Detection reports are incomplete; missing: ${missing[*]}"

    local checklist_path="$range_dir/checklist.md"
    local prompt_path="$data_dir/evaluation/prompt.md"
    local skill_path="$data_dir/evaluation/SKILL.md"
    checklist_path="$(canonical_file "$checklist_path" "Checklist")"
    prompt_path="$(canonical_file "$prompt_path" "Evaluation prompt")"
    skill_path="$(canonical_file "$skill_path" "Evaluation Skill")"

    [[ ! -e "$output_dir" ]] || die "Output path already exists: $output_dir"
    mkdir -p "$output_dir"
    output_dir="$(canonical_dir "$output_dir" "Output directory")"

    render_template \
        "$prompt_path" \
        "$output_dir/CLAUDE.md" \
        "CHECKLIST_PATH" "$checklist_path" \
        "DETECTION_REPORTS_PATH" "$reports_dir" \
        "EVALUATION_SKILL_PATH" "$skill_path" \
        "OUTPUT_PATH" "$output_dir"

    info "Range:      $range"
    info "Checklist:  $checklist_path"
    info "Reports:    $reports_dir"
    info "Skill:      $skill_path"
    info "Prompt:     $prompt_path"
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
        "Please read CLAUDE.md in the current directory and follow its evaluation process, including the referenced evaluation Skill."
    )

    local rc=0
    (
        cd "$output_dir"
        "${command[@]}" > session-events.jsonl
    ) || rc=$?

    local missing_outputs=()
    [[ -f "$output_dir/evaluation-report.md" ]] || missing_outputs+=("evaluation-report.md")
    [[ -f "$output_dir/scores.json" ]] || missing_outputs+=("scores.json")
    if [[ ${#missing_outputs[@]} -gt 0 ]]; then
        printf 'WARN: Evaluation outputs are incomplete; missing: %s\n' "${missing_outputs[*]}" >&2
        [[ "$rc" -ne 0 ]] || rc=4
    fi

    info "Evaluation finished with exit code $rc."
    info "Workspace: $output_dir"
    return "$rc"
}

main "$@"
