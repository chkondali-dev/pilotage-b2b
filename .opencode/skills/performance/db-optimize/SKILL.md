---
name: db-optimize
description: >
  Optimize database queries, caching strategies, and data layer performance.
  Use when the user mentions slow query, N+1 problem, caching, database performance,
  query optimization, or Redis. Triggers on: "optimize query", "fix N+1",
  "cache results", "slow database", or when analyzing DB performance.
---

# Database & IO Performance Optimizer

Optimize database queries, caching, and data layer performance.

## Process

### Step 1: Identify Query Problems

Common DB performance issues:

- **N+1 queries**: Loading related records one-by-one
- **Missing indexes**: Full table scans
- **Over-fetching**: Selecting more than needed
- **Unoptimized joins**: Complex join order
- **Repeated queries**: Same query multiple times

### Step 2: Query Optimization

- **Add indexes**: For WHERE, JOIN, ORDER BY columns
- **EXPLAIN analysis**: Review query plan
- **Select only needed columns**: Avoid SELECT *
- **Batch queries**: Combine multiple queries
- **Pagination**: Cursor-based vs offset

### Step 3: Caching Strategy

- **Query caching**: Cache frequent queries
- **Result caching**: Redis/Memcached for hot data
- **Cache invalidation**: TTL or event-based
- **Write-through**: Update cache on write
- **Cache warming**: Pre-populate on startup

### Step 4: Connection Management

- **Connection pooling**: Reuse connections
- **Query batching**: Execute multiple in one round-trip
- **Prepared statements**: Parse once, reuse
- **Timeout configuration**: Proper timeouts

## Common Patterns

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| db-optimize | code-review-workflow | DB performance review catches N+1 and slow queries |

### N+1 Solutions

| Anti-pattern | Better |
|------------|-------|
| Loop + query | Eager loading, batch query |
| Lazy loading | Preload in query |
| Separate find | Include/join |

### Caching Patterns

| Pattern | Use Case |
|---------|---------|
| Cache-aside | Read-heavy, write-infrequent |
| Write-through | Consistent reads needed |
| Redis get + set | TTL-based expiry |
| In-memory | Single instance |