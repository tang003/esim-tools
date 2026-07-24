import { defineStore } from 'pinia';
import { accountLogin, accountLoginMfa, sendAccountLoginChallenge } from '../api/account.api';
import { getErrorCode, getErrorMessage } from '../api/client';
import { clearSession } from '../api/session.api';
import { downloadToken, EsimItem, fetchEsim, reserveNewEsim } from '../api/esim.api';
import { sendMfa, verifyMfa } from '../api/mfa.api';
import { toQrDataUrl } from '../utils/qrcode';

type Step = 'account' | 'accountMfa' | 'fetch' | 'mfa' | 'result';
type PendingAction = '' | 'fetchOld' | 'reserveNew';

const SESSION_STORAGE_KEY = 'giffgaff_esim_session_v1';
const SESSION_TTL_MS = 24 * 60 * 60 * 1000;

interface PersistedSession {
  expiresAt: number;
  step: Step;
  sessionId: string;
  memberName: string;
  phoneNumber: string;
  memberId: string;
  maskedAccount: string;
  phoneNumberMasked: string;
  memberIdMasked: string;
  simStatus: string;
  esimCount: number;
  sessionExpiresAt: number;
  canDirectFetch: boolean;
  accountMfaChannel: 'TEXT' | 'EMAIL';
  accountMfaSent: boolean;
  accountMfaMessage: string;
  mfaChannel: 'TEXT' | 'EMAIL';
  mfaRef: string;
  items: EsimItem[];
  selectedItemId: string;
  pendingAction: PendingAction;
}

