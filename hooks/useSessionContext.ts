import { useState, useEffect, useCallback } from 'react';

export interface SessionContext {
  sessionId: string;
  userId: string;
  createdAt: string;
  lastActive: string;
  metadata: Record<string, unknown>;
}

export function useSessionContext(initialContext?: Partial<SessionContext>) {
  const [context, setContext] = useState<SessionContext>({
    sessionId: '',
    userId: '',
    createdAt: '',
    lastActive: '',
    metadata: {},
    ...initialContext,
  });
  const [trackingEnabled, setTrackingEnabled] = useState<boolean>(true);

  const updateLastActive = useCallback(() => {
    if (!trackingEnabled) return;
    setContext((prev) => ({
      ...prev,
      lastActive: new Date().toISOString(),
    }));
  }, [trackingEnabled]);

  useEffect(() => {
    if (!trackingEnabled) return;
    const interval = setInterval(updateLastActive, 5000);
    return () => clearInterval(interval);
  }, [trackingEnabled, updateLastActive]);

  const startSession = useCallback(() => {
    const newContext: SessionContext = {
      sessionId: `session-${Date.now()}`,
      userId: `user-${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date().toISOString(),
      lastActive: new Date().toISOString(),
      metadata: { source: 'manual-start' },
    };
    setContext(newContext);
  }, []);

  const toggleTracking = useCallback(() => {
    setTrackingEnabled((prev) => !prev);
  }, []);

  const updateMetadata = useCallback((key: string, value: unknown) => {
    setContext((prev) => ({
      ...prev,
      metadata: { ...prev.metadata, [key]: value },
    }));
  }, []);

  return {
    context,
    trackingEnabled,
    startSession,
    toggleTracking,
    updateMetadata,
  };
}
