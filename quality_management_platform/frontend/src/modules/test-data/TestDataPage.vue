<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import {
  fetchTestDataMeta,
  generateEnterpriseWorkspace,
  generateUserWorkspace,
  refreshEnterpriseField,
  refreshUserField,
} from "./api";
import TestDataEnterpriseConfigPanel from "./components/TestDataEnterpriseConfigPanel.vue";
import TestDataResultPanel from "./components/TestDataResultPanel.vue";
import TestDataUserConfigPanel from "./components/TestDataUserConfigPanel.vue";
import type {
  EnterpriseWorkspace,
  ResultSection,
  TestDataConfig,
  TestDataMeta,
  UserWorkspace,
} from "./types";

const fallbackConfig: TestDataConfig = {
  mode: "id_number",
  min_age: 22,
  max_age: 55,
  age: "",
  id_number: "",
  name: "",
  gender: "male",
  ethnic_group: "random",
  id_prefix: "random",
  phone: "",
  bank_name: "建设银行",
  card_type: "debit",
  bank_card: "",
  company_type: "random",
  company_name: "",
  credit_code: "",
  legal_representative: "",
  address: "",
  registered_capital: "",
  establish_date: "",
  business_start_date: "",
  business_end_date: "",
  business_scope: "",
  industry_type: "random",
};

const meta = ref<TestDataMeta | null>(null);
const booting = ref(true);
const userLoading = ref(false);
const enterpriseLoading = ref(false);
const userDetailVisible = ref(false);
const enterpriseDetailVisible = ref(false);

const userForm = reactive<TestDataConfig>({ ...fallbackConfig });
const enterpriseForm = reactive<TestDataConfig>({ ...fallbackConfig });

const userWorkspace = ref<UserWorkspace | null>(null);
const enterpriseWorkspace = ref<EnterpriseWorkspace | null>(null);

const userFrontImage = computed(() =>
  userWorkspace.value?.id_card.images.front
    ? `data:image/jpeg;base64,${userWorkspace.value.id_card.images.front}`
    : "",
);
const userBackImage = computed(() =>
  userWorkspace.value?.id_card.images.back
    ? `data:image/jpeg;base64,${userWorkspace.value.id_card.images.back}`
    : "",
);
const enterpriseImage = computed(() =>
  enterpriseWorkspace.value?.business_license.image_base64
    ? `data:image/jpeg;base64,${enterpriseWorkspace.value.business_license.image_base64}`
    : "",
);

const userSections = computed<ResultSection[]>(() => {
  const data = userWorkspace.value?.id_card.data;
  return [
    {
      title: "生成结果",
      rows: [
        { key: "name", label: "姓名", value: data?.name ?? "", canBackfill: true, canCopy: false, canRefresh: true },
        {
          key: "id_number",
          label: "身份证号",
          value: data?.id_number ?? "",
          canBackfill: true,
          canCopy: false,
          canRefresh: true,
        },
        { key: "phone", label: "手机号", value: data?.phone_number ?? "", canBackfill: true, canCopy: false, canRefresh: true },
        {
          key: "bank_card",
          label: "银行卡号",
          value: data?.bank_card_number ?? "",
          canBackfill: true,
          canCopy: false,
          canRefresh: true,
        },
      ],
    },
  ];
});

const enterpriseSections = computed<ResultSection[]>(() => {
  const data = enterpriseWorkspace.value?.business_license.data;
  return [
    {
      title: "生成结果",
      rows: [
        {
          key: "company_name",
          label: "企业名称",
          value: data?.company_name ?? "",
          canBackfill: true,
          canCopy: false,
          canRefresh: true,
        },
        {
          key: "credit_code",
          label: "统一信用代码",
          value: data?.unified_social_credit_code ?? "",
          canBackfill: true,
          canCopy: false,
          canRefresh: true,
        },
        {
          key: "legal_person",
          label: "法人姓名",
          value: data?.legal_person ?? "",
          canBackfill: true,
          canCopy: false,
          canRefresh: true,
        },
        {
          key: "registered_capital",
          label: "注册资本",
          value: data?.registered_capital ?? "",
          canBackfill: true,
          canCopy: false,
          canRefresh: true,
        },
      ],
    },
  ];
});

