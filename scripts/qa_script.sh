#!/usr/bin/env bash
# ==========================================================================
# Linguistic Tax QA Script
# Comprehensive pre-release checklist: env, pytest, CLI, data, config, API
# ==========================================================================
set -uo pipefail

# ---------------------------------------------------------------------------
# Global variables
# ---------------------------------------------------------------------------
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
INFO_COUNT=0
CHECK_NUM=0
LIVE=false
LOG_FILE=""
SECTION="all"
START_TIME=$(date +%s)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate project venv if present and not already active
if [[ -z "${VIRTUAL_ENV:-}" && -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Linguistic Tax QA Script -- unified pre-release checklist.

Options:
  --live            Enable live API tests (Section 6)
  --section NAME    Run only one section (env, pytest, cli, data, config, api, all)
  --log             Write results to timestamped log file
  -h, --help        Show this help message

Sections:
  env       Environment checks (Python version, packages, directories)
  pytest    Unit test suite
  cli       CLI smoke tests (--help for each module)
  data      Data pipeline validation (prompts.json, experiment_matrix.json)
  config    Configuration validation (ExperimentConfig, seed determinism)
  api       Live API connectivity tests (requires --live or --section api)

Examples:
  $(basename "$0")                    # Run all offline checks
  $(basename "$0") --live             # Run all checks including API
  $(basename "$0") --section env      # Run only environment checks
  $(basename "$0") --section cli --log  # Run CLI checks, log to file
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --live)
            LIVE=true
            shift
            ;;
        --section)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --section requires a value" >&2
                exit 1
            fi
            SECTION="$2"
            case "$SECTION" in
                env|pytest|cli|data|config|api|all) ;;
                *)
                    echo "ERROR: Invalid section '$SECTION'. Valid: env, pytest, cli, data, config, api, all" >&2
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        --log)
            LOG_FILE="qa_results_$(date +%Y%m%d_%H%M%S).log"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option '$1'" >&2
            usage
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
strip_ansi() {
    sed 's/\x1b\[[0-9;]*m//g'
}

log_line() {
    local line="$1"
    if [[ -n "$LOG_FILE" ]]; then
        echo "$line" | strip_ansi >> "$LOG_FILE"
    fi
}

run_check() {
    local description="$1"
    shift
    CHECK_NUM=$((CHECK_NUM + 1))
    local start_ms
    start_ms=$(date +%s%N 2>/dev/null || echo "0")

    local output
    output=$("$@" 2>&1)
    local exit_code=$?

    local end_ms
    end_ms=$(date +%s%N 2>/dev/null || echo "0")

    local elapsed_ms=0
    if [[ "$start_ms" != "0" && "$end_ms" != "0" ]]; then
        elapsed_ms=$(( (end_ms - start_ms) / 1000000 ))
    fi

    local status status_color
    if [[ $exit_code -eq 0 ]]; then
        status="PASS"
        status_color="${GREEN}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        status="FAIL"
        status_color="${RED}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    local line
    line=$(printf "| %3d | ${status_color}%-4s${NC} | %6dms | %s |" "$CHECK_NUM" "$status" "$elapsed_ms" "$description")
    echo -e "$line"
    log_line "$(printf "| %3d | %-4s | %6dms | %s |" "$CHECK_NUM" "$status" "$elapsed_ms" "$description")"

    if [[ $exit_code -ne 0 && -n "$output" ]]; then
        local detail="      -> $(echo "$output" | head -3 | tr '\n' ' ')"
        echo -e "  ${RED}${detail}${NC}"
        log_line "  $detail"
    fi
}

run_warn_check() {
    local description="$1"
    shift
    CHECK_NUM=$((CHECK_NUM + 1))
    local start_ms
    start_ms=$(date +%s%N 2>/dev/null || echo "0")

    local output
    output=$("$@" 2>&1)
    local exit_code=$?

    local end_ms
    end_ms=$(date +%s%N 2>/dev/null || echo "0")

    local elapsed_ms=0
    if [[ "$start_ms" != "0" && "$end_ms" != "0" ]]; then
        elapsed_ms=$(( (end_ms - start_ms) / 1000000 ))
    fi

    local status status_color
    if [[ $exit_code -eq 0 ]]; then
        status="PASS"
        status_color="${GREEN}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        status="WARN"
        status_color="${YELLOW}"
        WARN_COUNT=$((WARN_COUNT + 1))
    fi

    local line
    line=$(printf "| %3d | ${status_color}%-4s${NC} | %6dms | %s |" "$CHECK_NUM" "$status" "$elapsed_ms" "$description")
    echo -e "$line"
    log_line "$(printf "| %3d | %-4s | %6dms | %s |" "$CHECK_NUM" "$status" "$elapsed_ms" "$description")"

    if [[ $exit_code -ne 0 && -n "$output" ]]; then
        local detail="      -> $(echo "$output" | head -3 | tr '\n' ' ')"
        echo -e "  ${YELLOW}${detail}${NC}"
        log_line "  $detail"
    fi
}

