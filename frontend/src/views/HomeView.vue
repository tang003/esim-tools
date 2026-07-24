<script setup lang="ts">
import { computed, ref } from 'vue';
import { useEsimStore } from '../stores/esim.store';

const store = useEsimStore();
store.restoreSession();
const memberName = ref('');
const password = ref('');
const accountMfaCode = ref('');
const mfaCode = ref('');

const activeStep = computed(() => {
  if (store.step === 'account' || store.step === 'accountMfa') return 1;
  if (store.step === 'fetch' || store.step === 'mfa') return 2;
  return 3;
});

function downloadQr() {
  if (!store.qrDataUrl) return;
  const link = document.createElement('a');
  link.href = store.qrDataUrl;
  link.download = 'giffgaff-esim-qr.png';
  link.click();
}

async function copyLpa() {
  if (store.lpaString) await navigator.clipboard.writeText(store.lpaString);
}

function confirmReserveNew() {
  const ok = window.confirm('申请新的 eSIM 可能会触发 giffgaff 重新下发 eSIM，请确认这是你要做的操作。');
  if (ok) store.startReserveNew();
}
</script>

<template>
  <main class="min-h-screen bg-[#f4f7fb] text-ink">
    <div class="mx-auto max-w-5xl px-5 py-10">
      <header class="mb-8 text-center">
        <div class="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
          <span class="text-xl">▯</span>
        </div>
        <h1 class="text-4xl font-black tracking-normal md:text-5xl">eSIM 获取工具</h1>
        <p class="mt-3 text-base text-slate-600">获取已有二维码全天可用；申请新的 eSIM 建议在中国时间 11:30 至次日 04:30 操作。</p>
      </header>

      <section class="mb-7 grid grid-cols-3 gap-3">
        <div v-for="step in [1, 2, 3]" :key="step" class="rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200">
          <div class="flex items-center gap-3">
            <div class="grid h-10 w-10 place-items-center rounded-full font-black" :class="activeStep >= step ? 'bg-gold text-white' : 'bg-white text-ink ring-2 ring-gold'">
              {{ step }}
            </div>
            <span class="font-bold">
              {{ step === 1 ? '账号登录' : step === 2 ? '获取eSIM' : '二维码' }}
            </span>
          </div>
        </div>
      </section>

      <p v-if="store.error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
        {{ store.error }}
      </p>

      <section v-if="store.step === 'account'" class="panel">
        <div class="panel-head">第一步：账号登录</div>
        <div class="panel-body space-y-5">
          <div>
            <label class="mb-3 block font-bold">手机号 / 会员名 / 邮箱</label>
            <input v-model="memberName" class="input" autocomplete="username" placeholder="输入 giffgaff 账号" />
          </div>
          <div>
            <label class="mb-3 block font-bold">密码</label>
            <input v-model="password" class="input" type="password" autocomplete="current-password" placeholder="输入密码" />
          </div>
          <button class="primary-btn" :disabled="store.loading || memberName.length < 2 || !password" @click="store.accountLogin(memberName, password)">
            {{ store.loading ? '登录中...' : '登录 giffgaff' }}
          </button>
          <p class="text-sm text-slate-600">密码仅用于本次登录请求；如需验证码，会在后端 Redis 临时会话中保存 15 分钟，完成登录后清空。</p>
        </div>
      </section>

      <section v-if="store.step === 'accountMfa'" class="panel">
        <div class="panel-head">第一步：登录验证码</div>
        <div class="panel-body space-y-5">
          <p class="rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-800">
            giffgaff 要求二次验证。请先选择邮箱或短信发送验证码，再输入收到的验证码继续登录。
          </p>
          <div>
            <label class="mb-2 block font-bold">验证码接收方式</label>
            <select v-model="store.accountMfaChannel" class="input">
              <option value="EMAIL">邮箱 EMAIL</option>
              <option value="TEXT">短信 TEXT</option>
            </select>
          </div>
          <button class="secondary-btn" :disabled="store.loading || !store.sessionId" @click="store.sendAccountLoginChallenge">
            {{ store.loading ? '发送中...' : store.accountMfaSent ? '重新发送验证码' : '发送验证码' }}
          </button>
          <p v-if="store.accountMfaMessage" class="rounded-lg bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
            {{ store.accountMfaMessage }}
          </p>
          <div>
            <label class="mb-3 block font-bold">验证码</label>
            <input v-model="accountMfaCode" class="input" maxlength="10" placeholder="输入验证码" />
          </div>
          <label class="flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input v-model="store.rememberBrowser" type="checkbox" class="h-4 w-4" />
            记住此浏览器
          </label>
          <button class="primary-btn" :disabled="store.loading || !store.accountMfaSent || accountMfaCode.length < 4" @click="store.accountLoginMfa(accountMfaCode)">
            {{ store.loading ? '验证中...' : '验证并继续' }}
          </button>
        </div>
      </section>

      <section v-if="false && store.step === 'accountMfa'" class="panel">
        <div class="panel-head">第一步：输入登录验证码</div>
        <div class="panel-body space-y-5">
          <p class="rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-800">giffgaff 要求二次验证。请输入你收到的邮箱或短信验证码。</p>
          <div>
            <label class="mb-3 block font-bold">验证码</label>
            <input v-model="accountMfaCode" class="input" maxlength="10" placeholder="输入验证码" />
          </div>
          <label class="flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input v-model="store.rememberBrowser" type="checkbox" class="h-4 w-4" />
            记住此浏览器
          </label>
          <button class="primary-btn" :disabled="store.loading || accountMfaCode.length < 4" @click="store.accountLoginMfa(accountMfaCode)">
            {{ store.loading ? '验证中...' : '验证并继续' }}
          </button>
        </div>
      </section>

      <section v-if="store.step === 'fetch'" class="panel">
        <div class="panel-head">第二步：获取 eSIM</div>
        <div class="panel-body space-y-5">
          <div v-if="false" class="rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
            <p v-if="store.maskedAccount"><strong>账号：</strong>{{ store.maskedAccount }}</p>
            <p v-if="store.phoneNumberMasked"><strong>号码：</strong>{{ store.phoneNumberMasked }}</p>
            <p v-if="!store.canDirectFetch" class="mt-2 text-amber-700">登录已完成，但可能缺少完整访问令牌。如果获取失败，请重新登录后再试。</p>
          </div>
          <div class="overflow-hidden rounded-lg border border-slate-200 bg-white text-sm">
            <div class="grid gap-0 divide-y divide-slate-100">
              <div class="grid grid-cols-[92px_1fr] items-center gap-3 px-4 py-3">
                <span class="font-semibold text-slate-500">用户名</span>
                <span class="font-bold text-slate-900">{{ store.memberName || store.maskedAccount || '已登录' }}</span>
              </div>
              <div class="grid grid-cols-[92px_1fr] items-center gap-3 px-4 py-3">
                <span class="font-semibold text-slate-500">会员 ID</span>
                <span class="font-bold text-slate-900">{{ store.memberId || store.memberIdMasked || '获取 eSIM 后显示' }}</span>
              </div>
              <div class="grid grid-cols-[92px_1fr] items-center gap-3 px-4 py-3">
                <span class="font-semibold text-slate-500">手机号</span>
                <span class="font-bold text-slate-900">{{ store.phoneNumber || store.phoneNumberMasked || '获取 eSIM 后显示' }}</span>
              </div>
              <div class="grid grid-cols-[92px_1fr] items-center gap-3 px-4 py-3">
                <span class="font-semibold text-slate-500">SIM 状态</span>
                <span class="font-bold text-slate-900">{{ store.simStatus || '待查询' }}</span>
              </div>
              <div class="grid grid-cols-[92px_1fr] items-center gap-3 px-4 py-3">
                <span class="font-semibold text-slate-500">eSIM 数量</span>
                <span class="font-bold text-slate-900">{{ store.esimCount || store.items.length || '待查询' }}</span>
              </div>
            </div>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <button class="primary-btn" :disabled="store.loading" @click="store.fetchEsim">
              {{ store.loading && store.pendingAction === 'fetchOld' ? '获取中...' : '获取已有 eSIM 二维码' }}
            </button>
            <button class="secondary-btn" :disabled="store.loading" @click="confirmReserveNew">
              {{ store.loading && store.pendingAction === 'reserveNew' ? '申请中...' : '申请新的 eSIM 二维码' }}
            </button>
          </div>

          <div v-if="store.pendingAction === 'reserveNew' && !store.lpaString" class="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p class="text-sm font-semibold text-amber-800">
              申请新的 eSIM 前，giffgaff 可能会要求再次验证；建议在中国时间 11:30 至次日 04:30 操作。验证码由 giffgaff 发送到账号绑定的邮箱或手机号，不是通过 eSIM 卡发送。
            </p>
            <div class="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
              <select v-model="store.mfaChannel" class="input">
                <option value="EMAIL">邮箱 EMAIL</option>
                <option value="TEXT">短信 TEXT</option>
              </select>
              <button class="secondary-btn" :disabled="store.loading" @click="store.sendMfa">
                {{ store.loading ? '发送中...' : store.mfaRef ? '重新发送验证码' : '发送验证码' }}
              </button>
            </div>
            <div v-if="store.mfaRef" class="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
              <input v-model="mfaCode" class="input" maxlength="10" placeholder="输入收到的验证码" />
              <button class="primary-btn" :disabled="store.loading || mfaCode.length < 4" @click="store.verifyMfa(mfaCode)">
                验证并申请
              </button>
            </div>
          </div>

          <div v-if="store.items.length > 1" class="rounded-lg border border-slate-200 bg-white p-4">
            <label class="mb-2 block font-bold">选择 eSIM</label>
            <select v-model="store.selectedItemId" class="input">
              <option v-for="item in store.items" :key="item.itemId" :value="item.itemId">{{ item.ssn || item.ssnMasked }}</option>
            </select>
            <button class="secondary-btn mt-4" :disabled="store.loading || !store.selectedItemId" @click="store.downloadSelected">
              获取所选 eSIM 二维码
            </button>
          </div>

          <div v-if="store.lpaString" class="rounded-lg border border-slate-200 bg-white p-5">
            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="text-lg font-black text-slate-900">
                  {{ store.resultMode === 'new' ? '新的 eSIM 二维码' : '已有 eSIM 二维码' }}
                </p>
                <p class="mt-1 text-sm font-semibold text-slate-500">SSN：{{ store.ssnMasked }}</p>
              </div>
              <span v-if="store.resultMode === 'new' && store.reserveStatus" class="rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700">
                {{ store.reserveStatus }}
              </span>
            </div>
            <div class="grid gap-6 md:grid-cols-[320px_1fr]">
              <div class="text-center">
                <img :src="store.qrDataUrl" alt="eSIM QR Code" class="mx-auto h-64 w-64 rounded-lg border border-slate-100" />
                <p v-if="store.reservationEndDate" class="mt-3 text-sm font-semibold text-slate-500">
                  预留有效期：{{ store.reservationEndDate }}
                </p>
              </div>
              <div class="space-y-4">
                <label class="block font-bold">LPA 字符串</label>
                <textarea readonly class="input min-h-36 font-mono text-sm" :value="store.lpaString"></textarea>
                <div class="flex flex-wrap gap-3">
                  <button class="primary-btn" @click="copyLpa">复制 LPA</button>
                  <button class="secondary-btn" @click="downloadQr">下载二维码</button>
                  <button class="danger-btn" @click="store.clear">退出登录</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="store.step === 'mfa'" class="panel">
        <div class="panel-head">备用验证：giffgaff 要求二次验证</div>
        <div class="panel-body space-y-5">
          <div>
            <label class="mb-2 block font-bold">验证码接收方式</label>
            <select v-model="store.mfaChannel" class="input">
              <option value="TEXT">短信 TEXT</option>
              <option value="EMAIL">邮箱 EMAIL</option>
            </select>
          </div>
          <button class="secondary-btn" :disabled="store.loading" @click="store.sendMfa">
            {{ store.loading ? '发送中...' : '发送验证码' }}
          </button>
          <div v-if="store.mfaRef">
            <label class="mb-2 block font-bold">验证码</label>
            <input v-model="mfaCode" class="input" maxlength="10" placeholder="输入收到的验证码" />
            <button class="primary-btn mt-4" :disabled="store.loading || mfaCode.length < 4" @click="store.verifyMfa(mfaCode)">
              验证并继续获取
            </button>
          </div>
        </div>
      </section>

      <section v-if="store.step === 'result'" class="panel">
        <div class="panel-head">第三步：eSIM 二维码</div>
        <div class="panel-body">
          <div class="grid gap-6 md:grid-cols-[320px_1fr]">
            <div class="rounded-lg bg-white p-5 text-center ring-1 ring-slate-200">
              <img :src="store.qrDataUrl" alt="eSIM QR Code" class="mx-auto h-64 w-64" />
              <p class="mt-3 text-sm font-semibold text-slate-600">SSN：{{ store.ssnMasked }}</p>
            </div>
            <div class="space-y-4">
              <label class="block font-bold">LPA 字符串</label>
              <textarea readonly class="input min-h-36 font-mono text-sm" :value="store.lpaString"></textarea>
              <div class="flex flex-wrap gap-3">
                <button class="primary-btn" @click="copyLpa">复制 LPA</button>
                <button class="secondary-btn" @click="downloadQr">下载二维码</button>
                <button class="danger-btn" @click="store.clear">清除会话</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer class="mt-8 text-center text-sm text-slate-600">
        获取已有 eSIM 二维码不受服务窗口限制且不换卡；申请新的 eSIM 会调用 giffgaff 新 eSIM 下发流程，操作前请确认当前号码确实需要重新下发。
      </footer>
    </div>
  </main>
</template>
