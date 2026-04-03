import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'motion/react';
import { Send, Terminal, Box, Database, FileText, Cpu, Info, Sparkles, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/src/lib/utils';

const API_BASE_URL = import.meta.env.DEV ? '/api' : 'http://localhost:8000/api';

const examplePrompts = [
  '参数化螺旋楼梯，高度 12m，踏步宽度 1.2m',
  '基于 Voronoi 算法的建筑外立面遮阳系统',
  '模块化集装箱住宅集群，包含 15 个单元',
];

const quickActions = ['结构验证', '材质分配', '光照模拟', '导出 STL'];

interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
  status?: 'success' | 'error' | 'processing';
  progress?: string;
}

export function Explore() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: 'Pal 3D 已就绪。等待输入设计简报...' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentProgress, setCurrentProgress] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setCurrentProgress(null);

    // Add processing message
    const processingMsg: Message = {
      role: 'assistant',
      content: '正在处理...',
      status: 'processing'
    };
    setMessages(prev => [...prev, processingMsg]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: input }],
          session_id: `session_${Date.now()}`,
          thread_id: `thread_${Date.now()}`,
        }),
      });

      if (!response.ok) {
        throw new Error('API 请求失败');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      let buffer = '';
      let finalContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'start') {
                setCurrentProgress('开始处理...');
              } else if (data.type === 'progress') {
                setCurrentProgress(data.content);
                // Update processing message
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastIdx = newMessages.length - 1;
                  if (newMessages[lastIdx].status === 'processing') {
                    newMessages[lastIdx] = {
                      ...newMessages[lastIdx],
                      content: data.content,
                      progress: data.node
                    };
                  }
                  return newMessages;
                });
              } else if (data.type === 'complete') {
                finalContent = data.content;
                setCurrentProgress(null);
              } else if (data.type === 'error') {
                throw new Error(data.content);
              }
            } catch (e) {
              console.error('解析 SSE 数据失败:', e);
            }
          }
        }
      }

      // Update final message
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        newMessages[lastIdx] = {
          role: 'assistant',
          content: finalContent,
          status: 'success'
        };
        return newMessages;
      });

    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        newMessages[lastIdx] = {
          role: 'assistant',
          content: `处理出错: ${error instanceof Error ? error.message : '未知错误'}。\n\n请确保后端服务已启动 (python api_server.py)`,
          status: 'error'
        };
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      setCurrentProgress(null);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="pt-20 min-h-screen lg:h-screen flex flex-col lg:flex-row overflow-hidden bg-bg-warm">
      {/* Left: Interaction Console */}
      <div className="w-full lg:w-1/2 flex flex-col border-r border-border-subtle bg-white overflow-hidden">
        <div className="p-6 border-b border-border-subtle flex items-center justify-between bg-white sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-2 h-2 rounded-full",
              isLoading ? "bg-yellow-500 animate-pulse" : "bg-accent"
            )} />
            <h2 className="text-sm font-bold tracking-tight uppercase font-mono">Design Brief Console v1.0</h2>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-ink/30 uppercase tracking-widest">
            <span>{isLoading ? 'Processing...' : 'Status: Connected'}</span>
            <span>Node: {currentProgress || 'Idle'}</span>
          </div>
        </div>

        {/* Conversation History */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8 scrollbar-hide">
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={cn(
                "flex gap-4",
                msg.role === 'user' ? "items-start" : "items-center"
              )}
            >
              <div className={cn(
                "w-8 h-8 flex items-center justify-center shrink-0 text-[10px] font-mono font-bold border",
                msg.role === 'user' ? "bg-ink text-white border-ink" :
                msg.status === 'processing' ? "bg-yellow-100 text-yellow-700 border-yellow-200" :
                msg.status === 'error' ? "bg-red-100 text-red-700 border-red-200" :
                "bg-bg-warm text-ink/40 border-border-subtle"
              )}>
                {msg.status === 'processing' ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : msg.role === 'user' ? 'USR' : 'SYS'}
              </div>
              <div className={cn(
                "text-sm leading-relaxed",
                msg.role === 'user' ? "text-ink font-medium" :
                msg.status === 'processing' ? "text-ink/70 font-mono" :
                msg.status === 'error' ? "text-red-600 font-mono" :
                "text-ink/50 font-mono"
              )}>
                {msg.content}
                {msg.status === 'success' && (
                  <div className="mt-2 flex gap-2">
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] rounded-full flex items-center gap-1">
                      <CheckCircle2 size={10} /> VALIDATED
                    </span>
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] rounded-full">SCRIPT_READY</span>
                  </div>
                )}
                {msg.status === 'error' && (
                  <div className="mt-2 flex gap-2">
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] rounded-full flex items-center gap-1">
                      <XCircle size={10} /> ERROR
                    </span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-8 border-t border-border-subtle bg-bg-warm/30">
          <div className="mb-6">
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-3">快速操作 (Quick Actions)</div>
            <div className="flex flex-wrap gap-2">
              {quickActions.map(action => (
                <button
                  key={action}
                  disabled={isLoading}
                  className="px-3 py-1 bg-white border border-border-subtle text-[10px] font-medium hover:border-accent hover:text-accent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {action}
                </button>
              ))}
            </div>
          </div>

          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的设计简报或指令..."
              disabled={isLoading}
              className="w-full h-40 bg-white border-2 border-accent focus:ring-2 focus:ring-accent/20 p-6 text-base font-sans resize-none outline-none transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="absolute bottom-6 right-6 bg-accent text-white px-6 py-3 hover:bg-ink transition-colors flex items-center gap-2 text-sm font-bold shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>处理中...</span>
                </>
              ) : (
                <>
                  <span>发送指令</span>
                  <Send size={18} />
                </>
              )}
            </button>
          </div>

          <div className="mt-6">
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-3">示例提示词 (Example Prompts)</div>
            <div className="space-y-2">
              {examplePrompts.map((p, i) => (
                <button
                  key={i}
                  onClick={() => setInput(p)}
                  disabled={isLoading}
                  className="block text-[11px] text-ink/40 hover:text-accent transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  • {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right: 3D Exhibition Placeholder */}
      <div className="w-full lg:flex-1 relative flex items-center justify-center bg-[#0F0F0F] overflow-hidden min-h-[400px] lg:min-h-0">
        <div className="architectural-grid absolute inset-0 opacity-10" />

        <div className="relative z-10 text-center px-12">
          <motion.div
            animate={{
              rotateY: [0, 360],
              rotateX: [0, 10, 0]
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="w-64 h-64 border border-white/10 mx-auto mb-12 flex items-center justify-center relative"
          >
            <Box size={80} className="text-white/20" strokeWidth={1} />
            <div className="absolute inset-0 border border-accent/20 scale-110 animate-pulse" />
            <div className="absolute inset-0 border border-white/5 -rotate-12" />

            {/* Status Label */}
            <div className={cn(
              "absolute -bottom-4 left-1/2 -translate-x-1/2 px-3 py-1 text-[8px] font-mono text-white uppercase tracking-widest whitespace-nowrap",
              isLoading ? "bg-yellow-600" : "bg-accent"
            )}>
              {isLoading ? 'Processing...' : 'Ready'}
            </div>
          </motion.div>

          <h3 className="text-white/80 text-xl font-bold mb-4 tracking-tight">3D 实时预览空间</h3>
          <p className="text-white/30 text-sm max-w-sm mx-auto leading-relaxed mb-8">
            {currentProgress || '等待输入设计简报...'}
          </p>

          <div className="flex items-center justify-center gap-8">
            <div className={cn(
              "text-center",
              isLoading ? "opacity-100" : "opacity-30"
            )}>
              <div className="text-white/10 mb-2"><Database size={20} className="mx-auto" /></div>
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">Context Sync</div>
            </div>
            <div className={cn(
              "text-center",
              isLoading ? "opacity-100" : "opacity-30"
            )}>
              <div className="text-white/10 mb-2"><Cpu size={20} className="mx-auto" /></div>
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">GPU Compute</div>
            </div>
            <div className={cn(
              "text-center",
              isLoading ? "opacity-100" : "opacity-30"
            )}>
              <div className="text-white/10 mb-2"><Sparkles size={20} className="mx-auto" /></div>
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">RT Rendering</div>
            </div>
          </div>
        </div>

        {/* Floating Labels */}
        <div className="absolute top-10 right-10 text-right">
          <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-1">Viewport: Perspective</div>
          <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">Grid: 1.0m</div>
          <div className={cn(
            "mt-4 px-2 py-1 border text-[8px] font-mono uppercase tracking-widest",
            isLoading ? "border-yellow-500/50 text-yellow-400" : "border-white/10 text-white/40"
          )}>
            {isLoading ? 'Processing' : 'Backend Ready'}
          </div>
        </div>

        <div className="absolute bottom-10 left-10 flex items-center gap-4">
          <div className="w-32 h-px bg-white/10" />
          <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest">
            Pal 3D Agent Connected
          </span>
        </div>
      </div>
    </div>
  );
}
