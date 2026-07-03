import React from 'react';
import { ChatMessage } from '../types';
import { Bot, User } from 'lucide-react';

interface ChatBubbleProps {
  message: ChatMessage;
}

// Simple custom markdown formatter to avoid complex libraries and guarantee correct rendering
const formatMarkdown = (text: string) => {
  if (!text) return null;

  const lines = text.split('\n');
  return lines.map((line, idx) => {
    let content: React.ReactNode = line;
    
    // Check for code blocks
    if (line.trim().startsWith('```')) {
      return null; // Skip wrapper line, simple formatting will handle inline elements
    }

    // Check for headers
    if (line.startsWith('# ')) {
      return <h1 key={idx} className="text-xl font-bold text-slate-100 mt-4 mb-2">{line.substring(2)}</h1>;
    }
    if (line.startsWith('## ')) {
      return <h2 key={idx} className="text-lg font-bold text-slate-100 mt-3 mb-2">{line.substring(3)}</h2>;
    }
    if (line.startsWith('### ')) {
      return <h3 key={idx} className="text-base font-bold text-slate-200 mt-2 mb-1">{line.substring(4)}</h3>;
    }

    // Check for list items
    if (line.trim().startsWith('• ') || line.trim().startsWith('- ')) {
      const cleanLine = line.trim().substring(2);
      content = <li key={idx} className="list-disc ml-5 mb-1">{parseInline(cleanLine)}</li>;
      return content;
    }

    // Check for numbered lists
    const numListMatch = line.trim().match(/^(\d+)\.\s(.*)/);
    if (numListMatch) {
      content = <li key={idx} className="list-decimal ml-5 mb-1">{parseInline(numListMatch[2])}</li>;
      return content;
    }

    // Check for bold text, inline code, etc.
    return <p key={idx} className="mb-2 leading-relaxed">{parseInline(line)}</p>;
  });
};

const parseInline = (text: string): React.ReactNode[] => {
  // Regex matchers for bold (**bold** or *bold*) and code (`code`)
  const parts = [];
  let remaining = text;
  
  while (remaining.length > 0) {
    const boldMatch = remaining.match(/(\*\*|`)(.*?)\1/);
    if (!boldMatch) {
      parts.push(remaining);
      break;
    }

    const matchIndex = remaining.indexOf(boldMatch[0]);
    if (matchIndex > 0) {
      parts.push(remaining.substring(0, matchIndex));
    }

    const type = boldMatch[1];
    const matchContent = boldMatch[2];

    if (type === '**') {
      parts.push(<strong key={remaining.length} className="font-bold text-slate-100">{matchContent}</strong>);
    } else if (type === '`') {
      parts.push(
        <code key={remaining.length} className="bg-slate-900 border border-slate-700/60 text-sky-400 px-1.5 py-0.5 rounded text-xs font-mono">
          {matchContent}
        </code>
      );
    }

    remaining = remaining.substring(matchIndex + boldMatch[0].length);
  }

  return parts;
};

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`flex gap-3 w-full animate-fade-in ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      {isAssistant && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
          <Bot size={16} />
        </div>
      )}
      
      <div className={`max-w-[85%] ${isAssistant ? 'chat-bubble-assistant' : 'chat-bubble-user'}`}>
        {!isAssistant && (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        )}
        {isAssistant && (
          <div className="prose-dark font-sans text-sm">
            {formatMarkdown(message.content)}
          </div>
        )}
      </div>

      {!isAssistant && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-800 border border-slate-700/60 text-slate-400 flex items-center justify-center">
          <User size={16} />
        </div>
      )}
    </div>
  );
};
