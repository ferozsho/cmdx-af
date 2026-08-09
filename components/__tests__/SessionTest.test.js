import { render, screen } from '@testing-library/react';
import SessionTest from '../SessionTest';

describe('SessionTest Component', () => {
  test('renders session context correctly', () => {
    render(<SessionTest />);
    expect(screen.getByText(/session context/i)).toBeInTheDocument();
  });

  test('displays user ID from context', () => {
    render(<SessionTest />);
    expect(screen.getByText(/user id: 123/i)).toBeInTheDocument();
  });

  test('displays role from context', () => {
    render(<SessionTest />);
    expect(screen.getByText(/role: admin/i)).toBeInTheDocument();
  });
});
