<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import type { Component } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import {
  Calendar,
  Connection,
  DataAnalysis,
  Files,
  Key,
  Lock,
  Message,
  Operation,
  Tickets,
  User,
  Grid,
} from "@element-plus/icons-vue";

import { post } from "@/shared/api/client";

type ModuleCard = {
  title: string;
  description: string;
  icon: Component;
  accent: string;
};

const router = useRouter();
const activeTab = ref("login");
const loading = ref(false);
const codeLoading = ref(false);

const loginForm = reactive({
  username: "",
  password: "",
  remember_me: true,
});

const registerForm = reactive({
  username: "",
  password: "",
  email: "",
  verification_code: "",
  business_line: "",
});

const moduleCards: ModuleCard[] = [
  {
    title: "工具平台",
    description: "接口工具、工具卡片与常用调试能力的统一入口。",
    icon: Grid,
    accent: "59, 130, 246",
  },
  {
    title: "需求协同",
    description: "需求管理、故事管理与迭代流转的协同工作台。",
    icon: Tickets,
    accent: "37, 99, 235",
  },
  {
    title: "测试中心",
    description: "测试数据、用例、缺陷与自动化能力的一体化空间。",
    icon: Files,
    accent: "14, 165, 233",
  },
  {
    title: "调度任务",
    description: "统一管理定时任务、自动化调度与平台级执行策略。",
    icon: Operation,
    accent: "16, 185, 129",
  },
  {
    title: "迭代计划",
    description: "按日期组织版本节奏，关联需求、故事与测试资产。",
    icon: Calendar,
    accent: "99, 102, 241",
  },
  {
    title: "数据服务",
    description: "数据查询与分析服务入口，沉淀配置驱动的数据能力。",
    icon: DataAnalysis,
    accent: "6, 182, 212",
  },
];

const loginReady = computed(() => {
  return Boolean(loginForm.username.trim() && loginForm.password.trim());
});

const registerReady = computed(() => {
  return Boolean(
    registerForm.username.trim() &&
      registerForm.password.trim() &&
      registerForm.email.trim() &&
      registerForm.verification_code.trim(),
  );
});

const sendCodeDisabled = computed(() => {
  return !registerForm.email.trim() || codeLoading.value || loading.value;
});

const passwordStrength = computed(() => {
  const password = registerForm.password.trim();
  let score = 0;

  if (password.length >= 6) score += 1;
  if (/[A-Z]/.test(password) || /[a-z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password) || password.length >= 10) score += 1;

  if (!password) {
    return { level: 0, label: "未设置", tip: "建议至少 6 位，包含字母与数字。" };
  }

  if (score <= 2) {
    return { level: 1, label: "基础", tip: "建议补充数字或特殊字符，提升安全性。" };
  }

  if (score === 3) {
    return { level: 2, label: "良好", tip: "当前强度可用，适合日常账号注册。" };
  }

  return { level: 3, label: "较强", tip: "强度较好，适合长期使用。" };
});

