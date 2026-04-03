<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import type { TabsPaneContext } from "element-plus";

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

type WorkspaceTab = "user" | "enterprise";

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
const activeTab = ref<WorkspaceTab>("user");
const userLoading = ref(false);
const enterpriseLoading = ref(false);
const userDetailVisible = ref(false);
const enterpriseDetailVisible = ref(false);

const userForm = reactive<TestDataConfig>({ ...fallbackConfig });
const enterpriseForm = reactive<TestDataConfig>({ ...fallbackConfig });

const userWorkspace = ref<UserWorkspace | null>(null);
const enterpriseWorkspace = ref<EnterpriseWorkspace | null>(null);

const currentLoading = computed(() =>
  activeTab.value === "user" ? userLoading.value : enterpriseLoading.value,
);

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
      title: "核心结果",
      rows: [
        { key: "name", label: "姓名", value: data?.name ?? "", canBackfill: true, canRefresh: true },
        {
          key: "id_number",
          label: "身份证号",
          value: data?.id_number ?? "",
          canBackfill: true,
          canRefresh: true,
        },
        { key: "phone", label: "手机号", value: data?.phone_number ?? "", canBackfill: true, canRefresh: true },
        {
          key: "bank_card",
          label: "银行卡号",
          value: data?.bank_card_number ?? "",
          canBackfill: true,
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
      title: "核心结果",
      rows: [
        {
          key: "company_name",
          label: "企业名称",
          value: data?.company_name ?? "",
          canBackfill: true,
          canRefresh: true,
        },
        {
          key: "credit_code",
          label: "统一信用代码",
          value: data?.unified_social_credit_code ?? "",
          canBackfill: true,
          canRefresh: true,
        },
        {
          key: "legal_person",
          label: "法人姓名",
          value: data?.legal_person ?? "",
          canBackfill: true,
          canRefresh: true,
        },
        {
          key: "registered_capital",
          label: "注册资本",
          value: data?.registered_capital ?? "",
          canBackfill: true,
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
    activeTab.value = "user";
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

function handleTabClick(tab: TabsPaneContext) {
  activeTab.value = tab.paneName as WorkspaceTab;
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

    <el-tabs
      v-else
      v-model="activeTab"
      class="workspace-tabs"
      @tab-click="handleTabClick"
    >
      <el-tab-pane label="用户信息" name="user">
        <div
          v-loading="userLoading"
          class="tab-workbench user-grid"
          element-loading-text="正在生成用户信息"
        >
          <TestDataUserConfigPanel v-model="userForm" :options="meta?.options ?? null" />

          <TestDataResultPanel
            title="核心结果"
            description="按需生成后在这里查看常用身份字段"
            :sections="userSections"
            :loading="userLoading"
            generate-label="生成"
            @refresh="handleRefreshUser"
            @copy="handleCopyUser"
            @backfill="handleBackfillUser"
            @generate="loadUserWorkspace"
            @copy-all="handleCopyAllUser"
            @echo-all="handleEchoUser"
            @clear="handleClearUser"
          />

          <section class="work-panel preview-panel">
            <div class="panel-head">
              <div class="panel-title-group">
                <h2>身份证预览</h2>
                <span class="panel-meta">点击生成后查看证件图。</span>
              </div>
              <div class="panel-head-actions">
                <el-button size="small" plain :disabled="!userWorkspace" @click="userDetailVisible = true">
                  查看 OCR
                </el-button>
                <el-button size="small" plain :disabled="!userWorkspace" @click="downloadUserImages">
                  下载全部
                </el-button>
              </div>
            </div>

            <div class="panel-body preview-stack">
              <div class="preview-box">
                <div class="preview-box-head">
                  <span>身份证正面</span>
                  <el-button
                    size="small"
                    link
                    :disabled="!userWorkspace"
                    @click="userWorkspace && downloadBase64('身份证正面.jpg', userWorkspace.id_card.images.front)"
                  >
                    下载
                  </el-button>
                </div>
                <el-image
                  v-if="userFrontImage"
                  class="preview-image preview-image-id"
                  :src="userFrontImage"
                  :preview-src-list="userFrontImage ? [userFrontImage] : []"
                  fit="contain"
                  preview-teleported
                />
                <div v-else class="preview-empty preview-empty-id">点击生成后查看预览</div>
              </div>

              <div class="preview-box">
                <div class="preview-box-head">
                  <span>身份证反面</span>
                  <el-button
                    size="small"
                    link
                    :disabled="!userWorkspace"
                    @click="userWorkspace && downloadBase64('身份证反面.jpg', userWorkspace.id_card.images.back)"
                  >
                    下载
                  </el-button>
                </div>
                <el-image
                  v-if="userBackImage"
                  class="preview-image preview-image-id"
                  :src="userBackImage"
                  :preview-src-list="userBackImage ? [userBackImage] : []"
                  fit="contain"
                  preview-teleported
                />
                <div v-else class="preview-empty preview-empty-id">点击生成后查看预览</div>
              </div>
            </div>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="企业信息" name="enterprise">
        <div
          v-loading="enterpriseLoading"
          class="tab-workbench enterprise-grid"
          element-loading-text="正在生成企业信息"
        >
          <TestDataEnterpriseConfigPanel v-model="enterpriseForm" :options="meta?.options ?? null" />

          <TestDataResultPanel
            title="核心结果"
            description="按需生成后查看企业主体字段，完整信息收进详情面板"
            :sections="enterpriseSections"
            :loading="enterpriseLoading"
            generate-label="生成"
            @refresh="handleRefreshEnterprise"
            @copy="handleCopyEnterprise"
            @backfill="handleBackfillEnterprise"
            @generate="loadEnterpriseWorkspace"
            @copy-all="handleCopyAllEnterprise"
            @echo-all="handleEchoEnterprise"
            @clear="handleClearEnterprise"
          />

          <section class="work-panel preview-panel">
            <div class="panel-head">
              <div class="panel-title-group">
                <h2>营业执照预览</h2>
                <span class="panel-meta">点击生成后查看执照版式，可查看详情。</span>
              </div>
              <div class="panel-head-actions">
                <el-button size="small" plain :disabled="!enterpriseWorkspace" @click="enterpriseDetailVisible = true">
                  查看详情
                </el-button>
                <el-button size="small" plain :disabled="!enterpriseWorkspace" @click="downloadEnterpriseImage">
                  下载
                </el-button>
              </div>
            </div>

            <div class="panel-body license-body">
              <div class="preview-box preview-box-license">
                <el-image
                  v-if="enterpriseImage"
                  class="preview-image preview-image-license"
                  :src="enterpriseImage"
                  :preview-src-list="enterpriseImage ? [enterpriseImage] : []"
                  fit="contain"
                  preview-teleported
                />
                <div v-else class="preview-empty preview-empty-license">点击生成后查看预览</div>
              </div>
            </div>
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="userDetailVisible" title="身份证 OCR 结果" width="680px" destroy-on-close>
      <div class="detail-dialog">
        <TestDataResultPanel
          title="OCR 结构化结果"
          :sections="userOcrSections"
          :loading="false"
          :show-footer="false"
          :show-echo-all="false"
          :show-clear="false"
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

.workspace-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #e6ebf0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
  padding: 0 14px 14px;
}

.workspace-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.workspace-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.workspace-tabs :deep(.el-tabs__item) {
  height: 54px;
  padding: 0 18px;
  color: #6b7380;
  font-size: 14px;
  font-weight: 500;
}

.workspace-tabs :deep(.el-tabs__item.is-active) {
  color: #135bd8;
  font-weight: 600;
}

.workspace-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, #1677ff 0%, #4aa2ff 100%);
}

.workspace-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding-top: 14px;
}

.workspace-tabs :deep(.el-tab-pane) {
  display: block;
  height: 100%;
}

.tab-workbench {
  display: grid;
  height: 100%;
  min-height: 0;
  gap: 16px;
  align-items: stretch;
}

.user-grid {
  grid-template-columns: minmax(320px, 380px) minmax(390px, 400px) minmax(380px, 450px);
}

.enterprise-grid {
  grid-template-columns: minmax(320px, 380px) minmax(390px, 400px) minmax(380px, 450px);
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
  min-height: 68px;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid #edf1f6;
  background: linear-gradient(180deg, #fafcff 0%, #ffffff 100%);
}

.panel-title-group {
  display: grid;
  gap: 4px;
}

.panel-head h2 {
  margin: 0;
  color: var(--qm-title);
  font-size: 15px;
  font-weight: 600;
}

.panel-meta {
  color: #8a94a6;
  font-size: 12px;
  line-height: 1.5;
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

.preview-panel {
  min-width: 0;
}

.preview-stack {
  display: grid;
  min-height: 0;
  gap: 14px;
}

.preview-box {
  border: 1px solid #e9eef5;
  border-radius: 14px;
  background: linear-gradient(180deg, #fafbfc 0%, #f6f8fb 100%);
  padding: 12px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.preview-box:hover {
  border-color: #d9e2ee;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.preview-box-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--qm-title);
  font-size: 13px;
  font-weight: 600;
}

.preview-image {
  width: 100%;
  overflow: hidden;
  border: 1px solid #dde6f0;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfd 100%);
}

.preview-image-id {
  height: 214px;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  overflow: hidden;
  border: 1px solid #dde6f0;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfd 100%);
  color: #a0a8b6;
  font-size: 13px;
  line-height: 1.6;
  text-align: center;
}

.preview-empty-id {
  height: 214px;
}

.license-body {
  flex: 1;
  min-height: 0;
}

.preview-box-license {
  display: flex;
  min-height: 0;
  height: 100%;
}

.preview-image-license {
  height: clamp(520px, calc(100vh - 324px), 660px);
}

.preview-empty-license {
  height: clamp(520px, calc(100vh - 324px), 660px);
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

@media (max-width: 1760px) {
  .user-grid,
  .enterprise-grid {
    grid-template-columns: minmax(374px, 414px) minmax(384px, 424px) minmax(328px, 368px);
  }
}

@media (max-width: 1480px) {
  .user-grid,
  .enterprise-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .work-panel {
    min-height: auto;
  }
}

@media (max-width: 960px) {
  .tab-workbench {
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
