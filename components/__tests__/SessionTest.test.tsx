import { render, screen, fireEvent } from '@testing-library/react';
import SessionTest from '../SessionTest';
import { useSessionContext } from '../../hooks/useSessionContext';

jest.mock('../../hooks/useSessionContext');

const mockUseSessionContext = useSessionContext as jest.MockedFunction<typeof useSessionContext>;

beforeEach(() => {
  mockUseSessionContext.mockReturnValue({
    data: {},
    setData: jest.fn(),
    clear: jest.fn(),
  });
});

describe('SessionTest component', () => {
  test('renders session data', () => {
    mockUseSessionContext.mockReturnValue({
      data: { user: 'Alice' },
      setData: jest.fn(),
      clear: jest.fn(),
    });
    render(<SessionTest />);
    expect(screen.getByText(/user/i)).toBeInTheDocument();
    expect(screen.getByText(/Alice/i)).toBeInTheDocument();
  });

  test('calls setData when button clicked', () => {
    const setData = jest.fn();
    mockUseSessionContext.mockReturnValue({
      data: {},
      setData,
      clear: jest.fn(),
    });
    render(<SessionTest />);
    fireEvent.click(screen.getByRole('button', { name: /set data/i }));
    expect(setData).toHaveBeenCalled();
  });

  test('calls clear when clear button clicked', () => {
    const clear = jest.fn();
    mockUseSessionContext.mockReturnValue({
      data: { user: 'Alice' },
      setData: jest.fn(),
      clear,
    });
    render(<SessionTest />);
    fireEvent.click(screen.getByRole('button', { name: /clear/i }));
    expect(clear).toHaveBeenCalled();
  });

  test('displays empty state when no data', () => {
    render(<SessionTest />);
    expect(screen.getByText(/no session data/i)).toBeInTheDocument();
  });
});
