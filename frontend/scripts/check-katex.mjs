// Compile every collected LaTeX fragment with the exact KaTeX the app uses.
// Usage: node scripts/check-katex.mjs [/tmp/educator-latex.json]
import { readFileSync } from 'node:fs'
import katex from 'katex'

const path = process.argv[2] ?? '/tmp/educator-latex.json'
const fragments = JSON.parse(readFileSync(path, 'utf8'))

const failures = []
for (const f of fragments) {
  try {
    katex.renderToString(f.math, { displayMode: f.display, throwOnError: true })
  } catch (e) {
    failures.push({ ...f, error: String(e.message).split('\n')[0] })
  }
}

const bySource = new Map()
for (const f of failures) {
  const key = f.source.replace(/ s\d+$/, '') // collapse per-seed duplicates
  if (!bySource.has(key)) bySource.set(key, f)
}

console.log(`checked ${fragments.length} fragments: ${failures.length} failures (${bySource.size} distinct sources)`)
for (const f of bySource.values()) {
  console.log(`\nFAIL ${f.source}`)
  console.log(`  math:  ${f.math.slice(0, 120)}`)
  console.log(`  error: ${f.error.slice(0, 160)}`)
}
process.exit(bySource.size === 0 ? 0 : 1)
