import React from 'react';
import { ChatArea } from './ChatArea';
import { Input } from './Input';
import type { Message } from '../types';



interface RightPanelProps {
    messages: Message[];
    inputMessage: string;
    setInputMessage: (msg: string) => void;
    handleSendMessage: () => void;
    isStreaming: boolean;
    onOpenSettings: () => void;
    onStop: () => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({
    messages, inputMessage, setInputMessage, handleSendMessage, isStreaming, onOpenSettings, onStop
}) => {
    return (
        <div className="w-96 h-full flex flex-col gap-4">
            {/* Chat Card */}
            <div className="flex-1 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col overflow-hidden relative">
                 {/* Chat Area */}
                 <div className="flex-1 overflow-hidden relative flex flex-col min-h-0">
                    <ChatArea messages={messages} isStreaming={isStreaming} />
                 </div>

                 {/* Input Area (Integrated at bottom of card) */}
                 <div className="p-4 border-t border-gray-100 bg-white">
                    <Input 
                        inputMessage={inputMessage}
                        setInputMessage={setInputMessage}
                        onSend={handleSendMessage}
                        isStreaming={isStreaming}
                        onOpenSettings={onOpenSettings}
                        onStop={onStop}
                    />
                 </div>
            </div>


        </div>
    );
};