run_info() {
    local description="$1"
    CHECK_NUM=$((CHECK_NUM + 1))
    INFO_COUNT=$((INFO_COUNT + 1))

    local line
    line=$(printf "| %3d | ${BLUE}%-4s${NC} | %6s   | %s |" "$CHECK_NUM" "INFO" "--" "$description")
    echo -e "$line"
    log_line "$(printf "| %3d | %-4s | %6s   | %s |" "$CHECK_NUM" "INFO" "--" "$description")"
}

print_header() {
    local title="$1"
    echo ""
    echo -e "${BOLD}============================================${NC}"
    echo -e "${BOLD}  $title${NC}"
    echo -e "${BOLD}============================================${NC}"
    echo ""
    log_line ""
    log_line "============================================"
    log_line "  $title"
    log_line "============================================"
    log_line ""
}

print_section() {
    local title="$1"
    echo ""
    echo -e "${BOLD}--- $title ---${NC}"
    echo ""
    log_line ""
    log_line "--- $title ---"
    log_line ""
}

print_summary() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local total=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT + INFO_COUNT))

    local verdict verdict_color
    if [[ $FAIL_COUNT -gt 0 ]]; then
        verdict="FAIL"
        verdict_color="${RED}"
    else
        verdict="PASS"
        verdict_color="${GREEN}"
    fi

    echo ""
    echo -e "${BOLD}============================================${NC}"
    echo -e "${BOLD}QA SUMMARY${NC}"
    echo -e "${BOLD}============================================${NC}"
    echo -e "PASS: ${GREEN}${PASS_COUNT}${NC} | FAIL: ${RED}${FAIL_COUNT}${NC} | WARN: ${YELLOW}${WARN_COUNT}${NC} | INFO: ${BLUE}${INFO_COUNT}${NC}"
    echo -e "Total checks: ${total}"
    echo -e "Duration: ${duration}s"
    echo -e "${BOLD}--------------------------------------------${NC}"
    echo -e "VERDICT: ${verdict_color}${BOLD}${verdict}${NC}"
    echo -e "${BOLD}============================================${NC}"

    log_line ""
    log_line "============================================"
    log_line "QA SUMMARY"
    log_line "============================================"
    log_line "PASS: ${PASS_COUNT} | FAIL: ${FAIL_COUNT} | WARN: ${WARN_COUNT} | INFO: ${INFO_COUNT}"
    log_line "Total checks: ${total}"
    log_line "Duration: ${duration}s"
    log_line "--------------------------------------------"
    log_line "VERDICT: ${verdict}"
    log_line "============================================"
}

# ---------------------------------------------------------------------------
# Section 1: Environment checks
# ---------------------------------------------------------------------------
check_env() {
    print_section "Section 1: Environment Checks"

    # Python version >= 3.11
    run_check "Python version >= 3.11" python3 -c "
import sys
v = sys.version_info
assert v >= (3, 11), f'Python {v.major}.{v.minor} < 3.11'
print(f'Python {v.major}.{v.minor}.{v.micro}')
"

    # pip available
    run_check "pip/venv available" python3 -m pip --version

    # Required packages
    local packages=(
        "anthropic"
        "google.genai"
        "openai"
        "statsmodels"
        "scipy"
        "pandas"
        "matplotlib"
        "seaborn"
        "pytest"
        "tiktoken"
        "tabulate"
    )
    for pkg in "${packages[@]}"; do
        run_check "Package importable: ${pkg}" python3 -c "import ${pkg}"
    done

    # pytest-cov
    run_warn_check "Package importable: pytest-cov" python3 -c "import pytest_cov"

    # Directories exist
    run_check "Directory exists: src/" test -d "$PROJECT_ROOT/src"
    run_check "Directory exists: tests/" test -d "$PROJECT_ROOT/tests"
    run_check "Directory exists: data/" test -d "$PROJECT_ROOT/data"
}

# ---------------------------------------------------------------------------
# Section 2: Unit tests
# ---------------------------------------------------------------------------
check_pytest() {
    print_section "Section 2: Unit Tests (pytest)"

    run_check "pytest tests/ passes" python3 -m pytest tests/ -x -q --tb=short

    # Report test count
    local test_count
    test_count=$(python3 -m pytest tests/ -q --co 2>/dev/null | tail -1 | grep -oP '\d+(?= test)' || echo "unknown")
    run_info "Test count: ${test_count}"
}

# ---------------------------------------------------------------------------
# Section 3: CLI smoke tests
# ---------------------------------------------------------------------------
check_cli() {
    print_section "Section 3: CLI Smoke Tests"

    local modules=(
        "src.noise_generator"
        "src.grade_results"
        "src.run_experiment"
        "src.analyze_results"
        "src.compute_derived"
        "src.pilot"
        "src.generate_figures"
    )
    for mod in "${modules[@]}"; do
        run_check "CLI: python -m ${mod} --help" python3 -m "${mod}" --help
    done

    # Functional smoke test: noise generator with a small input
    run_check "Noise generator functional test" python3 -c "
from src.noise_generator import inject_type_a_noise
result = inject_type_a_noise('Hello world test', error_rate=0.05, seed=42)
assert isinstance(result, str), 'Expected string output'
assert len(result) > 0, 'Expected non-empty output'
print(f'Output: {result}')
"
}

