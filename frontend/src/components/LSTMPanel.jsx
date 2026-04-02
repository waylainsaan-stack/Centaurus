import React, { useState, useEffect, useRef } from "react";
import { Brain } from "lucide-react";
import { postApi, useApi } from "@/hooks/useApi";

export default function LSTMPanel({ currentSignal, symbol }) {
  const [trainError, setTrainError] = useState(null);
  const pollRef = useRef(null);

  // Poll LSTM status - faster when training
  const { data: lstmData, refetch: refetchLstm } = useApi(`/lstm/status?symbol=${encodeURIComponent(symbol)}`, 3000);

  const trained = lstmData?.trained || false;
  const isTraining = lstmData?.training || false;
  const prediction = lstmData?.prediction || currentSignal?.lstm || {};

  // Stop polling fast once training completes
  useEffect(() => {
    if (isTraining) {
      pollRef.current = setInterval(refetchLstm, 2000);
      return () => clearInterval(pollRef.current);
    }
  }, [isTraining, refetchLstm]);

  const trainModel = async () => {
    setTrainError(null);
    try {
      const result = await postApi(`/lstm/train?symbol=${encodeURIComponent(symbol)}`);
      if (result.status === "already_training") {
        return; // Already training
      }
      // Immediately refetch to show training state
      setTimeout(refetchLstm, 500);
    } catch (e) {
      setTrainError(e.message || "Failed to start training");
    }
  };

  const direction = prediction.predicted_direction || "NEUTRAL";
  const confidence = prediction.confidence || 0;
  const changePct = prediction.predicted_change_pct || 0;
  const predPrice = prediction.predicted_price;

  const dirColor = direction === "UP" ? '#00FF41' : direction === "DOWN" ? '#FF003C' : '#FDE047';

  return (
    <div data-testid="lstm-panel" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-heading text-base font-bold uppercase tracking-widest flex items-center gap-2" style={{ color: '#a1a1aa' }}>
          <Brain size={16} /> LSTM MODEL
        </h3>
        <button data-testid="train-lstm-button" onClick={trainModel} disabled={isTraining} className="btn-terminal text-xs">
          {isTraining ? 'TRAINING...' : trained ? 'RETRAIN' : 'TRAIN'}
        </button>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2" style={{ background: isTraining ? '#FDE047' : trained ? '#00FF41' : '#FF003C', animation: isTraining ? 'pulse-dot 1s ease-in-out infinite' : 'none' }} />
        <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#a1a1aa' }}>
          {isTraining ? 'TRAINING ON 500 CANDLES...' : trained ? 'MODEL READY' : 'NOT TRAINED'}
        </span>
      </div>

      {/* Error */}
      {trainError && (
        <div className="text-xs font-mono mb-3 p-2" style={{ color: '#FF003C', background: 'rgba(255,0,60,0.1)', border: '1px solid #FF003C' }}>
          ERR: {trainError}
        </div>
      )}

      {trained && !isTraining && (
        <>
          <div className="text-center py-3 mb-3" style={{ background: '#000', border: '1px solid #27272a' }}>
            <div className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>PREDICTED DIRECTION</div>
            <div className="text-2xl font-heading font-black mt-1" style={{ color: dirColor }}>{direction}</div>
            {changePct !== 0 && (
              <div className="text-sm font-mono mt-1" style={{ color: dirColor }}>{changePct > 0 ? '+' : ''}{changePct.toFixed(4)}%</div>
            )}
          </div>

          <div className="mb-3">
            <div className="flex justify-between mb-1">
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>CONFIDENCE</span>
              <span className="text-xs font-mono font-bold" style={{ color: dirColor }}>{confidence}%</span>
            </div>
            <div className="h-2 w-full" style={{ background: '#18181b' }}>
              <div className="h-full" style={{ width: `${Math.min(confidence, 100)}%`, background: dirColor }} />
            </div>
          </div>

          {predPrice && (
            <div className="flex justify-between py-2" style={{ borderTop: '1px solid #27272a' }}>
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>PREDICTED PRICE</span>
              <span className="text-xs font-mono font-bold" style={{ color: '#fafafa' }}>${predPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
          )}

          <div className="flex justify-between py-2" style={{ borderTop: '1px solid #27272a' }}>
            <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>LSTM SIGNAL</span>
            <span className="text-xs font-mono font-bold" style={{ color: dirColor }}>{prediction.signal || 'HOLD'}</span>
          </div>
        </>
      )}

      {!trained && !isTraining && (
        <div className="text-xs font-mono py-4 text-center" style={{ color: '#52525b' }}>
          Click TRAIN to initialize the LSTM model with historical data.
        </div>
      )}
    </div>
  );
}
