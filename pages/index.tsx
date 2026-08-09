import React from 'react';
import SessionTest from '../components/SessionTest';

const HomePage: React.FC = () => {
  return (
    <div>
      <h1>Session Context Tracking Test</h1>
      <SessionTest initialCount={5} />
    </div>
  );
};

export default HomePage;