async function onLogin() {
  if (!loginReady.value) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }

  loading.value = true;
  try {
    await post("/api/auth/login/", loginForm);
    ElMessage.success("登录成功");
    router.push("/");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function sendCode() {
  if (sendCodeDisabled.value) {
    ElMessage.warning("请先填写邮箱地址");
    return;
  }

  codeLoading.value = true;
  try {
    const data = await post<{ debug_code?: string; sent: boolean }>("/api/auth/verification-code/", {
      email: registerForm.email,
    });

    if (data.debug_code) {
      ElMessage.success(`验证码已生成，调试码：${data.debug_code}`);
      return;
    }

    ElMessage.success(data.sent ? "验证码已发送，请检查邮箱" : "验证码已生成，请检查邮件配置");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    codeLoading.value = false;
  }
}

async function onRegister() {
  if (!registerReady.value) {
    ElMessage.warning("请先完整填写注册信息");
    return;
  }

  loading.value = true;
  try {
    await post("/api/auth/register/", registerForm);
    ElMessage.success("注册成功，请使用新账号登录");
    Object.assign(registerForm, {
      username: "",
      password: "",
      email: "",
      verification_code: "",
      business_line: "",
    });
    activeTab.value = "login";
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <section class="hero-panel">
      <div class="hero-copy">
        <h1>质量管理平台</h1>
        <p>围绕需求、测试、调度与数据协同，构建更清晰、更稳定的质量工作入口。</p>
      </div>

      <div class="module-grid">
        <article
          v-for="item in moduleCards"
          :key="item.title"
          class="module-card"
          :style="{ '--accent-rgb': item.accent }"
        >
          <div class="module-card__head">
            <div class="module-icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
          </div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="auth-panel">
      <div class="auth-shell">
        <el-card class="form-card" shadow="never">
          <el-tabs v-model="activeTab" stretch>
            <el-tab-pane label="登录" name="login">
              <el-form class="inline-form" label-width="82px" @submit.prevent="onLogin">
                <el-form-item label="用户名">
                  <el-input
                    v-model="loginForm.username"
                    clearable
                    placeholder="请输入用户名"
                    size="large"
                  >
                    <template #prefix>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <el-form-item label="密码">
                  <el-input
                    v-model="loginForm.password"
                    type="password"
                    show-password
                    placeholder="请输入密码"
                    size="large"
                  >
                    <template #prefix>
                      <el-icon><Lock /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <div class="form-foot">
                  <el-checkbox v-model="loginForm.remember_me">7 天内保持登录</el-checkbox>
                  <span class="hint-text">
                    {{ loginReady ? "信息已就绪，可直接进入平台" : "请输入账号与密码" }}
                  </span>
                </div>

                <el-button
                  type="primary"
                  :loading="loading"
                  :disabled="!loginReady"
                  class="submit-btn"
                  @click="onLogin"
                >
                  登录并进入平台
                </el-button>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="注册" name="register">
              <el-form class="inline-form" label-width="82px" @submit.prevent="onRegister">
                <el-form-item label="用户名">
                  <el-input
                    v-model="registerForm.username"
                    clearable
                    placeholder="请输入用户名"
                    size="large"
                  >
                    <template #prefix>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <el-form-item label="邮箱">
                  <el-input
                    v-model="registerForm.email"
                    clearable
                    placeholder="请输入邮箱地址"
                    size="large"
                  >
                    <template #prefix>
                      <el-icon><Message /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <el-form-item label="验证码">
                  <div class="code-row">
                    <el-input
                      v-model="registerForm.verification_code"
                      clearable
                      placeholder="请输入验证码"
                      size="large"
                    >
                      <template #prefix>
                        <el-icon><Connection /></el-icon>
                      </template>
                    </el-input>
                    <el-button
                      class="code-btn"
                      :loading="codeLoading"
                      :disabled="sendCodeDisabled"
                      @click="sendCode"
                    >
                      发送验证码
                    </el-button>
                  </div>
                </el-form-item>

                <el-form-item label="密码">
                  <div class="password-field">
                    <el-input
                      v-model="registerForm.password"
                      type="password"
                      show-password
                      placeholder="至少 6 位字符"
                      size="large"
                    >
                      <template #prefix>
                        <el-icon><Key /></el-icon>
                      </template>
                    </el-input>

                    <div class="strength-panel" :data-level="passwordStrength.level">
                      <div class="strength-bars">
                        <span :class="{ active: passwordStrength.level >= 1 }" />
                        <span :class="{ active: passwordStrength.level >= 2 }" />
                        <span :class="{ active: passwordStrength.level >= 3 }" />
                      </div>
                      <div class="strength-copy">
                        <strong>密码强度 {{ passwordStrength.label }}</strong>
                        <span>{{ passwordStrength.tip }}</span>
                      </div>
                    </div>
                  </div>
                </el-form-item>

                <el-form-item label="业务线">
                  <el-input
                    v-model="registerForm.business_line"
                    clearable
                    placeholder="例如：支付、会员、基础服务"
                    size="large"
                  >
                    <template #prefix>
                      <el-icon><Tickets /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <el-button
                  type="primary"
                  :loading="loading"
                  :disabled="!registerReady"
                  class="submit-btn"
                  @click="onRegister"
                >
                  注册账号
                </el-button>
              </el-form>
            </el-tab-pane>
          </el-tabs>

          <div class="auth-footnote">默认管理员账号：admin / admin123</div>
        </el-card>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.56fr) minmax(420px, 468px);
  column-gap: 88px;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 16%, rgba(93, 167, 255, 0.14), transparent 26%),
    radial-gradient(circle at 76% 14%, rgba(125, 211, 252, 0.08), transparent 20%),
    linear-gradient(135deg, #f8fbff 0%, #eef4fb 44%, #f9fbfe 100%);
}

.login-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.3), transparent 74%);
  pointer-events: none;
}

.login-page::after {
  content: "";
  position: absolute;
  top: 7%;
  left: 8%;
  width: 480px;
  height: 480px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(96, 165, 250, 0.12), transparent 70%);
  filter: blur(48px);
  pointer-events: none;
}

.hero-panel,
.auth-panel {
  position: relative;
  z-index: 1;
}

.hero-panel {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 50px;
  height: 100vh;
  overflow: hidden;
  padding: 88px 0 56px 78px;
}