const userOcrSections = computed<ResultSection[]>(() => {
  const ocr = userWorkspace.value?.id_card.ocr;
  return [
    {
      title: "正面识别",
      rows: [
        { key: "ocr_name", label: "姓名", value: ocr?.front.name ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "ocr_gender", label: "性别", value: ocr?.front.gender ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "ocr_ethnic_group", label: "民族", value: ocr?.front.ethnic_group ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "ocr_birth_date", label: "出生日期", value: ocr?.front.birth_date ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "ocr_address", label: "地址", value: ocr?.front.address ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "ocr_id_number", label: "身份证号", value: ocr?.front.id_number ?? "", canCopy: true, canRefresh: false, canBackfill: false },
      ],
    },
    {
      title: "反面识别",
      rows: [
        {
          key: "ocr_issue_authority",
          label: "签发机关",
          value: ocr?.back.issue_authority ?? "",
          canCopy: true,
          canRefresh: false,
          canBackfill: false,
        },
        {
          key: "ocr_valid_period",
          label: "有效期限",
          value: ocr?.back.valid_period ?? "",
          canCopy: true,
          canRefresh: false,
          canBackfill: false,
        },
      ],
    },
  ];
});

const enterpriseDetailSections = computed<ResultSection[]>(() => {
  const data = enterpriseWorkspace.value?.business_license.data;
  return [
    {
      title: "主体字段",
      rows: [
        { key: "company_name", label: "企业名称", value: data?.company_name ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "company_type", label: "公司类型", value: data?.company_type ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "industry_type", label: "行业类型", value: data?.industry_type ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "credit_code", label: "统一信用代码", value: data?.unified_social_credit_code ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "legal_person", label: "法人姓名", value: data?.legal_person ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "registered_capital", label: "注册资本", value: data?.registered_capital ?? "", canCopy: true, canRefresh: false, canBackfill: false },
      ],
    },
    {
      title: "经营信息",
      rows: [
        { key: "establish_date", label: "成立日期", value: data?.establish_date_display ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "business_term", label: "经营期限", value: data?.business_term_display ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "address", label: "企业地址", value: data?.address ?? "", canCopy: true, canRefresh: false, canBackfill: false },
        { key: "business_scope", label: "经营范围", value: data?.business_scope ?? "", canCopy: true, canRefresh: false, canBackfill: false },
      ],
    },
  ];
});

function applyDefaults(target: TestDataConfig, source: TestDataConfig) {
  Object.assign(target, source);
}

function resetUserForm() {
  applyDefaults(userForm, meta.value?.defaults ?? fallbackConfig);
}

function resetEnterpriseForm() {
  applyDefaults(enterpriseForm, meta.value?.defaults ?? fallbackConfig);
}

async function bootstrap() {
  booting.value = true;
  try {
    meta.value = await fetchTestDataMeta();
    applyDefaults(userForm, meta.value.defaults);
    applyDefaults(enterpriseForm, meta.value.defaults);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    booting.value = false;
  }
}

