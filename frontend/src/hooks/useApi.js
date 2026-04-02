import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useApi(endpoint, interval = null) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const prevDataRef = useRef(null);

  const fetch = useCallback(async () => {
    try {
      const res = await axios.get(`${API}${endpoint}`);
      prevDataRef.current = data;
      setData(res.data);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    fetch();
    if (interval) {
      const id = setInterval(fetch, interval);
      return () => clearInterval(id);
    }
  }, [fetch, interval]);

  return { data, loading, error, refetch: fetch, prevData: prevDataRef.current };
}

export async function postApi(endpoint, body = {}) {
  const res = await axios.post(`${API}${endpoint}`, body);
  return res.data;
}
