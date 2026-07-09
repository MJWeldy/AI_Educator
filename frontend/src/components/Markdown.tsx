import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

/** Sanitize the contents of `$…$` / `$$…$$` math spans so KaTeX doesn't choke on
 * things LLMs routinely emit but KaTeX rejects:
 *   - `\$` (literal dollar) → `\dollar` macro: inside inline `$…$`, math content
 *     is literal, so the `$` in `\$` closes the span early. A macro with no `$`
 *     char avoids that; display `$$` is unaffected but rewritten for consistency.
 *   - bare `#` / `%` → `\#` / `\%`: unescaped they mean macro-param / comment and
 *     abort the parse (`\text{# patches}`, `\text{(27% of cells)}`).
 * Escaped sequences (`\#`, `\%`, `\frac`, …) and code spans are passed through
 * untouched, and dollars in prose stay `\$` (rendering a literal `$`). */
function sanitizeMath(md: string): string {
  let out = ''
  let inInline = false
  let inDisplay = false
  let inCode = false
  for (let i = 0; i < md.length; ) {
    const c = md[i]
    if (c === '`' && !inInline && !inDisplay) {
      inCode = !inCode
      out += c
      i++
      continue
    }
    if (inCode) {
      out += c
      i++
      continue
    }
    if (c === '\\') {
      const next = md[i + 1] ?? ''
      if (next === '$' && (inInline || inDisplay)) out += '\\dollar'
      else out += c + next
      i += next ? 2 : 1
      continue
    }
    if (c === '$') {
      if (md[i + 1] === '$') {
        inDisplay = !inDisplay
        out += '$$'
        i += 2
      } else {
        inInline = !inInline
        out += '$'
        i++
      }
      continue
    }
    if ((inInline || inDisplay) && (c === '#' || c === '%')) {
      out += '\\' + c
      i++
      continue
    }
    out += c
    i++
  }
  return out
}

/** LLMs often emit \( \) / \[ \] delimiters; remark-math wants $ / $$.
 * Trailing backslashes are stripped from the body: a lone `\` before the new
 * `$` delimiter would escape it in markdown and swallow the following prose. */
function normalizeMath(md: string): string {
  const withDollars = md
    // Display fences must sit on their own lines for remark-math.
    .replace(/(?<!\\)\\\[([\s\S]*?)(?<!\\)\\\]/g, (_, body) => `\n$$\n${body.replace(/\\+\s*$/, '')}\n$$\n`)
    .replace(/(?<!\\)\\\(([\s\S]*?)(?<!\\)\\\)/g, (_, body) => `$${body.replace(/\\+\s*$/, '')}$`)
  return sanitizeMath(withDollars)
}

// Stats operators KaTeX lacks; rendered like \operatorname{…}. `\dollar` backs
// the escaped-dollar rewrite in sanitizeMath.
const katexOptions = {
  macros: {
    '\\dollar': '\\$',
    '\\logit': '\\operatorname{logit}',
    '\\expit': '\\operatorname{expit}',
    '\\Var': '\\operatorname{Var}',
    '\\Cov': '\\operatorname{Cov}',
    '\\Corr': '\\operatorname{Corr}',
    '\\SE': '\\operatorname{SE}',
  },
}

export default function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath, remarkGfm]}
      rehypePlugins={[[rehypeKatex, katexOptions]]}
    >
      {normalizeMath(children)}
    </ReactMarkdown>
  )
}
