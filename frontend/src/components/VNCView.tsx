import React from 'react';

export const VNCView: React.FC = () => {
    // Assuming backend container exposes noVNC on port 6080 relative to localhost
    // Since we are running in docker compose, mapped ports should be consistent.
    // If accessing from browser, localhost:6080 should work.
    const vncUrl = "http://localhost:6080/vnc.html?autoconnect=true&resize=scale";

    return (
        <div className="h-full w-full bg-black flex flex-col items-center justify-center p-2 rounded-lg border border-gray-700">
            <div className="w-full h-full relative">
                <iframe 
                    src={vncUrl} 
                    className="w-full h-full border-none rounded"
                    title="Remote Desktop"
                />
            </div>
        </div>
    );
};
