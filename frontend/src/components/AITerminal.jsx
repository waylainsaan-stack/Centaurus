import React, { useState } from "react";
import { Zap } from "lucide-react";
import { postApi } from "@/hooks/useApi";

export default function AITerminal({ insights, currentSignal }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [latestResult, setLatestResult] = useState(null);

  const triggerAnalysis = async () => {
    setAnalyzing(true);
    try {
      const result = await postApi("/ai/analyze");
      setLatestResult(result);
    } catch (e) {
      setLatestResult({ error: e.message });
    } finally {
      setAnalyzing(false);
    }
  };

  const allInsights = insights?.insights || [];
  const aiInsight = currentSignal?.ai_insight;

  return (
    <div data-testid="ai-terminal" className="p-4 md:p-6" style={{ background: '#000' }}>
      <div className="flex items-center justify-between mb-4">
        <h3
          className="font-heading text-base font-bold uppercase tracking-widest"
          style={{ color: '#a1a1aa' }}
        >
          AI MARKET ANALYSIS
        </h3>
        <button
          data-testid="trigger-ai-analysis"
          onClick={triggerAnalysis}
          disabled={analyzing}
          className="btn-terminal flex items-center gap-2"
        >
          <Zap size={12} />
          {analyzing ? 'ANALYZING...' : 'ANALYZE NOW'}
        </button>
      </div>

      {/* Terminal output area */}
      <div
        data-testid="ai-terminal-log"
        className="overflow-y-auto"
        style={{
          maxHeight: 280,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '12px',
          lineHeight: '1.6',
        }}
      >
        {/* Latest manual analysis result */}
        {latestResult && !latestResult.error && (
          <div className="mb-3 animate-in">
            <span style={{ color: '#00FF41' }}>$ ai_analyze --model=gpt-5.2</span>
            <div className="mt-1 pl-2" style={{ borderLeft: '2px solid #00FF41' }}>
              <div className="flex items-center gap-2 mb-1">
                <span style={{ color: '#52525b' }}>[SIGNAL]</span>
                <span style={{ color: latestResult.signal === 'BUY' ? '#00FF41' : latestResult.signal === 'SELL' ? '#FF003C' : '#FDE047' }}>
                  {latestResult.signal}
                </span>
                <span style={{ color: '#52525b' }}>@ ${latestResult.price?.toLocaleString()}</span>
              </div>
              <div style={{ color: '#a1a1aa' }}>{latestResult.insight}</div>
            </div>
          </div>
        )}

        {latestResult?.error && (
          <div className="mb-3 animate-in">
            <span style={{ color: '#FF003C' }}>ERR: {latestResult.error}</span>
          </div>
        )}

        {/* Current bot AI insight */}
        {aiInsight && (
          <div className="mb-3">
            <span style={{ color: '#52525b' }}>[LATEST BOT INSIGHT]</span>
            <div className="mt-1" style={{ color: '#fafafa' }}>{aiInsight}</div>
          </div>
        )}

        {/* Historical insights */}
        {allInsights.map((ins, i) => (
          <div key={i} className="mb-2" style={{ borderBottom: '1px solid #0A0A0A', paddingBottom: 8 }}>
            <div className="flex items-center gap-2">
              <span style={{ color: '#52525b' }}>
                {new Date(ins.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span style={{ color: ins.signal === 'BUY' ? '#00FF41' : ins.signal === 'SELL' ? '#FF003C' : '#FDE047' }}>
                [{ins.signal}]
              </span>
              <span style={{ color: '#52525b' }}>@ ${ins.price?.toLocaleString()}</span>
            </div>
            <div className="mt-1" style={{ color: '#a1a1aa' }}>{ins.insight}</div>
          </div>
        ))}

        {/* Empty state */}
        {allInsights.length === 0 && !aiInsight && !latestResult && (
          <div>
            <span style={{ color: '#52525b' }}>$ awaiting_analysis...</span>
            <div className="mt-2" style={{ color: '#a1a1aa' }}>
              Start the bot or click ANALYZE NOW for GPT-5.2 market insights.
            </div>
          </div>
        )}

        {/* Cursor */}
        <span className="cursor-blink" style={{ color: '#00FF41' }}>_</span>
      </div>
    </div>
  );
}
