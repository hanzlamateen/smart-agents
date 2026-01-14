export interface Message {
  id?: string;
  role: 'user' | 'assistant' | 'tool';
  content: any; // Using any for flexibility with Anthropic blocks
  created_at?: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
}

export interface Instance {
  status: 'starting' | 'running' | 'stopped' | 'error' | 'pending';
  vnc_port: number | null;
}

export interface ChatConfig {
  provider: string;
  api_key: string;
  model: string;
  system_prompt_suffix: string;
  max_tokens: number;
  thinking_budget: number;
  only_n_most_recent_images: number;
  enable_token_efficient_tools: boolean;
  tool_version: string;
}
