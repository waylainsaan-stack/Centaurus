import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export function useApi(endpoint, interval = null) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const endpointRef = useRef(endpoint);

  // Reset data immediately when endpoint changes
  useEffect(() => {
    if (endpointRef.current !== endpoint) {
      endpointRef.current = endpoint;
      setData(null);
      setLoading(true);
    }
  }, [endpoint]);

  const fetchData = useCallback(async () => {
    try {
      const res = await axios.get(`${API}${endpoint}`);
      // Only set data if this is still the current endpoint
      if (endpointRef.current === endpoint) {
        setData(res.data);
        setError(null);
      }
    } catch (e) {
      if (endpointRef.current === endpoint) {
        setError(e.message);
      }
    } finally {
      if (endpointRef.current === endpoint) {
        setLoading(false);
      }
    }
  }, [endpoint]);

  useEffect(() => {
    fetchData();
    if (interval) {
      const id = setInterval(fetchData, interval);
      return () => clearInterval(id);
    }
  }, [fetchData, interval]);

  return { data, loading, error, refetch: fetchData };
}

export async function postApi(endpoint, body = {}) {
  const res = await axios.post(`${API}${endpoint}`, body);
  return res.data;
}

export async function deleteApi(endpoint) {
  const res = await axios.delete(`${API}${endpoint}`);
  return res.data;
}

export function useWebSocket() {
  const [lastMessage, setLastMessage] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  const connect = useCallback(() => {
    const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws';
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        ws.send(JSON.stringify({ action: "ping" }));
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type !== 'pong') {
            setLastMessage(data);
          }
        } catch {}
      };
      ws.onclose = () => {
        setConnected(false);
        reconnectRef.current = setTimeout(connect, 5000);
      };
      ws.onerror = () => {
        ws.close();
      };
    } catch {}
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connect]);

  return { lastMessage, connected };
}
