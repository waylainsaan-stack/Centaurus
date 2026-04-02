import React, { useState } from "react";
import { Brain } from "lucide-react";
import { postApi, useApi } from "@/hooks/useApi";

export default function LSTMPanel({ lstm: externalLstm, currentSignal, symbol }) {
  const [training, setTraining] = useState(false);
  const [trainError, setTrainError] = useState(null);

  // Use own fetch for LSTM status so we can refetch after training
  const { data: lstmData, refetch: refetchLstm } = useApi(`/lstm/status?symbol=${encodeURIComponent(symbol)}`, 10000);

  const lstm = lstmData || externalLstm;
  const trained = lstm?.trained || false;
  const prediction = lstm?.prediction || currentSignal?.lstm || {};

  const trainModel = async () => {
    setTraining(true);
    setTrainError(null);
    try {
      const result = await postApi(`/lstm/train?symbol=${encodeURIComponent(symbol)}`);
      if (result.status === "failed") {
        setTrainError("Training failed - not enough data");
      }
      // Refetch status to show updated model
      await refetchLstm();
    } catch (e) {
      setTrainError(e.message || "Training failed");
    } finally {
      setTraining(false);
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
        <button data-testid="train-lstm-button" onClick={trainModel} disabled={training} className="btn-terminal text-xs">
          {training ? 'TRAINING...' : trained ? 'RETRAIN' : 'TRAIN'}
        </button>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2" style={{ background: training ? '#FDE047' : trained ? '#00FF41' : '#FF003C', animation: training ? 'pulse-dot 1s ease-in-out infinite' : 'none' }} />
        <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#a1a1aa' }}>
          {training ? 'TRAINING ON 500 CANDLES...' : trained ? 'MODEL READY' : 'NOT TRAINED'}
        </span>
      </div>

      {/* Error */}
      {trainError && (
        <div className="text-xs font-mono mb-3 p-2" style={{ color: '#FF003C', background: 'rgba(255,0,60,0.1)', border: '1px solid #FF003C' }}>
          ERR: {trainError}
        </div>
      )}

      {trained && (
        <>
          {/* Direction prediction */}
          <div className="text-center py-3 mb-3" style={{ background: '#000', border: '1px solid #27272a' }}>
            <div className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>PREDICTED DIRECTION</div>
            <div className="text-2xl font-heading font-black mt-1" style={{ color: dirColor }}>
              {direction}
            </div>
            {changePct !== 0 && (
              <div className="text-sm font-mono mt-1" style={{ color: dirColor }}>
                {changePct > 0 ? '+' : ''}{changePct.toFixed(4)}%
              </div>
            )}
          </div>

          {/* Confidence bar */}
          <div className="mb-3">
            <div className="flex justify-between mb-1">
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>CONFIDENCE</span>
              <span className="text-xs font-mono font-bold" style={{ color: dirColor }}>{confidence}%</span>
            </div>
            <div className="h-2 w-full" style={{ background: '#18181b' }}>
              <div className="h-full" style={{ width: `${Math.min(confidence, 100)}%`, background: dirColor }} />
            </div>
          </div>

          {/* Predicted price */}
          {predPrice && (
            <div className="flex justify-between py-2" style={{ borderTop: '1px solid #27272a' }}>
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>PREDICTED PRICE</span>
              <span className="text-xs font-mono font-bold" style={{ color: '#fafafa' }}>${predPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
          )}

          {/* Signal */}
          <div className="flex justify-between py-2" style={{ borderTop: '1px solid #27272a' }}>
            <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>LSTM SIGNAL</span>
            <span className="text-xs font-mono font-bold" style={{ color: dirColor }}>{prediction.signal || 'HOLD'}</span>
          </div>
        </>
      )}

      {!trained && !training && (
        <div className="text-xs font-mono py-4 text-center" style={{ color: '#52525b' }}>
          Click TRAIN to initialize the LSTM model with historical data.
          The model learns from 500 candles of OHLCV data.
        </div>
      )}
    </div>
  );
}