.hero-copy {
  max-width: 760px;
}

.hero-copy h1 {
  margin: 0;
  color: #0f172a;
  font-size: 68px;
  font-weight: 700;
  letter-spacing: -0.045em;
  line-height: 1.02;
}

.hero-copy p {
  margin: 24px 0 0;
  max-width: 620px;
  color: #526079;
  font-size: 20px;
  line-height: 1.95;
}

.module-grid {
  display: grid;
  width: 100%;
  max-width: 1160px;
  grid-template-columns: repeat(3, minmax(268px, 1fr));
  gap: 24px;
  align-content: start;
}

.module-card {
  position: relative;
  min-height: 236px;
  padding: 28px 28px 26px;
  border: 1px solid rgba(var(--accent-rgb), 0.1);
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.74)),
    rgba(255, 255, 255, 0.72);
  box-shadow:
    0 20px 48px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(18px);
  transition:
    transform 0.26s ease,
    box-shadow 0.26s ease,
    border-color 0.26s ease;
  overflow: hidden;
}

.module-card::before {
  content: "";
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, rgba(var(--accent-rgb), 0.72), rgba(var(--accent-rgb), 0));
}

.module-card::after {
  content: "";
  position: absolute;
  top: -48px;
  right: -44px;
  width: 168px;
  height: 168px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--accent-rgb), 0.14), transparent 68%);
  pointer-events: none;
}

.module-card:hover {
  transform: translateY(-8px);
  border-color: rgba(var(--accent-rgb), 0.22);
  box-shadow:
    0 28px 60px rgba(15, 23, 42, 0.1),
    0 0 0 1px rgba(var(--accent-rgb), 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.module-card__head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.module-icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border: 1px solid rgba(var(--accent-rgb), 0.12);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(var(--accent-rgb), 0.16), rgba(255, 255, 255, 0.82)),
    rgba(255, 255, 255, 0.8);
  color: rgb(var(--accent-rgb));
  font-size: 24px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.84),
    0 10px 18px rgba(var(--accent-rgb), 0.08);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease;
}

.module-card:hover .module-icon {
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 14px 26px rgba(var(--accent-rgb), 0.14);
}

.module-card strong {
  display: block;
  margin-top: 26px;
  color: #0f172a;
  font-size: 23px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.38;
}

.module-card p {
  margin: 18px 0 0;
  color: #5f6f89;
  font-size: 16px;
  line-height: 2.05;
}

.auth-panel {
  display: flex;
  align-items: stretch;
  justify-content: center;
  height: 100vh;
  min-height: 100vh;
  padding: 0;
}

.auth-shell {
  box-sizing: border-box;
  position: relative;
  width: 100%;
  max-width: none;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  padding: 272px 28px 20px 0;
}

.auth-shell::before {
  content: "";
  position: absolute;
  inset: 0 0 0 0;
  border-left: 1px solid rgba(148, 163, 184, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(247, 250, 252, 0.92)),
    rgba(255, 255, 255, 0.84);
  box-shadow: -18px 0 42px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(22px);
  pointer-events: none;
}

.form-card {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  overflow: hidden;
}

.form-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  height: 100%;
  min-height: 0;
  padding: 20px 48px 24px;
}

.form-card :deep(.el-tabs) {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
}

.form-card :deep(.el-tabs__content) {
  min-height: 454px;
}

.form-card :deep(.el-tab-pane) {
  min-height: 100%;
}

.form-card :deep(.el-tabs__nav-wrap) {
  padding: 4px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.08);
}

.form-card :deep(.el-tabs__nav-wrap::after),
.form-card :deep(.el-tabs__active-bar) {
  display: none;
}

.form-card :deep(.el-tabs__header) {
  margin-bottom: 28px;
}

.form-card :deep(.el-tabs__nav) {
  width: 100%;
}

.form-card :deep(.el-tabs__item) {
  height: 44px;
  border-radius: 12px;
  color: #64748b;
  font-size: 15px;
  font-weight: 600;
  transition:
    color 0.22s ease,
    background-color 0.22s ease,
    box-shadow 0.22s ease;
}

.form-card :deep(.el-tabs__item.is-active) {
  color: #0f172a;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.inline-form {
  margin-top: 2px;
}

.form-card :deep(.el-form-item) {
  align-items: flex-start;
  margin-bottom: 18px;
}

.form-card :deep(.el-form-item__label) {
  justify-content: flex-start;
  align-items: center;
  min-height: 48px;
  padding-right: 14px;
  color: #475569;
  font-size: 14px;
  font-weight: 500;
}

.form-card :deep(.el-form-item__content) {
  min-height: 48px;
}

.form-card :deep(.el-input) {
  width: 100%;
}

