'use client'

import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Markdown renderer for AI-generated content (tech-lead answers, etc.).
 *
 * - Safe by default: react-markdown escapes raw HTML (`skipHtml`), so the
 *   model's output can never inject markup.
 * - GFM enabled: tables, strikethrough, task lists, autolinks.
 * - Styled to match the app's design system (dark code blocks, etc.).
 */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="text-sm text-foreground/90 leading-relaxed space-y-3">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          h1: (props) => (
            <h1
              className="text-base font-bold text-foreground m-0 pt-1"
              {...props}
            />
          ),
          h2: (props) => (
            <h2
              className="text-[15px] font-bold text-foreground m-0 pt-1"
              {...props}
            />
          ),
          h3: (props) => (
            <h3
              className="text-sm font-bold text-foreground m-0 pt-1"
              {...props}
            />
          ),
          p: (props) => <p className="m-0" {...props} />,
          ul: (props) => (
            <ul className="list-disc pl-5 m-0 space-y-1" {...props} />
          ),
          ol: (props) => (
            <ol className="list-decimal pl-5 m-0 space-y-1" {...props} />
          ),
          li: (props) => <li className="m-0" {...props} />,
          blockquote: (props) => (
            <blockquote
              className="border-l-2 border-primary/40 pl-3 text-muted italic m-0"
              {...props}
            />
          ),
          a: (props) => (
            <a
              className="text-primary underline underline-offset-2 hover:opacity-80"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),
          code: (props) => {
            const { inline, children, ...rest } = props as {
              inline?: boolean
              children?: React.ReactNode
            }
            if (inline) {
              return (
                <code
                  className="rounded bg-[#1e1e1e] text-[#e6edf3] px-1.5 py-0.5 font-mono text-[11px]"
                  {...rest}
                >
                  {children}
                </code>
              )
            }
            return (
              <code
                className="font-mono text-[11px] text-[#e6edf3]"
                {...rest}
              >
                {children}
              </code>
            )
          },
          pre: (props) => (
            <pre
              className="bg-[#1e1e1e] border border-[#3c3c3c] rounded-lg p-3 text-[11px] font-mono overflow-x-auto max-h-[400px] overflow-y-auto m-0"
              {...props}
            />
          ),
          hr: () => <hr className="border-border m-0" />,
          table: (props) => (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table
                className="w-full text-xs border-collapse divide-y divide-border"
                {...props}
              />
            </div>
          ),
          th: (props) => (
            <th
              className="px-3 py-2 text-left font-semibold text-foreground bg-surface-secondary"
              {...props}
            />
          ),
          td: (props) => (
            <td className="px-3 py-2 border-t border-border" {...props} />
          ),
          del: (props) => <del className="line-through opacity-70" {...props} />,
          input: (props) => (
            <input
              className="mr-1.5 accent-[--primary]"
              disabled={!props.checked}
              {...props}
            />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
