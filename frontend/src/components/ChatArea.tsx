import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../types';
import classNames from 'classnames';
import { Bot, User, Cpu, FileImage, TriangleAlert } from 'lucide-react';

interface ChatAreaProps {
  messages: Message[];
  isStreaming: boolean;
}

export const ChatArea: React.FC<ChatAreaProps> = ({ messages, isStreaming }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const renderContent = (content: any) => {
    if (!Array.isArray(content)) {
        // Handle direct text content if simplified
        return <div className="prose prose-sm max-w-none"><ReactMarkdown>{String(content)}</ReactMarkdown></div>;
    }

    return content.map((block: any, idx: number) => {
      if (block.type === 'text') {
        return (
            <div key={idx} className="prose prose-sm max-w-none">
                <ReactMarkdown
                    components={{
                        code({node, inline, className, children, ...props}: any) {
                            const match = /language-(\w+)/.exec(className || '')
                            return !inline && match ? (
                                <SyntaxHighlighter
                                    style={oneLight}
                                    language={match[1]}
                                    PreTag="div"
                                    {...props}
                                >
                                    {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                            ) : (
                                <code className={className} {...props}>
                                    {children}
                                </code>
                            )
                        }
                    }}
                >
                    {block.text}
                </ReactMarkdown>
            </div>
        );
      }
      
      if (block.type === 'thinking') {
          return (
              <div key={idx} className="text-sm text-gray-500 italic border-l-2 border-gray-300 pl-2 my-2 bg-gray-50 p-2 rounded-r">
                  <div className="font-semibold text-xs uppercase mb-1 flex items-center gap-1"><Cpu size={12}/> Thinking</div>
                  <div className="whitespace-pre-wrap">{block.thinking}</div>
              </div>
          )
      }

      if (block.type === 'tool_use') {
        return (
          <div key={idx} className="bg-gray-100 rounded p-2 my-2 text-xs font-mono border border-gray-200">
             <div className="font-bold text-gray-600 mb-1 flex items-center gap-1">🛠️ Tool Call: {block.name}</div>
             <pre className="overflow-x-auto text-gray-800">{JSON.stringify(block.input, null, 2)}</pre>
          </div>
        );
      }

      if (block.type === 'tool_result') {
         const isError = block.is_error;
         let output = block.content;

         // Handle flattened SSE structure from loop.py
         if (!output && (block.output || block.base64_image || block.image_url)) {
             output = [];
             if (block.output) {
                 output.push({ type: 'text', text: block.output });
             }
             if (block.image_url) {
                 output.push({
                     type: 'image',
                     source: {
                         type: 'url',
                         url: block.image_url
                     }
                 });
             } else if (block.base64_image) {
                 output.push({
                     type: 'image',
                     source: {
                         type: 'base64',
                         media_type: 'image/png',
                         data: block.base64_image
                     }
                 });
             }
         }
         
         // Inner content of tool result
         const renderToolOutput = (innerParts: any[]) => {
             if (!Array.isArray(innerParts)) return String(innerParts);
             return innerParts.map((part, pIdx) => {
                 if (part.type === 'text') return (
                     <div key={pIdx} className="whitespace-pre-wrap max-h-60 overflow-y-auto">{part.text}</div>
                 );
                 if (part.type === 'image') {
                     let src = '';
                     if (part.source.type === 'base64') {
                         src = `data:${part.source.media_type};base64,${part.source.data}`;
                     } else if (part.source.type === 'url') {
                         src = part.source.url;
                     }

                     return (
                         <div key={pIdx} className="my-2">
                            <img 
                                src={src} 
                                alt="Tool Result" 
                                className="max-w-full rounded border border-gray-300 shadow-sm"
                            />
                         </div>
                     );
                 };
                 return null;
             })
         }
         
         return (
             <div key={idx} className={classNames("rounded p-2 my-2 text-sm border max-h-96 overflow-y-auto custom-scrollbar", isError ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200")}>
                 <div className="font-bold text-gray-500 mb-1 flex items-center gap-1 sticky top-0 bg-inherit pb-1 border-b border-inherit">
                     {isError ? <TriangleAlert size={14} className="text-red-500"/> : <FileImage size={14}/>}
                     Tool Output
                 </div>
                 {renderToolOutput(Array.isArray(output) ? output : [{type: 'text', text: output}])}
             </div>
         )
      }
      
      return null;
    });
  };

  if (messages.length === 0) {
      return (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-gray-500">
              <div className="bg-gray-100 dark:bg-gray-800 p-6 rounded-2xl mb-4">
                  <Bot size={48} className="text-blue-500" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-700 dark:text-gray-300">Welcome to Smart Agents</h3>
              <p className="max-w-md text-center">
                  Enter your API Key in the settings (or use the environment variable), then type a request below to get started. 
                  <br/>Example: <em>"Check the weather in London using Firefox"</em>
              </p>
          </div>
      );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-white dark:bg-gray-900 custom-scrollbar">
      {messages.map((msg, index) => (
        <div 
            key={index} 
            className={classNames(
                "flex gap-3 max-w-4xl mx-auto",
                msg.role === 'user' ? "flex-row-reverse" : "flex-row"
            )}
        >
          <div className={classNames(
              "w-8 h-8 rounded-full flex items-center justify-center shrink-0 border",
              msg.role === 'assistant' ? "bg-orange-100 text-orange-600 border-orange-200" : (msg.role === 'user' ? "bg-blue-100 text-blue-600 border-blue-200" : "bg-gray-100 text-gray-600 border-gray-200")
          )}>
            {msg.role === 'assistant' ? <Bot size={18} /> : (msg.role === 'user' ? <User size={18} /> : <Cpu size={18}/>)}
          </div>
          
          <div className={classNames(
              "flex-1 min-w-0 rounded-lg p-4 shadow-sm border",
              msg.role === 'user' ? "bg-blue-50 border-blue-100 dark:bg-blue-900/20 dark:border-blue-800" : "bg-white border-gray-100 dark:bg-gray-800 dark:border-gray-700"
          )}>
             {renderContent(msg.content)}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};
