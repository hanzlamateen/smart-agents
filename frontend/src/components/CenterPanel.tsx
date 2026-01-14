import React from 'react';
import { Loader2 } from 'lucide-react';

interface CenterPanelProps {
    vncPort?: number | null;
    status: string;
}

export const CenterPanel: React.FC<CenterPanelProps> = ({ vncPort, status }) => {
    
    // Derived state
    const isLoading = status === 'starting' || status === 'pending';
    const isStopped = status === 'stopped' || status === 'error';
    const vncUrl = vncPort ? `http://localhost:${vncPort}/vnc.html?autoconnect=true&resize=scale` : null;

    return (
        <div className="flex-1 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col overflow-hidden relative">
            {/* VNC Canvas Area */}
            <div className="flex-1 bg-[#1e1e1e] relative overflow-hidden flex items-center justify-center">
                {isLoading && (
                    <div className="absolute inset-0 bg-[#1e1e1e] flex flex-col items-center justify-center opacity-90 z-10 text-white">
                        <Loader2 className="w-8 h-8 animate-spin mb-4" />
                        <p className="text-sm font-medium">Spawning Remote Desktop...</p>
                        <p className="text-xs text-gray-400 mt-2">This may take a few seconds</p>
                    </div>
                )}
                
                {isStopped && (
                     <div className="absolute inset-0 bg-[#1e1e1e] flex flex-col items-center justify-center opacity-90 z-10 text-white">
                        <p className="text-sm font-medium text-red-400">Instance Stopped</p>
                    </div>
                )}

                {/* iframe for noVNC */}
                {vncUrl && status === 'running' && (
                    <iframe 
                        src={vncUrl}
                        className="w-full h-full border-none"
                        title="VNC Viewer"
                    />
                )}
                
                {/* Idle / No Session State */}
                {!isLoading && !isStopped && (!vncUrl || status !== 'running') && (
                     <div className="absolute inset-0 bg-[#1e1e1e] flex flex-col items-center justify-center opacity-90 z-10 text-gray-400">
                        <p className="text-sm font-medium">Select a session or create a new one to start</p>
                    </div>
                )}
            </div>
        </div>
    );
};
