import React, { useState, useEffect } from 'react';

interface SessionTestProps {
  initialCount?: number;
}

const SessionTest: React.FC<SessionTestProps> = ({ initialCount = 0 }) => {
  const [count, setCount] = useState<number>(initialCount);
  const [sessionId, setSessionId] = useState<string>('');

  useEffect(() => {
    // Generate a session ID on mount to simulate context tracking
    const id = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(id);
  }, []);

  const increment = () => setCount(prev => prev + 1);
  const decrement = () => setCount(prev => prev - 1);
  const reset = () => setCount(initialCount);

  return (
    <div className="session-test">
      <h2>Session Test Component</h2>
      <p>Session ID: <span data-testid="session-id">{sessionId}</span></p>
      <p>Count: <span data-testid="count">{count}</span></p>
      <button onClick={increment} data-testid="increment">Increment</button>
      <button onClick={decrement} data-testid="decrement">Decrement</button>
      <button onClick={reset} data-testid="reset">Reset</button>
    </div>
  );
};

export default SessionTest;
