import React from 'react';
import { Eye, EyeOff, HelpCircle, Minus, Plus as PlusIcon, X } from 'lucide-react';
import type { ChatConfig } from '../types';
import classNames from 'classnames';

interface SettingsDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    config: ChatConfig;
    setConfig: (config: ChatConfig) => void;
}

const PROVIDERS = [
    { id: 'anthropic', label: 'Anthropic' },
    { id: 'bedrock', label: 'Bedrock' },
    { id: 'vertex', label: 'Vertex' },
];

const TOOL_VERSIONS = [
    'computer_use_20250124',
    'computer_use_20241022',
    'computer_use_20250429',
    'computer_use_20251124',
];

export const SettingsDrawer: React.FC<SettingsDrawerProps> = ({ 
    isOpen, onClose, config, setConfig
}) => {
    const [showApiKey, setShowApiKey] = React.useState(false);
    
    // Helper to update config number fields safely
    const updateNumber = (field: keyof ChatConfig, diff: number, min = 0) => {
        const current = (config[field] as number) || 0;
        setConfig({ ...config, [field]: Math.max(min, current + diff) });
    };

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div 
                    className="fixed inset-0 bg-black/50 z-40 transition-opacity"
                    onClick={onClose}
                />
            )}

            {/* Drawer */}
            <div className={classNames(
                "fixed right-0 top-0 h-full w-80 bg-[#1a1b1e] text-gray-300 font-sans shadow-2xl z-50 transform transition-transform duration-300 ease-in-out border-l border-[#2c2d31]",
                isOpen ? "translate-x-0" : "translate-x-full"
            )}>
                {/* Header */}
                <div className="p-4 border-b border-[#2c2d31] flex justify-between items-center bg-[#1a1b1e]">
                    <h2 className="font-semibold text-white">Settings</h2>
                    <button 
                        onClick={onClose}
                        className="p-1 hover:bg-[#2c2d31] rounded-full transition text-gray-400 hover:text-white"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar h-[calc(100%-60px)]">
                    <div className="space-y-6 text-sm">
                        
                        {/* API Provider */}
                        <div className="space-y-3">
                            <label className="block text-gray-400 font-medium">API Provider</label>
                            <div className="space-y-2">
                                {PROVIDERS.map(p => (
                                     <label key={p.id} className="flex items-center gap-3 cursor-pointer group">
                                        <div className={classNames(
                                            "w-5 h-5 rounded-full border flex items-center justify-center transition",
                                            config.provider === p.id ? "border-blue-500 bg-transparent" : "border-gray-600 group-hover:border-gray-500"
                                        )}>
                                            {config.provider === p.id && <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />}
                                        </div>
                                        <input 
                                            type="radio" 
                                            className="hidden" 
                                            name="provider" 
                                            checked={config.provider === p.id}
                                            onChange={() => {
                                                 let newModel = config.model;
                                                 if (p.id === 'anthropic') newModel = 'claude-sonnet-4-5-20250929';
                                                 if (p.id === 'bedrock') newModel = 'anthropic.claude-3-5-sonnet-20241022-v2:0';
                                                 setConfig({...config, provider: p.id, model: newModel});
                                            }}
                                        />
                                        <span className={classNames("transition", config.provider === p.id ? "text-blue-400" : "text-gray-400 group-hover:text-gray-300")}>
                                            {p.label}
                                        </span>
                                     </label>
                                ))}
                            </div>
                        </div>

                        {/* Model */}
                        <div className="space-y-2">
                            <label className="block text-gray-400 font-medium">Model</label>
                            {config.provider === 'anthropic' ? (
                                <select 
                                    className="w-full p-2.5 rounded-lg bg-[#141517] border border-[#2c2d31] text-gray-200 focus:border-blue-500 focus:outline-none"
                                    value={config.model}
                                    onChange={e => setConfig({...config, model: e.target.value})}
                                >
                                    <option value="claude-sonnet-4-5-20250929">claude-sonnet-4-5-20250929</option>
                                    <option value="claude-3-5-haiku-20241022">claude-3-5-haiku-20241022</option>
                                    <option value="claude-3-opus-20240229">claude-3-opus-20240229</option>
                                </select>
                            ) : config.provider === 'bedrock' ? (
                                <select 
                                    className="w-full p-2.5 rounded-lg bg-[#141517] border border-[#2c2d31] text-gray-200 focus:border-blue-500 focus:outline-none"
                                    value={config.model}
                                    onChange={e => setConfig({...config, model: e.target.value})}
                                >
                                    <option value="anthropic.claude-3-5-sonnet-20241022-v2:0">anthropic.claude-3-5-sonnet-20241022-v2:0</option>
                                    <option value="anthropic.claude-3-5-haiku-20241022-v1:0">anthropic.claude-3-5-haiku-20241022-v1:0</option>
                                    <option value="anthropic.claude-3-opus-20240229-v1:0">anthropic.claude-3-opus-20240229-v1:0</option>
                                </select>
                             ) : (
                                <input 
                                    type="text" 
                                    className="w-full p-2.5 rounded-lg bg-[#141517] border border-[#2c2d31] text-gray-200 focus:border-blue-500 focus:outline-none"
                                    value={config.model}
                                    onChange={e => setConfig({...config, model: e.target.value})}
                                    placeholder="Model ID"
                                />
                             )}
                        </div>

                        {/* API Key */}
                        <div className="space-y-2">
                             <div className="flex justify-between">
                                <label className="block text-gray-400 font-medium">Claude API Key</label>
                            </div>
                            <div className="relative">
                                <input 
                                    type={showApiKey ? "text" : "password"}
                                    className="w-full p-2.5 pr-10 rounded-lg bg-[#141517] border border-[#2c2d31] text-gray-200 focus:border-blue-500 focus:outline-none"
                                    placeholder="sk-..."
                                    value={config.api_key}
                                    onChange={e => setConfig({...config, api_key: e.target.value})}
                                />
                                <button 
                                    className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-300"
                                    onClick={() => setShowApiKey(!showApiKey)}
                                >
                                    {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>

                        {/* Only send N most recent images */}
                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <label className="block text-gray-400 font-medium">Only send N most recent images</label>
                                <HelpCircle size={14} className="text-gray-500" />
                            </div>
                            <div className="flex items-center bg-[#141517] border border-[#2c2d31] rounded-lg">
                                <span className="flex-1 p-2.5 text-gray-200">{config.only_n_most_recent_images}</span>
                                <div className="flex gap-1 pr-2">
                                     <button onClick={() => updateNumber('only_n_most_recent_images', -1)} className="p-1 text-gray-400 hover:text-white"><Minus size={14} /></button>
                                     <button onClick={() => updateNumber('only_n_most_recent_images', 1)} className="p-1 text-gray-400 hover:text-white"><PlusIcon size={14} /></button>
                                </div>
                            </div>
                        </div>

                         {/* Custom System Prompt */}
                        <div className="space-y-2">
                             <div className="flex justify-between items-center">
                                <label className="block text-gray-400 font-medium">Custom System Prompt Suffix</label>
                                <HelpCircle size={14} className="text-gray-500" />
                            </div>
                            <textarea 
                                className="w-full p-2.5 rounded-lg bg-[#141517] border border-[#2c2d31] text-gray-200 focus:border-blue-500 focus:outline-none h-24 resize-none"
                                value={config.system_prompt_suffix}
                                onChange={e => setConfig({...config, system_prompt_suffix: e.target.value})}
                            />
                        </div>

                        {/* Checkboxes */}
                         <div className="space-y-3">
                             <label className="flex items-center gap-3 cursor-pointer group">
                                <div className={classNames("w-5 h-5 rounded border flex items-center justify-center transition", config.enable_token_efficient_tools ? "bg-transparent border-blue-500" : "border-gray-600 bg-transparent")}>
                                     {config.enable_token_efficient_tools && <div className="w-2.5 h-2.5 bg-blue-500 rounded-sm" />}
                                </div>
                                <input type="checkbox" className="hidden" checked={!!config.enable_token_efficient_tools} onChange={e => setConfig({...config, enable_token_efficient_tools: e.target.checked})} />
                                <span className="text-gray-400">Enable token-efficient tools beta</span>
                            </label>
                        </div>
                        
                        {/* Tool Versions */}
                         <div className="space-y-3">
                            <label className="block text-gray-400 font-medium">Tool Versions</label>
                            <div className="space-y-2">
                                {TOOL_VERSIONS.map(v => (
                                     <label key={v} className="flex items-center gap-3 cursor-pointer group">
                                        <div className={classNames(
                                            "w-5 h-5 rounded-full border flex items-center justify-center transition",
                                            config.tool_version === v ? "border-blue-500 bg-transparent" : "border-gray-600 group-hover:border-gray-500"
                                        )}>
                                            {config.tool_version === v && <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />}
                                        </div>
                                        <input 
                                            type="radio" 
                                            className="hidden" 
                                            name="tool_version" 
                                            checked={config.tool_version === v}
                                            onChange={() => setConfig({...config, tool_version: v})}
                                        />
                                        <span className={classNames("transition", config.tool_version === v ? "text-blue-400" : "text-gray-400 group-hover:text-gray-300")}>
                                            {v}
                                        </span>
                                     </label>
                                ))}
                            </div>
                        </div>
                        
                         {/* Max Output Tokens */}
                        <div className="space-y-2">
                             <label className="block text-gray-400 font-medium">Max Output Tokens</label>
                             <div className="flex items-center bg-[#141517] border border-[#2c2d31] rounded-lg">
                                <span className="flex-1 p-2.5 text-gray-200">{config.max_tokens}</span>
                                <div className="flex gap-1 pr-2">
                                     <button onClick={() => updateNumber('max_tokens', -100)} className="p-1 text-gray-400 hover:text-white"><Minus size={14} /></button>
                                     <button onClick={() => updateNumber('max_tokens', 100)} className="p-1 text-gray-400 hover:text-white"><PlusIcon size={14} /></button>
                                </div>
                            </div>
                        </div>
                        
                        {/* Reset Button */}
                        <button 
                            onClick={() => window.location.reload()} // Simple reset for now or reset config to defaults
                            className="flex items-center justify-center gap-2 p-2 px-4 border border-[#2c2d31] rounded-lg text-gray-400 hover:text-white hover:bg-[#2c2d31] transition w-fit"
                        >
                            Reset
                        </button>

                    </div>
                </div>
            </div>
        </>
    );
};
