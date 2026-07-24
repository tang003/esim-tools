import { api } from './client';

export async function sendMfa(sessionId: string, channel: 'TEXT' | 'EMAIL'): Promise<{ ref: string; message: string }> {
  const { data } = await api.post('/api/mfa/send', { sessionId, channel });
  return data;
}

export async function verifyMfa(sessionId: string, ref: string, code: string): Promise<void> {
  await api.post('/api/mfa/verify', { sessionId, ref, code });
}