.form-card :deep(.el-input__wrapper) {
  min-height: 48px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 0 0 1px rgba(148, 163, 184, 0.14) inset,
    0 4px 12px rgba(148, 163, 184, 0.04);
  transition:
    box-shadow 0.22s ease,
    transform 0.22s ease,
    background-color 0.22s ease;
}

.form-card :deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 0 0 1px rgba(96, 165, 250, 0.2) inset,
    0 8px 18px rgba(37, 99, 235, 0.05);
}

.form-card :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 1);
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(59, 130, 246, 0.28) inset,
    0 0 0 4px rgba(59, 130, 246, 0.06),
    0 10px 18px rgba(37, 99, 235, 0.06);
}

.form-card :deep(.el-input__prefix-inner) {
  color: #94a3b8;
}

.form-card :deep(.el-input__inner::placeholder) {
  color: #a0aec0;
}

.password-field {
  width: 100%;
}

.strength-panel {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.strength-bars {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.strength-bars span {
  height: 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.22);
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.strength-bars span.active {
  background: #3b82f6;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.05);
}

.strength-panel[data-level="1"] .strength-bars span.active {
  background: #f59e0b;
}

.strength-panel[data-level="2"] .strength-bars span.active {
  background: #3b82f6;
}

.strength-panel[data-level="3"] .strength-bars span.active {
  background: #10b981;
}

.strength-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.strength-copy strong {
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
}

.strength-copy span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.form-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 8px 0 22px 82px;
}

.hint-text {
  color: #94a3b8;
  font-size: 12px;
}

.code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 126px;
  gap: 12px;
  width: 100%;
}

.code-btn {
  height: 48px;
  border-radius: 14px;
  border-color: rgba(59, 130, 246, 0.14);
  background: rgba(255, 255, 255, 0.94);
  color: #2563eb;
  font-weight: 600;
}

.code-btn:hover {
  border-color: rgba(59, 130, 246, 0.24);
  background: rgba(239, 246, 255, 0.96);
}

.submit-btn {
  width: calc(100% - 82px);
  margin-left: 82px;
  min-height: 50px;
  border: none;
  border-radius: 15px;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 62%, #4f9cff 100%);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.2);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    opacity 0.22s ease;
}

.submit-btn:not(.is-disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.24);
}

.submit-btn:deep(span) {
  letter-spacing: 0.03em;
}

.auth-footnote {
  margin-top: auto;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.14);
  color: #7c8aa5;
  font-size: 13px;
}

@media (max-width: 1600px) {
  .hero-copy h1 {
    font-size: 60px;
  }

  .module-grid {
    max-width: 980px;
    grid-template-columns: repeat(2, minmax(320px, 1fr));
  }
}

@media (max-width: 1320px) {
  .login-page {
    height: auto;
    grid-template-columns: 1fr;
    column-gap: 0;
  }

  .hero-panel {
    gap: 38px;
    padding: 42px 32px 24px;
  }

  .hero-copy h1 {
    font-size: 52px;
  }

  .auth-panel {
    height: auto;
    min-height: auto;
    padding: 0 32px 40px;
  }

  .auth-shell {
    max-width: 560px;
    height: auto;
    min-height: auto;
    overflow: visible;
    padding: 32px 0 0;
  }

  .auth-shell::before {
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 28px;
    box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  }

  .form-card {
    height: auto;
    min-height: auto;
  }

  .form-card :deep(.el-card__body) {
    height: auto;
    min-height: auto;
    padding: 52px 34px 28px;
  }

  .form-card :deep(.el-tabs__content) {
    min-height: 430px;
  }
}

@media (max-width: 960px) {
  .hero-panel {
    height: auto;
    overflow: visible;
    padding: 26px 16px 18px;
  }

  .hero-copy h1 {
    font-size: 40px;
  }

  .hero-copy p {
    font-size: 16px;
  }

  .module-grid {
    max-width: none;
    grid-template-columns: 1fr;
  }

  .module-card {
    min-height: 208px;
  }

  .auth-panel {
    padding: 0 16px 16px;
  }

  .form-card :deep(.el-form-item) {
    align-items: stretch;
  }

  .form-card :deep(.el-form-item__label) {
    min-height: auto;
    padding-bottom: 6px;
  }

  .form-card :deep(.el-card__body),
  .form-card :deep(.el-tabs__content) {
    min-height: auto;
  }

  .form-foot,
  .submit-btn {
    width: 100%;
    margin-left: 0;
  }

  .form-foot {
    align-items: flex-start;
    flex-direction: column;
  }

  .code-row,
  .strength-panel {
    grid-template-columns: 1fr;
  }
}
</style>
