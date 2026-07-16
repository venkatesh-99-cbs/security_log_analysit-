import React, { useState } from 'react';
import { ChatMessage } from '../types';
import { Bot, User, Copy, Check } from 'lucide-react';
import { parseServerDate } from '../utils/formatDate';

interface ChatBubbleProps {
  message: ChatMessage;
}

const formatMessageTime = (timestamp?: string) => {
  if (!timestamp) return '';
  const date = parseServerDate(timestamp);
  return !date ? '' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const CodeBlock: React.FC<{ code: string; language?: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-4 border border-slate-800 rounded-lg overflow-hidden shadow-lg select-text">
      <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-400 font-mono select-none">
        <span>{language || 'code'}</span>
        <button
          onClick={handleCopy}
          type="button"
          className="flex items-center gap-1 hover:text-slate-200 transition-colors"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre className="bg-slate-950 p-4 overflow-x-auto text-xs font-mono text-sky-300">
        <code>{code}</code>
      </pre>
    </div>
  );
};

// Advanced markdown formatter with table support
const formatMarkdown = (text: string) => {
  if (!text) return null;

  const lines = text.split('\n');
  const result: React.ReactNode[] = [];
  let i = 0;

  // Helper for parsing rows while preserving empty cells
  const parseRow = (rowStr: string) => {
    let cells = rowStr.split('|').map(cell => cell.trim());
    if (rowStr.startsWith('|')) cells.shift();
    if (rowStr.endsWith('|')) cells.pop();
    return cells;
  };

  // Robust pattern to identify list markers (bullet, dash, numbered list like "10.", letter list like "a.")
  const listMarkerRegex = /^(?:(?:\d+\.)|[*•\-]|(?:\w\.))\s/;

  while (i < lines.length) {
    const line = lines[i];

    // Check for markdown table
    if (i + 1 < lines.length && lines[i + 1].includes('|') && lines[i + 1].includes('-')) {
      const tableStart = i;
      let tableEnd = i + 1;
      
      // Find all table rows
      while (tableEnd < lines.length && lines[tableEnd].includes('|')) {
        tableEnd++;
      }

      // Parse table
      const tableLines = lines.slice(tableStart, tableEnd);
      const headerRow = parseRow(tableLines[0]);
      const rows = tableLines.slice(2).map(row => parseRow(row));

      result.push(
        <div key={`table-${i}`} className="my-3 overflow-x-auto">
          <table className="border-collapse border border-slate-600 text-xs">
            <thead>
              <tr className="bg-slate-800">
                {headerRow.map((header, idx) => (
                  <th key={idx} className="border border-slate-600 px-3 py-2 font-bold text-sky-400 text-left">
                    {parseInline(header)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIdx) => (
                <tr key={rowIdx} className="hover:bg-slate-900/50">
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx} className="border border-slate-600 px-3 py-2 text-slate-300">
                      {parseInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

      i = tableEnd;
      continue;
    }

    // Check for headers
    if (line.startsWith('# ')) {
      result.push(<h1 key={`h1-${i}`} className="text-2xl font-bold text-slate-100 mt-4 mb-3">{parseInline(line.substring(2))}</h1>);
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      result.push(<h2 key={`h2-${i}`} className="text-xl font-bold text-slate-100 mt-3 mb-2">{parseInline(line.substring(3))}</h2>);
      i++;
      continue;
    }
    if (line.startsWith('### ')) {
      result.push(<h3 key={`h3-${i}`} className="text-lg font-bold text-slate-200 mt-2 mb-1">{parseInline(line.substring(4))}</h3>);
      i++;
      continue;
    }

    // Check for code block
    if (line.trim().startsWith('```')) {
      const match = line.trim().match(/^```(\w+)?/);
      const language = match ? match[1] : '';
      let codeEnd = i + 1;
      while (codeEnd < lines.length && !lines[codeEnd].trim().startsWith('```')) {
        codeEnd++;
      }
      const codeContent = lines.slice(i + 1, codeEnd).join('\n');
      result.push(
        <CodeBlock key={`code-${i}`} code={codeContent} language={language} />
      );
      i = codeEnd + 1;
      continue;
    }

    // Check for list items
    if (line.trim().match(listMarkerRegex)) {
      const listStart = i;
      while (i < lines.length && (lines[i].trim().match(listMarkerRegex) || lines[i].startsWith('  ') || lines[i].startsWith('\t'))) {
        i++;
      }

      const listItems = lines.slice(listStart, i);
      const isNumbered = listItems[0].trim().match(/^\d+\./);

      result.push(
        <ul key={`list-${listStart}`} className={`my-2 ${isNumbered ? 'list-decimal' : 'list-disc'} ml-6`}>
          {listItems.map((item, idx) => {
            const cleanItem = item.trim().replace(listMarkerRegex, '');
            return (
              <li key={idx} className="mb-1 text-slate-300">
                {parseInline(cleanItem)}
              </li>
            );
          })}
        </ul>
      );
      continue;
    }

    // Check for horizontal rule
    if (line.match(/^[-_*]{3,}/)) {
      result.push(<hr key={`hr-${i}`} className="border-t border-slate-700 my-3" />);
      i++;
      continue;
    }

    // Regular paragraph
    if (line.trim()) {
      result.push(
        <p key={`p-${i}`} className="mb-2 leading-relaxed text-slate-300">
          {parseInline(line)}
        </p>
      );
    } else {
      result.push(<div key={`space-${i}`} className="mb-2" />);
    }

    i++;
  }

  return result;
};

const parseInline = (text: string): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let partKey = 0;

  // Replace markdown inline elements (non-global to prevent regex state retention)
  const patterns = [
    { regex: /\*\*(.*?)\*\*/, render: (match: string) => <strong className="font-bold text-slate-100">{match}</strong> },
    { regex: /__(.*?)__/, render: (match: string) => <strong className="font-bold text-slate-100">{match}</strong> },
    { regex: /\*(.*?)\*/, render: (match: string) => <em className="italic text-slate-300">{match}</em> },
    { regex: /_(.*?)_/, render: (match: string) => <em className="italic text-slate-300">{match}</em> },
    { regex: /`(.*?)`/, render: (match: string) => <code className="bg-slate-900 border border-slate-700/60 text-sky-400 px-1.5 py-0.5 rounded text-xs font-mono">{match}</code> },
    { regex: /\[(.*?)\]\((.*?)\)/, render: (match: string, url: string) => <a href={url} className="text-sky-400 hover:underline" target="_blank" rel="noopener noreferrer">{match}</a> },
  ];

  while (remaining.length > 0) {
    let found = false;

    for (const pattern of patterns) {
      const match = pattern.regex.exec(remaining);
      if (match && match.index === 0) {
        const fullMatch = match[0];
        const content = match[1];
        const url = match[2];

        parts.push(
          <span key={`inline-${partKey++}`}>
            {pattern.render(content, url)}
          </span>
        );

        remaining = remaining.substring(fullMatch.length);
        found = true;
        break;
      }
    }

    if (!found) {
      const nextMatch = patterns.reduce((min, pattern) => {
        const match = pattern.regex.exec(remaining);
        return !match ? min : match.index < min ? match.index : min;
      }, remaining.length);

      if (nextMatch > 0) {
        parts.push(remaining.substring(0, nextMatch));
        remaining = remaining.substring(nextMatch);
      } else {
        parts.push(remaining);
        remaining = '';
      }
    }
  }

  return parts;
};

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`flex gap-3 w-full animate-fade-in ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      {isAssistant && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center mt-1">
          <Bot size={16} />
        </div>
      )}
      
      <div className={`max-w-[85%] ${isAssistant ? 'chat-bubble-assistant font-sans select-text leading-relaxed text-sm' : 'chat-bubble-user font-sans select-text leading-relaxed text-sm'}`}>
        {!isAssistant && (
          <p className="text-sm whitespace-pre-wrap leading-relaxed select-text">{message.content}</p>
        )}
        {isAssistant && (
          <div className="prose-dark text-sm space-y-2 select-text">
            {message.content === '' ? (
              <div className="flex items-center gap-1.5 py-2 px-1 text-slate-500 font-mono text-xs select-none">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                <span className="ml-1 text-[10px] text-slate-400">Assistant preparing response...</span>
              </div>
            ) : (
              formatMarkdown(message.content)
            )}
          </div>
        )}
        <div className="mt-2 text-[10px] text-slate-500 text-right select-none">{formatMessageTime(message.timestamp)}</div>
      </div>

      {!isAssistant && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-800 border border-slate-700/60 text-slate-400 flex items-center justify-center mt-1">
          <User size={16} />
        </div>
      )}
    </div>
  );
};