async function loadUserWorkspace(showMessage = true) {
  userLoading.value = true;
  try {
    userWorkspace.value = await generateUserWorkspace({ ...userForm });
    if (showMessage) {
      ElMessage.success("用户信息已生成");
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    userLoading.value = false;
  }
}

async function loadEnterpriseWorkspace(showMessage = true) {
  enterpriseLoading.value = true;
  try {
    enterpriseWorkspace.value = await generateEnterpriseWorkspace({ ...enterpriseForm });
    if (showMessage) {
      ElMessage.success("企业信息已生成");
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    enterpriseLoading.value = false;
  }
}

async function handleRefreshUser(field: string) {
  if (!userWorkspace.value) return;
  userLoading.value = true;
  try {
    const next = await refreshUserField({ ...userForm }, userWorkspace.value, field);
    userWorkspace.value = next;
    ElMessage.success(next.notice ?? "字段已刷新");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    userLoading.value = false;
  }
}

async function handleRefreshEnterprise(field: string) {
  if (!enterpriseWorkspace.value) return;
  enterpriseLoading.value = true;
  try {
    const next = await refreshEnterpriseField({ ...enterpriseForm }, enterpriseWorkspace.value, field);
    enterpriseWorkspace.value = next;
    ElMessage.success(next.notice ?? "字段已刷新");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    enterpriseLoading.value = false;
  }
}

async function copyText(text: string) {
  if (!text) return;
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function getUserFieldValue(field: string) {
  const data = userWorkspace.value?.id_card.data;
  const ocr = userWorkspace.value?.id_card.ocr;
  if (!data) return "";
  switch (field) {
    case "name":
      return data.name;
    case "id_number":
      return data.id_number;
    case "phone":
      return data.phone_number;
    case "bank_card":
      return data.bank_card_number;
    case "ocr_name":
      return ocr?.front.name ?? "";
    case "ocr_gender":
      return ocr?.front.gender ?? "";
    case "ocr_ethnic_group":
      return ocr?.front.ethnic_group ?? "";
    case "ocr_birth_date":
      return ocr?.front.birth_date ?? "";
    case "ocr_address":
      return ocr?.front.address ?? "";
    case "ocr_id_number":
      return ocr?.front.id_number ?? "";
    case "ocr_issue_authority":
      return ocr?.back.issue_authority ?? "";
    case "ocr_valid_period":
      return ocr?.back.valid_period ?? "";
    default:
      return "";
  }
}

function getEnterpriseFieldValue(field: string) {
  const data = enterpriseWorkspace.value?.business_license.data;
  if (!data) return "";
  switch (field) {
    case "company_name":
      return data.company_name;
    case "credit_code":
      return data.unified_social_credit_code;
    case "legal_person":
      return data.legal_person;
    case "registered_capital":
      return data.registered_capital;
    case "company_type":
      return data.company_type;
    case "industry_type":
      return data.industry_type;
    case "establish_date":
      return data.establish_date_display;
    case "business_term":
      return data.business_term_display;
    case "address":
      return data.address;
    case "business_scope":
      return data.business_scope;
    default:
      return "";
  }
}

async function handleCopyUser(field: string) {
  const value = getUserFieldValue(field);
  if (!value) return;
  await copyText(value);
  ElMessage.success("已复制到剪贴板");
}

async function handleCopyEnterprise(field: string) {
  const value = getEnterpriseFieldValue(field);
  if (!value) return;
  await copyText(value);
  ElMessage.success("已复制到剪贴板");
}

async function handleCopyAllUser() {
  if (!userWorkspace.value?.clipboard_text) return;
  await copyText(userWorkspace.value.clipboard_text);
  ElMessage.success("用户信息已整组复制");
}

async function handleCopyAllEnterprise() {
  if (!enterpriseWorkspace.value?.clipboard_text) return;
  await copyText(enterpriseWorkspace.value.clipboard_text);
  ElMessage.success("企业信息已整组复制");
}

function handleBackfillUser(field: string) {
  const data = userWorkspace.value?.id_card.data;
  if (!data) return;

  switch (field) {
    case "name":
      userForm.name = data.name;
      break;
    case "id_number":
      userForm.mode = "id_number";
      userForm.id_number = data.id_number;
      userForm.id_prefix = data.area_prefix;
      break;
    case "phone":
      userForm.phone = data.phone_number;
      break;
    case "bank_card":
      userForm.bank_card = data.bank_card_number;
      break;
    default:
      return;
  }
  ElMessage.success("已回填到用户参数");
}

function handleBackfillEnterprise(field: string) {
  const data = enterpriseWorkspace.value?.business_license.data;
  if (!data) return;

  switch (field) {
    case "company_name":
      enterpriseForm.company_name = data.company_name;
      break;
    case "credit_code":
      enterpriseForm.credit_code = data.unified_social_credit_code;
      break;
    case "legal_person":
      enterpriseForm.legal_representative = data.legal_person;
      break;
    case "registered_capital":
      enterpriseForm.registered_capital = data.registered_capital;
      break;
    case "company_type":
      enterpriseForm.company_type = data.company_type;
      break;
    case "industry_type":
      enterpriseForm.industry_type = data.industry_type;
      break;
    case "address":
      enterpriseForm.address = data.address;
      break;
    case "business_scope":
      enterpriseForm.business_scope = data.business_scope;
      break;
    default:
      return;
  }
  ElMessage.success("已回填到企业参数");
}

function handleEchoUser() {
  const data = userWorkspace.value?.id_card.data;
  if (!data) return;
  userForm.name = data.name;
  userForm.mode = "id_number";
  userForm.id_number = data.id_number;
  userForm.id_prefix = data.area_prefix;
  userForm.phone = data.phone_number;
  userForm.bank_card = data.bank_card_number;
  ElMessage.success("用户结果已回显到配置区");
}

function handleEchoEnterprise() {
  const data = enterpriseWorkspace.value?.business_license.data;
  if (!data) return;
  enterpriseForm.company_name = data.company_name;
  enterpriseForm.credit_code = data.unified_social_credit_code;
  enterpriseForm.legal_representative = data.legal_person;
  enterpriseForm.registered_capital = data.registered_capital;
  enterpriseForm.company_type = data.company_type;
  enterpriseForm.industry_type = data.industry_type;
  enterpriseForm.address = data.address;
  enterpriseForm.business_scope = data.business_scope;
  ElMessage.success("企业结果已回显到配置区");
}

function handleClearUser() {
  resetUserForm();
  ElMessage.success("用户参数已重置");
}

function handleClearEnterprise() {
  resetEnterpriseForm();
  ElMessage.success("企业参数已重置");
}

function downloadBase64(filename: string, content: string, mime = "image/jpeg") {
  if (!content) return;
  const anchor = document.createElement("a");
  anchor.href = `data:${mime};base64,${content}`;
  anchor.download = filename;
  anchor.click();
}

function downloadUserImages() {
  if (!userWorkspace.value) return;
  downloadBase64("身份证正面.jpg", userWorkspace.value.id_card.images.front);
  downloadBase64("身份证反面.jpg", userWorkspace.value.id_card.images.back);
}

function downloadEnterpriseImage() {
  if (!enterpriseWorkspace.value) return;
  downloadBase64("营业执照.jpg", enterpriseWorkspace.value.business_license.image_base64);
}

onMounted(() => {
  void bootstrap();
});
</script>

<template>
  <div class="test-data-page">
    <div v-if="booting" class="loading-shell">
      <el-skeleton :rows="12" animated />
    </div>

    <div v-else class="test-data-workbench">
      <TestDataUserConfigPanel
        v-model="userForm"
        title="用户信息配置"
        :options="meta?.options ?? null"
      >
        <template #footer>
          <el-button type="primary" size="small" :loading="userLoading" @click="() => loadUserWorkspace()">
            生成
          </el-button>
          <el-button size="small" @click="handleCopyAllUser">复制</el-button>
          <el-button size="small" @click="handleEchoUser">回显</el-button>
          <el-button size="small" plain @click="handleClearUser">清空</el-button>
        </template>
      </TestDataUserConfigPanel>

      <TestDataResultPanel
        v-loading="userLoading"
        title="用户信息生成结果"
        :sections="userSections"
        :loading="userLoading"
        :show-section-header="false"
        :show-footer="false"
        inline-rows
        element-loading-text="正在生成用户信息"
        @refresh="handleRefreshUser"
        @copy="handleCopyUser"
        @backfill="handleBackfillUser"
      >
        <template #append>
          <section class="result-preview">
            <div class="result-preview-head">
              <h3>身份证图片</h3>
              <div class="panel-head-actions">
                <el-button size="small" plain :disabled="!userWorkspace" @click="userDetailVisible = true">
                  查看详情
                </el-button>
                <el-button size="small" plain :disabled="!userWorkspace" @click="downloadUserImages">
                  下载
                </el-button>
              </div>
            </div>

            <div
              class="preview-stack result-preview-stack"
              :class="{ 'preview-stack--empty': !userFrontImage && !userBackImage }"
            >
              <template v-if="userFrontImage || userBackImage">
                <div v-if="userFrontImage" class="preview-box">
                  <el-image
                    class="preview-image preview-image-id"
                    :src="userFrontImage"
                    :preview-src-list="userFrontImage ? [userFrontImage] : []"
                    fit="contain"
                    preview-teleported
                  />
                </div>

                <div v-if="userBackImage" class="preview-box">
                  <el-image
                    class="preview-image preview-image-id"
                    :src="userBackImage"
                    :preview-src-list="userBackImage ? [userBackImage] : []"
                    fit="contain"
                    preview-teleported
                  />
                </div>
              </template>
              <div v-else class="preview-placeholder-text">点击生成后查看预览</div>
            </div>
          </section>
        </template>
      </TestDataResultPanel>

      <TestDataEnterpriseConfigPanel
        v-model="enterpriseForm"
        title="企业信息配置"
        :options="meta?.options ?? null"
      >
        <template #footer>
          <el-button type="primary" size="small" :loading="enterpriseLoading" @click="() => loadEnterpriseWorkspace()">
            生成
          </el-button>
          <el-button size="small" @click="handleCopyAllEnterprise">复制</el-button>
          <el-button size="small" @click="handleEchoEnterprise">回显</el-button>
          <el-button size="small" plain @click="handleClearEnterprise">清空</el-button>
        </template>
      </TestDataEnterpriseConfigPanel>

      <TestDataResultPanel
        v-loading="enterpriseLoading"
        title="企业信息生成结果"
        :sections="enterpriseSections"
        :loading="enterpriseLoading"
        :show-section-header="false"
        :show-footer="false"
        inline-rows
        element-loading-text="正在生成企业信息"
        @refresh="handleRefreshEnterprise"
        @copy="handleCopyEnterprise"
        @backfill="handleBackfillEnterprise"
      >
        <template #append>
          <section class="result-preview">
            <div class="result-preview-head">
              <h3>营业执照图片</h3>
              <div class="panel-head-actions">
                <el-button size="small" plain :disabled="!enterpriseWorkspace" @click="enterpriseDetailVisible = true">
                  查看详情
                </el-button>
                <el-button size="small" plain :disabled="!enterpriseWorkspace" @click="downloadEnterpriseImage">
                  下载
                </el-button>
              </div>
            </div>

            <div class="license-body result-license-body">
              <div v-if="enterpriseImage" class="preview-box preview-box-license">
                <el-image
                  class="preview-image preview-image-license"
                  :src="enterpriseImage"
                  :preview-src-list="enterpriseImage ? [enterpriseImage] : []"
                  fit="contain"
                  preview-teleported
                />
              </div>
              <div v-else class="preview-placeholder-text">点击生成后查看预览</div>
            </div>
          </section>
        </template>
      </TestDataResultPanel>
    </div>

    <el-dialog v-model="userDetailVisible" title="身份证 OCR 结果" width="680px" destroy-on-close>
      <div class="detail-dialog">
        <TestDataResultPanel
          title="OCR 结构化结果"
          :sections="userOcrSections"
          :loading="false"
          :show-footer="false"
          :show-echo-all="false"
          :show-clear="false"
          inline-rows
          @copy="handleCopyUser"
          @copy-all="handleCopyAllUser"
          @refresh="() => undefined"
          @backfill="() => undefined"
          @echo-all="() => undefined"
          @clear="() => undefined"
        />
      </div>
    </el-dialog>

    <el-dialog v-model="enterpriseDetailVisible" title="营业执照完整字段" width="760px" destroy-on-close>
      <div class="detail-dialog">
        <TestDataResultPanel
          title="完整字段"
          :sections="enterpriseDetailSections"
          :loading="false"
          :show-footer="false"
          :show-echo-all="false"
          :show-clear="false"
          inline-rows
          @copy="handleCopyEnterprise"
          @copy-all="handleCopyAllEnterprise"
          @refresh="() => undefined"
          @backfill="() => undefined"
          @echo-all="() => undefined"
          @clear="() => undefined"
        />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.test-data-page {
  display: grid;
  gap: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.loading-shell {
  height: 100%;
  min-height: 0;
  border: 1px solid #e6ebf0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
  padding: 18px;
}

.test-data-workbench {
  display: grid;
  height: 100%;
  min-height: 0;
  gap: 16px;
  align-items: stretch;
  overflow: auto;
  width: 100%;
  grid-template-columns:
    minmax(320px, 0.95fr)
    minmax(390px, 1.05fr)
    minmax(320px, 0.95fr)
    minmax(390px, 1.05fr);
}

.work-panel {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e6ebf0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
}

.panel-head {
  display: flex;
  min-height: 50px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #edf1f6;
  background: linear-gradient(180deg, #fafcff 0%, #ffffff 100%);
}

.panel-head h2 {
  margin: 0;
  color: var(--qm-title);
  font-size: 15px;
  font-weight: 600;
}

.panel-body {
  min-height: 0;
  padding: 18px 18px;
}

.panel-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-head-actions :deep(.el-button) {
  min-height: 28px;
  padding: 6px 12px;
  font-size: 12px;
}

.result-preview {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.result-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.result-preview-head h3 {
  margin: 0;
  color: var(--qm-title);
  font-size: 13px;
  font-weight: 600;
}

.preview-stack {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: flex-start;
  min-height: 0;
  gap: 8px;
  width: 100%;
}

.result-preview-stack {
  flex: none;
  gap: 10px;
}

.preview-stack--empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-box {
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0;
  transition: none;
}

.preview-box:hover {
  border-color: transparent;
  box-shadow: none;
  transform: none;
}

.preview-box-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--qm-title);
  font-size: 13px;
  font-weight: 600;
}

.preview-image {
  width: 100%;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.preview-image-id {
  height: 214px;
}

.result-preview .preview-image-id {
  aspect-ratio: 1.58 / 1;
  height: auto;
  min-height: 238px;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #a0a8b6;
  font-size: 13px;
  line-height: 1.6;
  text-align: center;
}

.preview-empty-id {
  height: 214px;
}

.preview-placeholder-text {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 120px;
  color: #a0a8b6;
  font-size: 13px;
  line-height: 1.6;
  text-align: center;
}

.license-body {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 0;
  padding: 6px 0;
}

.result-license-body {
  min-height: 0;
  padding: 0;
}

.preview-box-license {
  display: flex;
  align-items: center;
  justify-content: center;
  width: min(100%, 360px);
  min-height: clamp(520px, calc(100vh - 260px), 640px);
  height: auto;
  overflow: hidden;
  margin: 0 auto;
}

.result-license-body .preview-box-license {
  width: min(100%, 480px);
  min-height: 0;
  max-height: none;
}

.preview-image-license {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
}

.result-license-body .preview-image-license {
  aspect-ratio: 0.72 / 1;
  height: auto;
  min-height: 560px;
  max-height: none;
}

.preview-empty-license {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
}

.detail-dialog :deep(.work-panel) {
  min-height: auto;
  box-shadow: none;
  border-radius: 12px;
}

.detail-dialog :deep(.panel-footer) {
  grid-template-columns: 1.15fr 1fr;
}

:global(.el-image-viewer__img) {
  max-width: 72vw !important;
  max-height: 74vh !important;
}

@media (max-width: 1540px) {
  .test-data-workbench {
    grid-template-columns: minmax(320px, 0.9fr) minmax(420px, 1.1fr);
  }
}

@media (max-width: 1180px) {
  .test-data-workbench {
    grid-template-columns: minmax(300px, 0.9fr) minmax(360px, 1.1fr);
  }

  .work-panel {
    min-height: auto;
  }
}

@media (max-width: 960px) {
  .test-data-workbench {
    grid-template-columns: 1fr;
  }

  .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .preview-image-license {
    height: 620px;
  }

  .preview-empty-license {
    height: 620px;
  }
}
</style>
