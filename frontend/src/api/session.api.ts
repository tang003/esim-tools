import { api } from './client';

export async function clearSession(sessionId: string): Promise<void> {
  await api.delete(`/api/session/${sessionId}`);
}
