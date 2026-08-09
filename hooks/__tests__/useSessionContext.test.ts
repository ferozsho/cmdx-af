import { renderHook, act } from '@testing-library/react';
import { useSessionContext } from '../useSessionContext';

describe('useSessionContext', () => {
  test('initializes with empty data', () => {
    const { result } = renderHook(() => useSessionContext());
    expect(result.current.data).toEqual({});
  });

  test('setData updates data', () => {
    const { result } = renderHook(() => useSessionContext());
    act(() => {
      result.current.setData({ user: 'Alice' });
    });
    expect(result.current.data).toEqual({ user: 'Alice' });
  });

  test('clear resets data', () => {
    const { result } = renderHook(() => useSessionContext());
    act(() => {
      result.current.setData({ user: 'Alice' });
    });
    act(() => {
      result.current.clear();
    });
    expect(result.current.data).toEqual({});
  });
});
