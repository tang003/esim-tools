import { api } from './client';

export interface EsimItem {
  itemId: string;
  ssn?: string;
  ssnMasked: string;
}

export interface FetchEsimResponse {
  ok: boolean;
  status: 'READY' | 'NEED_SELECTION';
  items: EsimItem[];
  lpaString?: string;
  phoneNumber?: string;
  memberName?: string;
  memberId?: string;
  phoneNumberMasked?: string;
  memberNameMasked?: string;
  memberIdMasked?: string;
  simStatus?: string;
  esimCount?: number;
}

export async function fetchEsim(sessionId: string): Promise<FetchEsimResponse> {
  const { data } = await api.post('/api/esim/fetch', { sessionId });
  return data;
}

export async function downloadToken(sessionId: string, itemId: string): Promise<{ lpaString: string; ssn?: string; ssnMasked: string }> {
  const { data } = await api.post('/api/esim/download-token', { sessionId, itemId });
  return data;
}

export async function reserveNewEsim(
  sessionId: string
): Promise<{ lpaString: string; ssn?: string; ssnMasked: string; deliveryStatus?: string; reservationEndDate?: string }> {
  const { data } = await api.post('/api/esim/reserve-new', { sessionId });
  return data;
}
