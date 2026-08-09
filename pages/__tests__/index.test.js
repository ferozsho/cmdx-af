import { render, screen } from '@testing-library/react';
import Home from '../index';

describe('Home Page', () => {
  test('renders SessionTest component', () => {
    render(<Home />);
    expect(screen.getByTestId('session-test')).toBeInTheDocument();
  });

  test('renders main heading', () => {
    render(<Home />);
    expect(screen.getByRole('heading', { name: /welcome/i })).toBeInTheDocument();
  });
});
