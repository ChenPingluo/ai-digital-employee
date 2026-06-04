/**
 * 轻量级 Markdown 渲染工具
 *
 * 不依赖第三方库，支持常见的 Markdown 语法：
 * - 标题
 * - 粗体 / 斜体 / 删除线
 * - 行内代码 / 代码块
 * - 引用
 * - 有序 / 无序列表
 * - 表格
 * - 链接
 * - 分割线
 * - 段落与换行
 */

const CODE_BLOCK_TOKEN_PREFIX = '@@CODEBLOCK'
const INLINE_CODE_TOKEN_PREFIX = '@@INLINECODE'

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, '&#96;')
}

function sanitizeUrl(url) {
  const trimmed = String(url || '').trim()
  if (/^(https?:|mailto:|\/|#)/i.test(trimmed)) {
    return escapeAttribute(trimmed)
  }
  return '#'
}

function splitTableRow(row) {
  return row
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function isTableSeparator(line) {
  return /^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line)
}

function isHorizontalRule(line) {
  return /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)
}

function isBlockquote(line) {
  return /^\s*>\s?/.test(line)
}

function isListItem(line) {
  return /^(\s*)(?:[-*+]|\d+\.)\s+/.test(line)
}

function isHeading(line) {
  return /^(#{1,6})\s+(.+)$/.test(line.trim())
}

function isCodeBlockToken(line) {
  return line.trim().startsWith(CODE_BLOCK_TOKEN_PREFIX)
}

function isSpecialBlockStart(line, nextLine = '') {
  if (!line.trim()) return true
  if (isCodeBlockToken(line)) return true
  if (isHeading(line)) return true
  if (isHorizontalRule(line)) return true
  if (isBlockquote(line)) return true
  if (isListItem(line)) return true
  if (line.includes('|') && isTableSeparator(nextLine)) return true
  return false
}

function renderInline(text, inlineCodeMap) {
  let html = escapeHtml(text)

  html = html.replace(/`([^`]+)`/g, (_, code) => {
    const token = `${INLINE_CODE_TOKEN_PREFIX}${inlineCodeMap.length}@@`
    inlineCodeMap.push(
      `<code class="inline-code">${escapeHtml(code)}</code>`
    )
    return token
  })

  html = html.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    (_, alt, url) => `<img src="${sanitizeUrl(url)}" alt="${escapeAttribute(alt)}" />`
  )

  html = html.replace(
    /\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]+)")?\)/g,
    (_, label, url, title) => {
      const titleAttr = title ? ` title="${escapeAttribute(title)}"` : ''
      return `<a href="${sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer"${titleAttr}>${label}</a>`
    }
  )

  html = html.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__([\s\S]+?)__/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>')
  html = html.replace(/~~([\s\S]+?)~~/g, '<del>$1</del>')

  inlineCodeMap.forEach((codeHtml, index) => {
    html = html.replace(`${INLINE_CODE_TOKEN_PREFIX}${index}@@`, codeHtml)
  })

  return html
}

function renderTable(lines, startIndex) {
  const headerLine = lines[startIndex]
  const rows = []
  let index = startIndex + 2

  while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
    rows.push(lines[index])
    index += 1
  }

  const inlineCodeMap = []
  const headers = splitTableRow(headerLine)
    .map((cell) => `<th>${renderInline(cell, inlineCodeMap)}</th>`)
    .join('')

  const body = rows
    .map((row) => {
      const cells = splitTableRow(row)
        .map((cell) => `<td>${renderInline(cell, inlineCodeMap)}</td>`)
        .join('')
      return `<tr>${cells}</tr>`
    })
    .join('')

  return {
    html: `<div class="markdown-table-wrapper"><table><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table></div>`,
    nextIndex: index
  }
}

function renderList(lines, startIndex) {
  const ordered = /^\s*\d+\.\s+/.test(lines[startIndex])
  const tag = ordered ? 'ol' : 'ul'
  const items = []
  let index = startIndex

  while (index < lines.length && isListItem(lines[index])) {
    const itemText = lines[index].replace(/^(\s*)(?:[-*+]|\d+\.)\s+/, '')
    const inlineCodeMap = []
    items.push(`<li>${renderInline(itemText, inlineCodeMap)}</li>`)
    index += 1
  }

  return {
    html: `<${tag}>${items.join('')}</${tag}>`,
    nextIndex: index
  }
}

function renderBlockquote(lines, startIndex) {
  const quoteLines = []
  let index = startIndex

  while (index < lines.length && isBlockquote(lines[index])) {
    quoteLines.push(lines[index].replace(/^\s*>\s?/, ''))
    index += 1
  }

  return {
    html: `<blockquote>${renderMarkdown(quoteLines.join('\n'))}</blockquote>`,
    nextIndex: index
  }
}

function renderParagraph(lines, startIndex) {
  const paragraphLines = []
  let index = startIndex

  while (
    index < lines.length &&
    lines[index].trim() &&
    !isSpecialBlockStart(lines[index], lines[index + 1] || '')
  ) {
    paragraphLines.push(lines[index].trim())
    index += 1
  }

  const inlineCodeMap = []
  const html = `<p>${renderInline(paragraphLines.join('\n'), inlineCodeMap).replace(/\n/g, '<br />')}</p>`

  return {
    html,
    nextIndex: index
  }
}

export function renderMarkdown(content) {
  if (!content) return ''

  const codeBlockMap = []
  const normalized = String(content)
    .replace(/\r\n/g, '\n')
    .replace(/```([\w-]*)\n?([\s\S]*?)```/g, (_, language, code) => {
      const token = `${CODE_BLOCK_TOKEN_PREFIX}${codeBlockMap.length}@@`
      const languageLabel = language ? `<div class="code-block-language">${escapeHtml(language)}</div>` : ''
      const languageClass = language ? ` language-${escapeAttribute(language)}` : ''
      const html = [
        '<pre class="code-block">',
        languageLabel,
        `<code class="${languageClass.trim()}">${escapeHtml(code).replace(/\n$/, '')}</code>`,
        '</pre>'
      ].join('')

      codeBlockMap.push({ token, html })
      return `\n${token}\n`
    })

  const lines = normalized.split('\n')
  const blocks = []

  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    const nextLine = lines[index + 1] || ''

    if (!line.trim()) {
      index += 1
      continue
    }

    if (isCodeBlockToken(line)) {
      const codeBlock = codeBlockMap.find((item) => item.token === line.trim())
      if (codeBlock) {
        blocks.push(codeBlock.html)
      }
      index += 1
      continue
    }

    if (isHeading(line)) {
      const [, hashes, title] = line.trim().match(/^(#{1,6})\s+(.+)$/)
      const level = hashes.length
      const inlineCodeMap = []
      blocks.push(`<h${level}>${renderInline(title, inlineCodeMap)}</h${level}>`)
      index += 1
      continue
    }

    if (isHorizontalRule(line)) {
      blocks.push('<hr />')
      index += 1
      continue
    }

    if (line.includes('|') && isTableSeparator(nextLine)) {
      const rendered = renderTable(lines, index)
      blocks.push(rendered.html)
      index = rendered.nextIndex
      continue
    }

    if (isBlockquote(line)) {
      const rendered = renderBlockquote(lines, index)
      blocks.push(rendered.html)
      index = rendered.nextIndex
      continue
    }

    if (isListItem(line)) {
      const rendered = renderList(lines, index)
      blocks.push(rendered.html)
      index = rendered.nextIndex
      continue
    }

    const rendered = renderParagraph(lines, index)
    blocks.push(rendered.html)
    index = rendered.nextIndex
  }

  return blocks.join('')
}

export default renderMarkdown
