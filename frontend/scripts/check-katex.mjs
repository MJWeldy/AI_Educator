// Validate every displayable markdown document through the app's actual
// pipeline: the same delimiter normalization, the same remark-math parser,
// the same KaTeX. Flags two failure classes:
//   1. math nodes that KaTeX cannot compile
//   2. LaTeX-looking commands sitting OUTSIDE math (missing delimiters)
// Usage: node scripts/check-katex.mjs [/tmp/educator-latex.json]
import { readFileSync } from 'node:fs'
import katex from 'katex'
import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import { visit } from 'unist-util-visit'

// Keep in sync with src/components/Markdown.tsx
function normalizeMath(md) {
  return md
    .replace(/(?<!\\)\\\[([\s\S]*?)(?<!\\)\\\]/g, (_, body) => `\n$$\n${body.replace(/\\+\s*$/, '')}\n$$\n`)
    .replace(/(?<!\\)\\\(([\s\S]*?)(?<!\\)\\\)/g, (_, body) => `$${body.replace(/\\+\s*$/, '')}$`)
}

const RAW_LATEX =
  /\\(?:frac|dfrac|tfrac|sqrt|text\{|mathbf|boldsymbol|begin\{|end\{|ell\b|Lambda|lambda|phi|Phi|varphi|pi\b|sigma|mu\b|times|cdot|exp\b|sum\b|prod\b|int\b|alpha|beta|gamma|delta|theta|rho\b|mid\b|approx|leq?\b|geq?\b|neq\b|infty|partial|nabla|hat\{|tilde\{|bar\{|vec\{|operatorname)|\\\(|\\\[/

const path = process.argv[2] ?? '/tmp/educator-latex.json'
const docs = JSON.parse(readFileSync(path, 'utf8'))
const processor = unified().use(remarkParse).use(remarkGfm).use(remarkMath)

const failures = []
for (const doc of docs) {
  const tree = processor.parse(normalizeMath(doc.md))
  visit(tree, ['math', 'inlineMath'], (node) => {
    try {
      katex.renderToString(node.value, {
        displayMode: node.type === 'math',
        throwOnError: true,
      })
    } catch (e) {
      failures.push({
        source: doc.source,
        kind: 'katex',
        math: node.value,
        error: String(e.message).split('\n')[0],
      })
    }
  })
  visit(tree, 'text', (node) => {
    if (RAW_LATEX.test(node.value)) {
      failures.push({
        source: doc.source,
        kind: 'raw-latex-outside-math',
        math: node.value,
        error: 'LaTeX commands outside $…$ delimiters (missing/unbalanced math markers)',
      })
    }
  })
}

const bySource = new Map()
for (const f of failures) {
  const key = f.source.replace(/ s\d+$/, '') + '|' + f.kind
  if (!bySource.has(key)) bySource.set(key, f)
}

console.log(
  `checked ${docs.length} documents: ${failures.length} findings (${bySource.size} distinct source×kind)`,
)
for (const f of bySource.values()) {
  console.log(`\nFAIL [${f.kind}] ${f.source}`)
  console.log(`  text:  ${f.math.slice(0, 140).replace(/\n/g, ' ⏎ ')}`)
  console.log(`  error: ${f.error.slice(0, 160)}`)
}
process.exit(bySource.size === 0 ? 0 : 1)
