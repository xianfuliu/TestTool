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
        <h2>参数配置</h2>
        <span class="panel-meta">标签与输入同行排布，录入更紧凑</span>
      </div>
    </div>

    <el-scrollbar class="panel-scroll">
      <div class="panel-body">
        <section class="section-block">
          <div class="section-head">
            <h3>证件配置</h3>
            <span>身份证、手机号、银行卡</span>
          </div>

          <el-form label-width="84px" size="small" class="config-form">
            <div class="form-grid">
              <el-form-item label="生成模式" class="span-full">
                <el-radio-group v-model="form.mode" class="segmented-group mode-group">
                  <el-radio-button value="age">按年龄</el-radio-button>
                  <el-radio-button value="id_number">按身份证号</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="最小年龄">
                <el-input-number
                  v-model="form.min_age"
                  :min="16"
                  :max="60"
                  controls-position="right"
                />
              </el-form-item>

              <el-form-item label="最大年龄">
                <el-input-number
                  v-model="form.max_age"
                  :min="16"
                  :max="60"
                  controls-position="right"
                />
              </el-form-item>

              <el-form-item v-if="form.mode === 'age'" label="年龄">
                <el-input v-model="form.age" placeholder="16-60" clearable />
              </el-form-item>

              <el-form-item v-else label="身份证号" class="span-full">
                <el-input
                  v-model="form.id_number"
                  maxlength="18"
                  placeholder="输入身份证号"
                  clearable
                />
              </el-form-item>

              <el-form-item label="姓名">
                <el-input v-model="form.name" placeholder="默认随机" clearable />
              </el-form-item>

              <el-form-item label="民族">
                <el-select v-model="form.ethnic_group">
                  <el-option
                    v-for="item in options?.ethnic_groups ?? []"
                    :key="item"
                    :label="item"
                    :value="item === '随机' ? 'random' : item"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="性别" class="span-full">
                <el-radio-group v-model="form.gender" class="segmented-group compact-group">
                  <el-radio-button value="random">随机</el-radio-button>
                  <el-radio-button value="male">男</el-radio-button>
                  <el-radio-button value="female">女</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="身份证开头">
                <el-select v-model="form.id_prefix">
                  <el-option
                    v-for="item in options?.areas ?? []"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="手机号">
                <el-input v-model="form.phone" placeholder="前三位或完整号码" clearable />
              </el-form-item>

              <el-form-item label="银行">
                <el-select v-model="form.bank_name">
                  <el-option
                    v-for="item in options?.banks ?? []"
                    :key="item"
                    :label="item"
                    :value="item"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="银行卡型" class="span-full">
                <el-radio-group v-model="form.card_type" class="segmented-group card-group">
                  <el-radio-button value="debit">储蓄卡</el-radio-button>
                  <el-radio-button value="credit">信用卡</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </div>
          </el-form>
        </section>

        <section class="section-block">
          <div class="section-head">
            <h3>企业配置</h3>
            <span>营业执照字段与经营范围</span>
          </div>

          <el-form label-width="84px" size="small" class="config-form">
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

              <el-form-item label="公司名称" class="span-full">
                <el-input v-model="form.company_name" placeholder="默认随机生成" clearable />
              </el-form-item>

              <el-form-item label="信用代码" class="span-full">
                <el-input v-model="form.credit_code" placeholder="默认随机生成" clearable />
              </el-form-item>

              <el-form-item label="法人姓名">
                <el-input
                  v-model="form.legal_representative"
                  placeholder="默认取身份证姓名"
                  clearable
                />
              </el-form-item>

              <el-form-item label="注册资本">
                <el-input v-model="form.registered_capital" placeholder="默认随机" clearable />
              </el-form-item>

              <el-form-item label="住所" class="span-full">
                <el-input v-model="form.address" placeholder="默认随机生成" clearable />
              </el-form-item>

              <el-form-item label="成立日期">
                <el-input
                  v-model="form.establish_date"
                  placeholder="YYYYMMDD 或 YYYY-MM-DD"
                  clearable
                />
              </el-form-item>

              <el-form-item label="营业开始">
                <el-input
                  v-model="form.business_start_date"
                  placeholder="YYYYMMDD 或 YYYY-MM-DD"
                  clearable
                />
              </el-form-item>

              <el-form-item label="营业结束" class="span-full">
                <el-input
                  v-model="form.business_end_date"
                  placeholder="YYYYMMDD 或 YYYY-MM-DD"
                  clearable
                />
              </el-form-item>

              <el-form-item label="经营范围" class="span-full align-top">
                <el-input
                  v-model="form.business_scope"
                  type="textarea"
                  :rows="4"
                  resize="none"
                  placeholder="默认按行业自动生成"
                />
              </el-form-item>
            </div>
          </el-form>
        </section>
      </div>
    </el-scrollbar>
  </section>
</template>

<style scoped>
.work-panel {
  display: flex;
  min-height: calc(100vh - 170px);
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e6ebf0;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
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
  line-height: 1.4;
}

.panel-scroll {
  flex: 1;
}

.panel-body {
  display: grid;
  gap: 14px;
  padding: 16px 18px;
}

.section-block {
  border: 1px solid #ebeff5;
  border-radius: 12px;
  background: linear-gradient(180deg, #fafbfd 0%, #ffffff 100%);
  padding: 14px;
}

.section-head {
  display: grid;
  gap: 4px;
  margin-bottom: 14px;
}

.section-head h3 {
  margin: 0;
  color: var(--qm-title);
  font-size: 13px;
  font-weight: 600;
}

.section-head span {
  color: #8a94a6;
  font-size: 12px;
  line-height: 1.4;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 10px;
}

.span-full {
  grid-column: 1 / -1;
}

.config-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.config-form :deep(.el-form-item__label) {
  justify-content: flex-end;
  padding-right: 8px;
  color: #5b6472;
  font-size: 12px;
  line-height: 30px;
}

.config-form :deep(.el-form-item__content) {
  min-width: 0;
}

.config-form :deep(.el-input),
.config-form :deep(.el-select),
.config-form :deep(.el-input-number) {
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
  box-shadow: 0 0 0 1px rgba(22, 119, 255, 0.38) inset;
}

.segmented-group {
  display: grid;
  width: 100%;
}

.mode-group {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.compact-group {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.card-group {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.config-form :deep(.segmented-group .el-radio-button__inner) {
  width: 100%;
  border-color: #dde6f0;
  background: #f8fafc;
  color: #4b5565;
  font-weight: 500;
  box-shadow: none;
}

.config-form :deep(.segmented-group .el-radio-button:first-child .el-radio-button__inner) {
  border-left-color: #dde6f0;
}

.config-form :deep(.segmented-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: rgba(22, 119, 255, 0.36);
  background: linear-gradient(180deg, #eef5ff 0%, #e6f0ff 100%);
  color: #135bd8;
  box-shadow: none;
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
