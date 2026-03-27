---
created: 2026-03-27T06:00:00.000Z
title: "Fix MBPP code extraction — example usage before code fence"
area: general
files:
  - src/grade_results.py
---

## Problem

596 of 785 remaining MBPP crashes are NameErrors caused by the code extractor pulling in example usage text that appears before the code fence. Example:

```
Here's a simple Python function:
print(all_dicts_empty([{}, {}, {}]))    <-- runs before function is defined

```python
def all_dicts_empty(dict_list):         <-- actual function definition
    ...
```

The extracted code includes the `print(...)` line which executes before the function exists, causing NameError.

## Solution

1. Extract ONLY content inside ` ```python ` fences, not surrounding text
2. If multiple code blocks exist, concatenate only the ones containing function definitions
3. Strip any standalone expression/print statements that appear before the first `def`
4. Re-run `propt regrade` after fixing to recover ~596 runs