export const useEsimStore = defineStore('esim', {
  state: () => ({
    step: 'account' as Step,
    loading: false,
    error: '',
    sessionId: '',
    memberName: '',
    phoneNumber: '',
    memberId: '',
    maskedAccount: '',
    phoneNumberMasked: '',
    memberIdMasked: '',
    simStatus: '',
    esimCount: 0,
    sessionExpiresAt: 0,
    canDirectFetch: false,
    items: [] as EsimItem[],
    selectedItemId: '',
    lpaString: '',
    ssnMasked: '',
    qrDataUrl: '',
    mfaRef: '',
    mfaChannel: 'EMAIL' as 'TEXT' | 'EMAIL',
    accountMfaChannel: 'EMAIL' as 'TEXT' | 'EMAIL',
    accountMfaSent: false,
    accountMfaMessage: '',
    pendingAction: '' as PendingAction,
    resultMode: '' as '' | 'old' | 'new',
    reserveStatus: '',
    reservationEndDate: '',
    rememberBrowser: false
  }),
  actions: {
    persistSession() {
      if (!this.sessionId) return;
      const payload: PersistedSession = {
        expiresAt: Date.now() + SESSION_TTL_MS,
        step: this.step === 'result' ? 'fetch' : this.step,
        sessionId: this.sessionId,
        memberName: this.memberName,
        phoneNumber: this.phoneNumber,
        memberId: this.memberId,
        maskedAccount: this.maskedAccount,
        phoneNumberMasked: this.phoneNumberMasked,
        memberIdMasked: this.memberIdMasked,
        simStatus: this.simStatus,
        esimCount: this.esimCount,
        sessionExpiresAt: this.sessionExpiresAt || Date.now() + SESSION_TTL_MS,
        canDirectFetch: this.canDirectFetch,
        accountMfaChannel: this.accountMfaChannel,
        accountMfaSent: this.accountMfaSent,
        accountMfaMessage: this.accountMfaMessage,
        mfaChannel: this.mfaChannel,
        mfaRef: this.mfaRef,
        items: this.items,
        selectedItemId: this.selectedItemId,
        pendingAction: this.pendingAction
      };
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload));
    },
    restoreSession() {
      const raw = localStorage.getItem(SESSION_STORAGE_KEY);
      if (!raw) return;
      try {
        const payload = JSON.parse(raw) as PersistedSession;
        if (!payload.sessionId || payload.expiresAt <= Date.now()) {
          localStorage.removeItem(SESSION_STORAGE_KEY);
          return;
        }
        this.step = payload.step;
        this.sessionId = payload.sessionId;
        this.memberName = payload.memberName || '';
        this.phoneNumber = payload.phoneNumber || '';
        this.memberId = payload.memberId || '';
        this.maskedAccount = payload.maskedAccount || '';
        this.phoneNumberMasked = payload.phoneNumberMasked || '';
        this.memberIdMasked = payload.memberIdMasked || '';
        this.simStatus = payload.simStatus || '';
        this.esimCount = payload.esimCount || 0;
        this.sessionExpiresAt = payload.sessionExpiresAt || payload.expiresAt;
        this.canDirectFetch = Boolean(payload.canDirectFetch);
        this.accountMfaChannel = payload.accountMfaChannel || 'EMAIL';
        this.accountMfaSent = Boolean(payload.accountMfaSent);
        this.accountMfaMessage = payload.accountMfaMessage || '';
        this.mfaChannel = payload.mfaChannel || 'EMAIL';
        this.mfaRef = payload.mfaRef || '';
        this.items = payload.items || [];
        this.selectedItemId = payload.selectedItemId || '';
        this.pendingAction = payload.pendingAction || '';
        this.error = '';
        this.loading = false;
      } catch {
        localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    },
    clearPersistedSession() {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    },
    async accountLogin(memberName: string, password: string) {
      this.loading = true;
      this.error = '';
      try {
        const result = await accountLogin(memberName, password);
        this.sessionId = result.sessionId;
        this.memberName = result.memberName || memberName;
        this.phoneNumber = result.phoneNumber || '';
        this.memberId = result.memberId || '';
        this.maskedAccount = result.maskedAccount || '';
        this.phoneNumberMasked = result.phoneNumberMasked || '';
        this.sessionExpiresAt = Date.now() + SESSION_TTL_MS;
        this.canDirectFetch = result.status === 'READY';
        this.accountMfaSent = false;
        this.accountMfaMessage = '';
        this.step = result.status === 'MFA_REQUIRED' ? 'accountMfa' : 'fetch';
        this.persistSession();
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async sendAccountLoginChallenge() {
      this.loading = true;
      this.error = '';
      try {
        const result = await sendAccountLoginChallenge(this.sessionId, this.accountMfaChannel);
        this.accountMfaSent = true;
        this.accountMfaMessage = result.message;
        this.persistSession();
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async accountLoginMfa(code: string) {
      this.loading = true;
      this.error = '';
      try {
        const result = await accountLoginMfa(this.sessionId, code, this.rememberBrowser);
        this.memberName = result.memberName || this.memberName;
        this.phoneNumber = result.phoneNumber || this.phoneNumber;
        this.memberId = result.memberId || this.memberId;
        this.maskedAccount = result.maskedAccount || this.maskedAccount;
        this.phoneNumberMasked = result.phoneNumberMasked || this.phoneNumberMasked;
        this.sessionExpiresAt = Date.now() + SESSION_TTL_MS;
        this.canDirectFetch = true;
        this.step = 'fetch';
        this.persistSession();
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async fetchEsim() {
      this.loading = true;
      this.error = '';
      this.pendingAction = 'fetchOld';
      try {
        const result = await fetchEsim(this.sessionId);
        this.items = result.items;
        this.phoneNumber = result.phoneNumber || this.phoneNumber;
        this.memberName = result.memberName || this.memberName;
        this.memberId = result.memberId || this.memberId;
        this.phoneNumberMasked = result.phoneNumberMasked || this.phoneNumberMasked;
        this.maskedAccount = result.memberNameMasked || this.maskedAccount;
        this.memberIdMasked = result.memberIdMasked || this.memberIdMasked;
        this.simStatus = result.simStatus || this.simStatus;
        this.esimCount = result.esimCount ?? result.items.length;
        if (result.status === 'READY' && result.lpaString) {
          this.resultMode = 'old';
          await this.setResult(result.lpaString, result.items[0]?.ssn || result.items[0]?.ssnMasked || '');
        } else {
          this.selectedItemId = result.items[0]?.itemId || '';
          this.persistSession();
        }
      } catch (error) {
        const code = getErrorCode(error);
        if (code === 'MFA_REQUIRED') {
          this.step = 'fetch';
          this.error = '';
        } else {
          this.error = getErrorMessage(error);
        }
      } finally {
        this.loading = false;
      }
    },
    async downloadSelected() {
      this.loading = true;
      this.error = '';
      try {
        const result = await downloadToken(this.sessionId, this.selectedItemId);
        this.resultMode = 'old';
        await this.setResult(result.lpaString, result.ssn || result.ssnMasked);
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async sendMfa() {
      this.loading = true;
      this.error = '';
      try {
        const result = await sendMfa(this.sessionId, this.mfaChannel);
        this.mfaRef = result.ref;
        this.persistSession();
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async verifyMfa(code: string) {
      this.loading = true;
      this.error = '';
      try {
        await verifyMfa(this.sessionId, this.mfaRef, code);
        if (this.pendingAction === 'reserveNew') {
          await this.reserveNew();
        } else {
          await this.fetchEsim();
        }
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async setResult(lpa: string, ssn: string) {
      this.lpaString = lpa;
      this.ssnMasked = ssn;
      this.qrDataUrl = await toQrDataUrl(lpa);
      this.step = 'fetch';
      this.persistSession();
    },
    async startReserveNew() {
      this.pendingAction = 'reserveNew';
      this.resultMode = '';
      this.lpaString = '';
      this.ssnMasked = '';
      this.qrDataUrl = '';
      this.reserveStatus = '';
      this.reservationEndDate = '';
      this.mfaChannel = 'EMAIL';
      this.mfaRef = '';
      this.error = '';
      this.step = 'fetch';
      this.persistSession();
    },
    async reserveNew() {
      this.loading = true;
      this.error = '';
      try {
        const result = await reserveNewEsim(this.sessionId);
        this.resultMode = 'new';
        this.reserveStatus = result.deliveryStatus || '';
        this.reservationEndDate = result.reservationEndDate || '';
        await this.setResult(result.lpaString, result.ssn || result.ssnMasked);
      } catch (error) {
        const code = getErrorCode(error);
        if (code === 'MFA_REQUIRED') {
          this.pendingAction = 'reserveNew';
          this.error = '';
        } else {
          this.error = getErrorMessage(error);
        }
      } finally {
        this.loading = false;
      }
    },
    async clear() {
      if (this.sessionId) {
        await clearSession(this.sessionId).catch(() => undefined);
      }
      this.clearPersistedSession();
      this.$reset();
    }
  }
});
