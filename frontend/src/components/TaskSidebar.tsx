import React from 'react';
import { Plus, Search, MessageSquare, Book } from 'lucide-react';
import type { Session as SessionType } from '../types';
import classNames from 'classnames';

interface TaskSidebarProps {
    sessions: SessionType[];
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onCreateSession: () => void;
    searchQuery: string;
    onSearch: (query: string) => void;
    onLoadMore: () => void;
    hasMore: boolean;
}

export const TaskSidebar: React.FC<TaskSidebarProps> = ({ 
    sessions, currentSessionId, onSelectSession, onCreateSession, searchQuery, onSearch, onLoadMore, hasMore 
}) => {
    return (
        <div className="w-64 h-full flex flex-col gap-4 font-sans text-gray-700">
            {/* Search */}
            <div className="relative">
                <Search className="absolute left-3 top-2.5 text-white" size={16} />
                <input 
                    type="text" 
                    placeholder="Search" 
                    value={searchQuery}
                    onChange={(e) => onSearch(e.target.value)}
                    className="w-full bg-blue-500 text-white placeholder-blue-200 pl-10 pr-8 py-2 rounded-lg focus:outline-none"
                    style={{backgroundColor: '#4285F4'}}
                />
                {searchQuery && (
                    <button 
                        onClick={() => onSearch('')}
                        className="absolute right-2 top-2.5 text-blue-200 hover:text-white transition"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L10 10 5.707 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Task History Panel */}
            <div className="flex-1 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col overflow-hidden">
                <div className="p-3 border-b border-gray-100 font-semibold text-gray-500 text-sm bg-gray-50">
                    Task History
                </div>
                
                <div className="flex-1 overflow-y-auto p-2 space-y-1">


                    <div className="px-2 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider mt-4 mb-1">Your Sessions</div>
                    {sessions.map(session => (
                        <button
                            key={session.id}
                            onClick={() => onSelectSession(session.id)}
                            className={classNames(
                                "w-full text-left px-3 py-2 rounded text-sm flex items-center gap-2 truncate transition",
                                currentSessionId === session.id 
                                    ? "bg-blue-50 text-blue-600 font-medium" 
                                    : "hover:bg-gray-50 text-gray-600"
                            )}
                        >
                            <MessageSquare size={14} />
                            <span className="truncate">{session.title || `Session ${session.id}`}</span>
                        </button>
                    ))}
                    
                    {hasMore && (
                        <button
                            onClick={onLoadMore}
                            className="w-full text-center px-3 py-2 text-xs text-blue-500 hover:text-blue-700 font-medium transition mt-2"
                        >
                            Load More
                        </button>
                    )}
                </div>

                {/* Bottom Menu Items */}
                <div className="p-2 border-t border-gray-100 space-y-1">
                     <button className="w-full text-left px-3 py-2 rounded hover:bg-gray-50 text-sm flex items-center gap-2 text-gray-600">
                        <Book size={14} /> Prompt Gallery
                    </button>
                </div>
            </div>

            {/* New Task Button */}
            <button 
                onClick={onCreateSession}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 rounded-lg font-medium flex items-center justify-center gap-2 shadow-sm transition"
                style={{backgroundColor: '#4285F4'}}
            >
                <Plus size={18} /> New Agent Task
            </button>
        </div>
    );
};
