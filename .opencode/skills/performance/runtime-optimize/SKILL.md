---
name: runtime-optimize
description: >
  Optimize browser rendering, animation performance, and network request efficiency.
  Use when the user mentions slow rendering, janky animation, network latency,
  or wants smoother UI performance. Triggers on: "smooth animation",
  "reduce latency", "optimize rendering", "60fps", "first contentful paint",
  or when analyzing runtime performance.
---

# Runtime Performance Optimizer

Optimize browser rendering, animations, and network performance.

## Process

### Step 1: Identify Rendering Issues

Common performance problems:

- **Layout thrashing**: Read-write-read-write pattern
- **Forced reflows**: Reading layout properties
- **Paintstorms**: Excessive repaints
- **Main thread blocking**: Heavy JS execution
- **Large JS bundles**: Parse/compile time

### Step 2: Rendering Optimization

- **CSS containment**: Contain: content/layout
- **will-change**: Promote to compositor
- **Transform for animations**: Use transform, opacity only
- **RequestAnimationFrame**: Sync with refresh rate
- **Virtual scrolling**: Render visible items only

### Step 3: Animation Optimization

- **Compositor-only properties**: transform, opacity
- **Avoid layout triggers**: No top/left changes
- **Debounce scroll handlers**: Throttle listeners
- **GPU acceleration**: Use transform3d()
- **Reduce paint areas**: Layer promotion

### Step 4: Network Optimization

- **Code splitting**: Load on demand
- **Preload critical**:rel="preload"
- **HTTP/2 multiplexing**: Concurrent requests
- **Resource hints**: prefetch, preconnect
- **Payload optimization**: Compress, minify
- **Image optimization**: Lazy load, responsive images

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| runtime-optimize | build-optimize | Bundle size directly affects runtime metrics |
| runtime-optimize | db-optimize | Slow queries degrade runtime UX |

## Common Issues

| Issue | Solution |
|-------|----------|
| janky scroll | Debounce, requestAnimationFrame |
| slow paint | Promote to GPU |
| layout thrash | Batch reads, separate writes |
| slow LCP | Preload hero image |
| large bundle | Code split |
| slow TTI | Reduce JS |