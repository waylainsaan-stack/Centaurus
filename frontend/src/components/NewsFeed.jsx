import React, { useState } from "react";
import { Newspaper, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { postApi } from "@/hooks/useApi";

export default function NewsFeed({ news, sentiment, symbol }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const articles = news?.articles || [];

  const analyzeNow = async () => {
    setAnalyzing(true);
    try {
      const res = await postApi(`/news/analyze?symbol=${encodeURIComponent(symbol)}`);
      setResult(res);
    } catch (e) {
      setResult({ error: e.message });
    }
    setAnalyzing(false);
  };

  const sentimentData = result?.sentiment || sentiment || {};
  const sentColor = sentimentData.sentiment === 'BULLISH' ? '#00FF41' : sentimentData.sentiment === 'BEARISH' ? '#FF003C' : '#FDE047';
  const SentIcon = sentimentData.sentiment === 'BULLISH' ? TrendingUp : sentimentData.sentiment === 'BEARISH' ? TrendingDown : Minus;

  return (
    <div data-testid="news-feed" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-heading text-base font-bold uppercase tracking-widest flex items-center gap-2" style={{ color: '#a1a1aa' }}>
          <Newspaper size={16} /> LIVE NEWS
        </h3>
        <button data-testid="analyze-news-button" onClick={analyzeNow} disabled={analyzing} className="btn-terminal text-xs">
          {analyzing ? 'ANALYZING...' : 'ANALYZE SENTIMENT'}
        </button>
      </div>

      {/* Sentiment bar */}
      {sentimentData.sentiment && (
        <div className="mb-4 p-3" style={{ background: '#000', border: `1px solid ${sentColor}` }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SentIcon size={16} style={{ color: sentColor }} />
              <span className="text-sm font-mono font-bold uppercase" style={{ color: sentColor }}>
                {sentimentData.sentiment}
              </span>
            </div>
            <span className="text-xs font-mono" style={{ color: sentColor }}>
              SCORE: {sentimentData.score || 0}
            </span>
          </div>
          {sentimentData.summary && (
            <div className="text-xs font-mono mt-2" style={{ color: '#a1a1aa' }}>
              {sentimentData.summary}
            </div>
          )}
          <div className="flex justify-between mt-2">
            <span className="text-xs font-mono" style={{ color: '#52525b' }}>SIGNAL:</span>
            <span className="text-xs font-mono font-bold" style={{ color: sentColor }}>
              {sentimentData.signal || 'HOLD'}
            </span>
          </div>
        </div>
      )}

      {/* News articles */}
      <div className="overflow-y-auto" style={{ maxHeight: 250 }}>
        {articles.length === 0 && (
          <div className="text-xs font-mono py-4 text-center" style={{ color: '#52525b' }}>
            Loading news from CryptoPanic, CoinDesk, CoinTelegraph...
          </div>
        )}
        {articles.map((article, i) => (
          <a
            key={i}
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className="block py-2 px-2 transition-colors duration-75 table-row"
            style={{ borderBottom: '1px solid #18181b', textDecoration: 'none' }}
          >
            <div className="flex items-start gap-2">
              <span className="text-xs font-mono shrink-0 mt-0.5 px-1" style={{ background: '#18181b', color: '#52525b' }}>
                {article.source?.slice(0, 4)?.toUpperCase()}
              </span>
              <div>
                <div className="text-xs font-mono leading-relaxed" style={{ color: '#a1a1aa' }}>
                  {article.title}
                </div>
                {article.published && (
                  <span className="text-xs font-mono" style={{ color: '#52525b' }}>
                    {new Date(article.published).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
