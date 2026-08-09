import { render, screen } from '@testing-library/react';
import SessionTestPage from '../session-test';

jest.mock('../../components/SessionTest', () => () => <div>Mocked SessionTest</div>);

describe('SessionTestPage', () => {
  test('renders the page with heading', () => {
    render(<SessionTestPage />);
    expect(screen.getByRole('heading', { name: /session test/i })).toBeInTheDocument();
  });

  test('renders the SessionTest component', () => {
    render(<SessionTestPage />);
    expect(screen.getByText('Mocked SessionTest')).toBeInTheDocument();
  });
});
