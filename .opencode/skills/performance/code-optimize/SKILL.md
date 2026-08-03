---
name: code-optimize
description: >
  Diagnose and fix code performance issues across algorithms, data structures, and computational complexity.
  Use when the user mentions slow, laggy, inefficient, performance, optimization, bottleneck,
  or wants faster code execution. Triggers on: "optimize this code", "make this faster",
  "performance issue", "slow function", "bottleneck", "O(n) complexity",
  "algorithm efficiency", or when analyzing code for performance improvements.
---

# Code Performance Optimizer

Diagnose and fix code performance issues across algorithms, data structures, and computational complexity.

## Process

### Step 1: Identify Performance Problems

Analyze the codebase for common performance anti-patterns:

- **Inefficient loops**: Nested loops, repeated computations, unnecessary iterations
- **Data structure issues**: Using wrong collections (array search vs map lookup)
- **Complexity issues**: O(n²) or worse algorithms that could be O(n) or O(log n)
- **Memory issues**: Creating objects in loops, not releasing references
- **Synchronous blocking**: Long-running operations blocking execution

### Step 2: Measure and Profile

Use profiling tools to identify actual bottlenecks:

- **Node.js**: `node --prof`, `0x`, `clinicjs`
- **Python**: `cProfile`, `line_profiler`, `memory_profiler`
- **Browser**: Chrome DevTools Performance panel
- **Database**: EXPLAIN queries, query plans

### Step 3: Apply Optimizations

Prioritize by impact:

1. **Algorithm improvements** (highest impact): Better data structures, caching
2. **Reduce allocations**: Reuse objects, object pools
3. **Lazy evaluation**: Defer expensive operations
4. **Batch operations**: Process in chunks vs one-by-one
5. **Memoization**: Cache repeated calculations

### Step 4: Verify Improvements

Run benchmarks before and after to confirm improvements.

## Common Patterns

### Array Operations

| Anti-pattern | Better |
|-------------|-------|
| `array.find()` in loop | Build Map/Set lookup first |
| `filter().map()` | Single reduce or loop |
| `push` in tight loop | Pre-allocate + index |
| Nested loops | Use Set or Map for O(1) lookup |

### Object Operations

| Anti-pattern | Better |
|-------------|-------|
| Property access chains | Destructure upfront |
| Dynamic keys in hot path | Static property access |
| Creating objects in loops | Reuse or pool |

### Async Operations

| Anti-pattern | Better |
|------------|-------|
| Sequential awaits | Promise.all() |
| No timeout | Add timeout handling |
| Fire-and-forget | Proper await/error handling |