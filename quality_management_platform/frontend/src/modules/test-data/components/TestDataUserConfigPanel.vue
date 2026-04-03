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
        <h2>用户参数</h2>
        <span class="panel-meta">身份证与基础身份信息配置</span>
      </div>
    </div>

    <el-scrollbar class="panel-scroll">
      <div class="panel-body">
        <el-form label-width="74px" size="small" class="config-form">
          <div class="form-grid">
            <el-form-item label="生成方式" class="span-full">
              <el-radio-group v-model="form.mode" class="plain-radio-group">
                <el-radio value="age">按年龄</el-radio>
                <el-radio value="id_number">按身份证号</el-radio>
              </el-radio-group>
            </el-form-item>

            <template v-if="form.mode === 'age'">
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
              <el-form-item label="指定年龄" class="span-full">
                <el-input v-model="form.age" placeholder="留空则按区间随机" clearable />
              </el-form-item>
            </template>
            <el-form-item v-else label="身份证号" class="span-full">
              <el-input v-model="form.id_number" maxlength="18" placeholder="输入身份证号" clearable />
            </el-form-item>

            <el-form-item label="姓名">
              <el-input v-model="form.name" placeholder="留空则随机生成" clearable />
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
              <el-radio-group v-model="form.gender" class="plain-radio-group">
                <el-radio value="random">随机</el-radio>
                <el-radio value="male">男</el-radio>
                <el-radio value="female">女</el-radio>
              </el-radio-group>
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
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="前三位或完整号码" clearable />
            </el-form-item>

            <el-form-item label="银行">
              <el-select v-model="form.bank_name">
                <el-option v-for="item in options?.banks ?? []" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
            <el-form-item label="卡类型">
              <el-radio-group v-model="form.card_type" class="plain-radio-group">
                <el-radio value="debit">储蓄卡</el-radio>
                <el-radio value="credit">信用卡</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="银行卡" class="span-full">
              <el-input v-model="form.bank_card" placeholder="留空则自动生成" clearable />
            </el-form-item>

            <el-form-item label="地址" class="span-full">
              <el-input
                v-model="form.address"
                placeholder="留空则按地区随机生成"
                clearable
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
  box-shadow: 0 0 0 1px rgba(22, 119, 255, 0.36) inset;
}

.plain-radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  min-height: 32px;
  align-items: center;
}

.config-form :deep(.plain-radio-group .el-radio) {
  margin-right: 0;
  color: #4b5565;
  font-size: 13px;
  font-weight: 500;
}

.config-form :deep(.plain-radio-group .el-radio__label) {
  padding-left: 8px;
}

.config-form :deep(.plain-radio-group .el-radio__input.is-checked + .el-radio__label) {
  color: #135bd8;
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