# ---------------------------------------------------------------------------
# Section 4: Data pipeline checks
# ---------------------------------------------------------------------------
check_data() {
    print_section "Section 4: Data Pipeline Checks"

    run_check "data/prompts.json exists" test -f "$PROJECT_ROOT/data/prompts.json"

    run_check "data/prompts.json has 200 entries" python3 -c "
import json
with open('data/prompts.json') as f:
    d = json.load(f)
assert len(d) == 200, f'Expected 200, got {len(d)}'
print(f'Entries: {len(d)}')
"

    run_check "data/experiment_matrix.json exists" test -f "$PROJECT_ROOT/data/experiment_matrix.json"

    run_check "data/experiment_matrix.json is valid JSON" python3 -c "
import json
with open('data/experiment_matrix.json') as f:
    d = json.load(f)
print(f'Valid JSON, {len(d)} items')
"

    # Report matrix size
    local matrix_size
    matrix_size=$(python3 -c "import json; d=json.load(open('data/experiment_matrix.json')); print(len(d))" 2>/dev/null || echo "unknown")
    run_info "Matrix size: ${matrix_size} items"
}

# ---------------------------------------------------------------------------
# Section 5: Config validation
# ---------------------------------------------------------------------------
check_config() {
    print_section "Section 5: Configuration Validation"

    run_check "ExperimentConfig instantiates" python3 -c "
from src.config import ExperimentConfig
c = ExperimentConfig()
print(f'Models: claude={c.claude_model}, gemini={c.gemini_model}, openai={c.openai_model}')
"

    run_check "Pinned model versions are non-empty" python3 -c "
from src.config import ExperimentConfig
c = ExperimentConfig()
for name in ['claude_model', 'gemini_model', 'openai_model']:
    val = getattr(c, name)
    assert isinstance(val, str) and len(val) > 0, f'{name} is empty or not string'
print('All model versions non-empty')
"

    run_check "Seed derivation is deterministic" python3 -c "
from src.config import derive_seed
s1 = derive_seed(42, 'test', 'type_a', '5')
s2 = derive_seed(42, 'test', 'type_a', '5')
assert s1 == s2, f'Seeds differ: {s1} != {s2}'
print(f'Deterministic seed: {s1}')
"
}

# ---------------------------------------------------------------------------
# Section 6: Live API tests (only with --live)
# ---------------------------------------------------------------------------
check_api() {
    print_section "Section 6: Live API Tests"

    if [[ "$LIVE" != true && "$SECTION" != "api" ]]; then
        run_info "Skipped (use --live to enable)"
        return
    fi

    # Check API keys
    run_warn_check "ANTHROPIC_API_KEY is set" test -n "${ANTHROPIC_API_KEY:-}"
    run_warn_check "GOOGLE_API_KEY is set" test -n "${GOOGLE_API_KEY:-}"
    run_warn_check "OPENAI_API_KEY is set" test -n "${OPENAI_API_KEY:-}"

    # Live API calls
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        run_check "Anthropic API connectivity" python3 -c "
from src.api_client import call_model
r = call_model('claude-sonnet-4-20250514', None, 'Say hello in one word', max_tokens=10)
print(f'Response: {r.response_text[:50]}')
"
    else
        run_info "Anthropic API test skipped (no key)"
    fi

    if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
        run_check "Google API connectivity" python3 -c "
from src.api_client import call_model
r = call_model('gemini-1.5-pro', None, 'Say hello in one word', max_tokens=10)
print(f'Response: {r.response_text[:50]}')
"
    else
        run_info "Google API test skipped (no key)"
    fi

    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        run_check "OpenAI API connectivity" python3 -c "
from src.api_client import call_model
r = call_model('gpt-4o-2024-11-20', None, 'Say hello in one word', max_tokens=10)
print(f'Response: {r.response_text[:50]}')
"
    else
        run_info "OpenAI API test skipped (no key)"
    fi
}

# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
cd "$PROJECT_ROOT"

print_header "Linguistic Tax QA Script"

if [[ -n "$LOG_FILE" ]]; then
    echo "Logging to: $LOG_FILE"
    echo "Linguistic Tax QA Script -- $(date)" > "$LOG_FILE"
fi

if [[ "$SECTION" == "all" || "$SECTION" == "env" ]]; then check_env; fi
if [[ "$SECTION" == "all" || "$SECTION" == "pytest" ]]; then check_pytest; fi
if [[ "$SECTION" == "all" || "$SECTION" == "cli" ]]; then check_cli; fi
if [[ "$SECTION" == "all" || "$SECTION" == "data" ]]; then check_data; fi
if [[ "$SECTION" == "all" || "$SECTION" == "config" ]]; then check_config; fi
if [[ "$SECTION" == "api" || ( "$SECTION" == "all" && "$LIVE" == true ) ]]; then check_api; fi

print_summary

exit $([ "$FAIL_COUNT" -gt 0 ] && echo 1 || echo 0)
