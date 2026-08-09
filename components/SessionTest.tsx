import React, { useState, useEffect, useCallback } from 'react';

interface SessionContext {
  sessionId: string;
  userId: string;
  createdAt: string;
  lastActive: string;
  metadata: Record<string, unknown>;
}

interface SessionTestProps {
  initialContext?: Partial<SessionContext>;
}

const SessionTest: React.FC<SessionTestProps> = ({ initialContext }) => {
  const [context, setContext] = useState<SessionContext>({
    sessionId: '',
    userId: '',
    createdAt: '',
    lastActive: '',
    metadata: {},
    ...initialContext,
  });
  const [trackingEnabled, setTrackingEnabled] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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

  const handleStartSession = () => {
    try {
      const newContext: SessionContext = {
        sessionId: `session-${Date.now()}`,
        userId: `user-${Math.random().toString(36).substr(2, 9)}`,
        createdAt: new Date().toISOString(),
        lastActive: new Date().toISOString(),
        metadata: { source: 'manual-start' },
      };
      setContext(newContext);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    }
  };

  const handleToggleTracking = () => {
    setTrackingEnabled((prev) => !prev);
  };

  const handleUpdateMetadata = (key: string, value: unknown) => {
    setContext((prev) => ({
      ...prev,
      metadata: { ...prev.metadata, [key]: value },
    }));
  };

  return (
    <div className="session-test">
      <h2>Session Context Tracking</h2>
      <div className="controls">
        <button onClick={handleStartSession}>Start New Session</button>
        <button onClick={handleToggleTracking}>
          {trackingEnabled ? 'Disable Tracking' : 'Enable Tracking'}
        </button>
      </div>
      {error && <div className="error">Error: {error}</div>}
      <div className="context-display">
        <h3>Current Context</h3>
        <p><strong>Session ID:</strong> {context.sessionId || 'N/A'}</p>
        <p><strong>User ID:</strong> {context.userId || 'N/A'}</p>
        <p><strong>Created At:</strong> {context.createdAt || 'N/A'}</p>
        <p><strong>Last Active:</strong> {context.lastActive || 'N/A'}</p>
        <div>
          <strong>Metadata:</strong>
          <pre>{JSON.stringify(context.metadata, null, 2)}</pre>
        </div>
      </div>
      <div className="metadata-update">
        <h3>Update Metadata</h3>
        <button onClick={() => handleUpdateMetadata('lastAction', `click-${Date.now()}`)}>
          Add Last Action
        </button>
        <button onClick={() => handleUpdateMetadata('page', window.location.pathname)}>
          Add Current Page
        </button>
      </div>
    </div>
  );
};

export default SessionTest;
