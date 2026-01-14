import React, { useState, type KeyboardEvent } from "react";
import { Send, Settings, Square } from "lucide-react";

interface InputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  // Controlled props
  inputMessage?: string;
  setInputMessage?: (msg: string) => void;
  onOpenSettings: () => void;
}

export const Input: React.FC<InputProps> = ({
  onSend,
  onStop,
  isStreaming,
  disabled,
  inputMessage,
  setInputMessage,
  onOpenSettings,
}) => {
  // If controlled, use props. If not, use local state.
  const isControlled =
    inputMessage !== undefined && setInputMessage !== undefined;
  const [localText, setLocalText] = useState("");

  const text = isControlled ? inputMessage : localText;
  const setText = isControlled ? setInputMessage : setLocalText;

  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 192) + "px"; // 192px = max-h-48
    }
  }, [text]);

  const handleSend = () => {
    if (!text.trim()) return;
    onSend(text);
    if (!isControlled) {
      setText("");
    } else {
      setText("");
    }
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full">
      <div className="relative flex items-end gap-2 p-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500 transition-all">
        {/* Settings Button (Left) */}
        <button
          onClick={onOpenSettings}
          className="p-2 text-gray-400 hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition shrink-0 mb-0.5"
          title="Settings"
        >
          <Settings size={20} />
        </button>

        <textarea
          ref={textareaRef}
          className="w-full py-3 px-1 max-h-48 bg-transparent text-gray-900 dark:text-gray-100 outline-none resize-none overflow-y-auto custom-scrollbar"
          rows={1}
          placeholder="Ask Smart Agent to do something..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isStreaming}
          style={{ minHeight: "44px" }}
        />

        {/* Send / Stop Button (Right) */}
        {isStreaming ? (
          <div className="relative shrink-0 mb-0.5 w-10 h-10 flex items-center justify-center">
            {/* Spinner border */}
            <div className="absolute inset-0 rounded-full border-2 border-red-200 border-t-red-500 animate-spin" />
            <button
              onClick={onStop}
              className="p-2 text-red-500 hover:bg-red-50 hover:text-red-600 rounded-lg transition flex items-center justify-center w-full h-full z-10"
              title="Stop"
            >
              <Square size={16} fill="currentColor" />
            </button>
          </div>
        ) : (
          <button
            onClick={handleSend}
            disabled={!text.trim() || disabled}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed transition shrink-0 mb-0.5 w-10 h-10 flex items-center justify-center"
            title="Send"
          >
            <Send size={18} />
          </button>
        )}
      </div>
    </div>
  );
};
