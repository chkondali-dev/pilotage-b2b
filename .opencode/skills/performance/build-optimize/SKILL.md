---
name: build-optimize
description: >
  Optimize build times, bundle size, and asset processing.
  Use when the user mentions build time, slow build, bundle size, large bundle,
  chunk size, tree shaking, or wants faster builds. Triggers on: "optimize build",
  "reduce bundle size", "faster build", "tree shaking", "code splitting",
  or when analyzing build configuration.
---

# Build Optimizer

Optimize build times, bundle sizes, and asset processing.

## Process

### Step 1: Analyze Build Output

Examine current build:

- Bundle size breakdown (webpack analyzer, rollup-plugin-visualizer)
- Build time per stage
- Tree shaking effectiveness
- Code splitting configuration
- Duplicate code detection

### Step 2: Optimize Bundle

- **Code splitting**: Dynamic imports for lazy-loaded chunks
- **Tree shaking**: Remove unused exports, sideEffects: false
- **Dead code elimination**: Remove development-only code
- **Module concatenation**: Enable scope hoisting
- **Chunk optimization**: CommonsChunkPlugin or equivalent

### Step 3: Optimize Assets

- **Image compression**: WebP, AVIF formats
- **SVG optimization**: SVGO, remove metadata
- **Font subsetting**: Only include used glyphs
- **Compression**: Gzip, Brotli pre-compression

### Step 4: Optimize Build Speed

- **Caching**: Persistent caching, cache-loader
- **Parallelization**: thread-loader, parallel-webpack
- **Lazy compilation**: @babel/plugin-transform-runtime
- **Module federation**: Shared dependencies
- **Watch optimization**: Ignore node_modules

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| build-optimize | runtime-optimize | Bundle size affects runtime performance |
| build-optimize | code-review-workflow | Performance review catches build issues |

## Common Issues

| Issue | Solution |
|-------|----------|
| Large vendor chunk | Split to separate chunk |
| Many small chunks | Increase chunk size limit |
| Duplicate code | Dedupe dependencies |
| Slow rebuilds | Enable caching |
| Large images | Convert to WebP |
| Many requests | HTTP/2 push, preconnect |