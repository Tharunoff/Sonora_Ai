import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket(url) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log('🔗 IntentCast WebSocket Connected');
      setIsConnected(true);
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };

    ws.current.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        try {
          const text = await event.data.text();
          const parsed = JSON.parse(text);
          setLastMessage(parsed);
        } catch {
          setLastMessage({ type: 'audio', blob: event.data });
        }
      } else if (typeof event.data === 'string') {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch (e) {
          console.warn('[WS] Unparseable message:', event.data);
        }
      }
    };

    ws.current.onclose = () => {
      console.log('🔴 IntentCast WebSocket Disconnected. Retrying in 2s...');
      setIsConnected(false);
      reconnectTimeout.current = setTimeout(connect, 2000); // Auto-reconnect
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
      ws.current.close();
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [connect]);

  const sendPayload = useCallback((payload) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      if (payload instanceof Blob) {
        ws.current.send(payload);
      } else {
        ws.current.send(JSON.stringify(payload));
      }
    } else {
      console.warn("Attempted to send payload, but WebSocket is not open.");
    }
  }, []);

  return { isConnected, sendPayload, lastMessage, wsRef: ws };
}
