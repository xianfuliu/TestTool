<script setup lang="ts">
import type { TestDataConfig, TestDataOptions } from "../types";

defineProps<{
  options: TestDataOptions | null;
}>();

const form = defineModel<TestDataConfig>({ required: true });
</script>

<template>
  <section class="work-panel">
    <div class="panel-head">
      <div class="panel-title-group">
        <h2>企业参数</h2>
        <span class="panel-meta">营业执照主体信息配置</span>
      </div>
    </div>

    <el-scrollbar class="panel-scroll">
      <div class="panel-body">
        <el-form label-width="74px" size="small" class="config-form">
          <div class="form-grid">
            <el-form-item label="公司类型">
              <el-select v-model="form.company_type">
                <el-option
                  v-for="item in options?.company_types ?? []"
                  :key="item"
                  :label="item"
                  :value="item === '随机' ? 'random' : item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="行业类型">
              <el-select v-model="form.industry_type">
                <el-option
                  v-for="item in options?.industries ?? []"
                  :key="item"
                  :label="item"
                  :value="item === '随机' ? 'random' : item"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="企业名称" class="span-full">
              <el-input v-model="form.company_name" placeholder="留空则随机生成" clearable />
            </el-form-item>
            <el-form-item label="信用代码" class="span-full">
              <el-input v-model="form.credit_code" placeholder="留空则随机生成" clearable />
            </el-form-item>

            <el-form-item label="法人姓名">
              <el-input v-model="form.legal_representative" placeholder="留空则随机生成" clearable />
            </el-form-item>
            <el-form-item label="注册资本">
              <el-input v-model="form.registered_capital" placeholder="例如 500万元" clearable />
            </el-form-item>

            <el-form-item label="地区">
              <el-select v-model="form.id_prefix">
                <el-option
                  v-for="item in options?.areas ?? []"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="成立日期">
              <el-input v-model="form.establish_date" placeholder="YYYYMMDD 或 YYYY-MM-DD" clearable />
            </el-form-item>

            <el-form-item label="经营开始">
              <el-input
                v-model="form.business_start_date"
                placeholder="留空则与成立日期一致"
                clearable
              />
            </el-form-item>
            <el-form-item label="经营结束">
              <el-input v-model="form.business_end_date" placeholder="留空则自动生成" clearable />
            </el-form-item>

            <el-form-item label="企业地址" class="span-full">
              <el-input v-model="form.address" placeholder="留空则按地区随机生成" clearable />
            </el-form-item>
            <el-form-item label="经营范围" class="span-full align-top">
              <el-input
                v-model="form.business_scope"
                type="textarea"
                :rows="5"
                resize="none"
                placeholder="留空则按行业自动生成"
              />
            </el-form-item>
          </div>
        </el-form>
      </div>
    </el-scrollbar>
  </section>
</template>

<style scoped>
.work-panel {
  display: flex;
  min-height: calc(100vh - 176px);
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e6ebf0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
}

.panel-head {
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

.panel-scroll {
  flex: 1;
}

.panel-body {
  padding: 18px 20px 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
}

.span-full {
  grid-column: auto;
}

.config-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.config-form :deep(.el-form-item__label) {
  justify-content: flex-end;
  padding-right: 10px;
  color: #5b6472;
  font-size: 12px;
}

.config-form :deep(.el-input),
.config-form :deep(.el-select),
.config-form :deep(.el-textarea) {
  width: 100%;
}

.config-form :deep(.el-input__wrapper),
.config-form :deep(.el-textarea__inner),
.config-form :deep(.el-select__wrapper) {
  background: #fbfcfd;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}

.config-form :deep(.el-input__wrapper:hover),
.config-form :deep(.el-textarea__inner:hover),
.config-form :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px #cad5e3 inset;
}

.config-form :deep(.el-input__wrapper.is-focus),
.config-form :deep(.el-select__wrapper.is-focused),
.config-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px rgba(22, 119, 255, 0.36) inset;
}

.align-top :deep(.el-form-item__label) {
  align-self: flex-start;
  line-height: 30px;
}

@media (max-width: 1440px) {
  .work-panel {
    min-height: auto;
  }
}

@media (max-width: 560px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .span-full {
    grid-column: auto;
  }
}
</style>
