---
phase: quick
plan: 260327-qun
type: execute
wave: 1
depends_on: []
files_modified:
  - src/execution_summary.py
  - src/cli.py
  - tests/test_execution_summary.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "propt report shows per-benchmark pass rate, cost, and timing"
    - "propt report --benchmark shows benchmark x noise cross-tabulation"
    - "propt report shows per-benchmark baselines (clean + raw)"
  artifacts:
    - path: "src/execution_summary.py"
      provides: "format_benchmark_breakdown and format_benchmark_noise_crosstab functions"
    - path: "src/cli.py"
      provides: "--benchmark flag on report subcommand"
  key_links:
    - from: "src/cli.py"
      to: "src/execution_summary.py"
      via: "handle_report calls benchmark breakdown formatters"
      pattern: "format_benchmark_breakdown|format_benchmark_noise"
---

<objective>
Add benchmark-level breakdown to `propt report` so the user can see how HumanEval, MBPP, and GSM8K perform individually rather than only seeing an aggregate pass rate.

Purpose: The pilot shows a flat ~59.6% pass rate, but one benchmark may be pulling the average down. Per-benchmark visibility is essential for diagnosing this.
Output: Enhanced report with per-benchmark stats always shown, plus a --benchmark flag for detailed cross-tabulation.
</objective>

<execution_context>
@/home/steve/linguistic-tax/.claude/get-shit-done/workflows/execute-plan.md
@/home/steve/linguistic-tax/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/execution_summary.py
@src/cli.py
@tests/test_execution_summary.py
@src/db.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add benchmark breakdown and cross-tabulation to format_post_run_report</name>
  <files>src/execution_summary.py, tests/test_execution_summary.py</files>
  <behavior>
    - Test 1: format_post_run_report with benchmark=False includes a "Per-Benchmark:" section showing pass rate, cost, and avg timing per benchmark (humaneval, mbpp, gsm8k)
    - Test 2: format_post_run_report with benchmark=True includes a "Benchmark x Noise:" cross-tabulation table showing pass rate for each benchmark under each noise type
    - Test 3: format_post_run_report with benchmark=True includes a "Benchmark Baselines:" section showing pass rate for clean+raw condition per benchmark
    - Test 4: format_post_run_report with no completed runs returns "No runs found" (existing behavior preserved)
  </behavior>
  <action>
    1. Add `benchmark: bool = False` parameter to `format_post_run_report(conn, benchmark=False)`.

    2. Always add a "Per-Benchmark:" section after the existing "Noise Conditions:" section. Query:
       ```sql
       SELECT benchmark, COUNT(*) as calls,
              SUM(CASE WHEN pass_fail=1 THEN 1 ELSE 0 END) as passed,
              COALESCE(SUM(total_cost_usd), 0) as cost,
              AVG(ttlt_ms) as avg_ttlt
       FROM experiment_runs WHERE status='completed'
       GROUP BY benchmark ORDER BY benchmark
       ```
       Format as tabulate table with columns: Benchmark, API Calls, Pass Rate, Cost, Avg TTLT.

    3. When `benchmark=True`, add two additional sections:

       a. "Benchmark x Noise:" cross-tabulation. Query all distinct (benchmark, noise_type) pairs with pass rates. Format as a pivot table with benchmarks as rows and noise types as columns, cells showing pass rate percentages.

       b. "Benchmark Baselines (clean + raw):" Query pass rates where noise_type='clean' AND intervention='raw', grouped by benchmark. Show each benchmark's natural pass rate.

    4. Write tests using an in-memory SQLite database (use init_database from src.db) with inserted test rows covering multiple benchmarks and noise types. Import format_post_run_report in the test and verify output contains expected section headers and values.

    5. Update the import in tests/test_execution_summary.py to include format_post_run_report.
  </action>
  <verify>
    <automated>cd /home/steve/linguistic-tax && python -m pytest tests/test_execution_summary.py -x -v -k "benchmark" 2>&1 | tail -30</automated>
  </verify>
  <done>format_post_run_report always shows per-benchmark breakdown; benchmark=True adds cross-tabulation and baselines. All new tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Wire --benchmark flag to CLI report subcommand</name>
  <files>src/cli.py</files>
  <action>
    1. In build_cli(), add `--benchmark` flag to the report_parser:
       ```python
       report_parser.add_argument(
           "--benchmark", action="store_true",
           help="Show per-benchmark cross-tabulation with noise types and baselines"
       )
       ```

    2. In handle_report(), pass `args.benchmark` to format_post_run_report:
       ```python
       print(format_post_run_report(conn, benchmark=args.benchmark))
       ```

    3. Update the import if needed (format_post_run_report signature changed but import stays the same).
  </action>
  <verify>
    <automated>cd /home/steve/linguistic-tax && python -m propt report --help 2>&1 | grep -q "benchmark" && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>propt report --benchmark flag exists and is passed through to format_post_run_report.</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/test_execution_summary.py -x -v` passes with no failures
- `python -m propt report --help` shows --benchmark flag
- Existing tests in test_execution_summary.py still pass
</verification>

<success_criteria>
- propt report always shows per-benchmark pass rate, cost, and timing
- propt report --benchmark additionally shows benchmark x noise cross-tabulation and clean+raw baselines
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260327-qun-add-benchmark-breakdown-to-report/260327-qun-SUMMARY.md`
</output>
