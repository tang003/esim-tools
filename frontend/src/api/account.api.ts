import { api } from './client';

export interface AccountLoginResponse {
  ok: boolean;
  status: 'READY' | 'MFA_REQUIRED';
  sessionId: string;
  message: string;
  memberName?: string;
  phoneNumber?: string;
  memberId?: string;
  maskedAccount?: string;
  phoneNumberMasked?: string;
}

export interface AccountLoginChallengeResponse {
  ok: boolean;
  message: string;
  channel: 'TEXT' | 'EMAIL';
}

export async function accountLogin(memberName: string, password: string): Promise<AccountLoginResponse> {
  const { data } = await api.post('/api/account/login', { memberName, password });
  return data;
}

export async function sendAccountLoginChallenge(
  sessionId: string,
  channel: 'TEXT' | 'EMAIL'
): Promise<AccountLoginChallengeResponse> {
  const { data } = await api.post('/api/account/login/challenge', { sessionId, channel });
  return data;
}

export async function accountLoginMfa(
  sessionId: string,
  code: string,
  rememberBrowser: boolean
): Promise<AccountLoginResponse> {
  const { data } = await api.post('/api/account/login/mfa', { sessionId, code, rememberBrowser });
  return data;
}
