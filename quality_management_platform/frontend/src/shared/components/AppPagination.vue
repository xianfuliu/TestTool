<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    total: number;
    currentPage: number;
    pageSize: number;
    pageSizes?: number[];
    layout?: string;
    disabled?: boolean;
    hideOnSinglePage?: boolean;
  }>(),
  {
    pageSizes: () => [10, 20, 50, 100],
    layout: "sizes, prev, pager, next, jumper",
    disabled: false,
    hideOnSinglePage: false,
  },
);

const emit = defineEmits<{
  (event: "update:currentPage", value: number): void;
  (event: "update:pageSize", value: number): void;
  (event: "current-change", value: number): void;
  (event: "size-change", value: number): void;
}>();

function handleCurrentChange(page: number) {
  emit("update:currentPage", page);
  emit("current-change", page);
}

function handleSizeChange(size: number) {
  emit("update:pageSize", size);
  emit("size-change", size);
}
</script>

<template>
  <div class="app-pagination">
    <span class="app-pagination__total">共 {{ props.total }} 条</span>
    <el-pagination
      class="app-pagination__control"
      size="small"
      :current-page="props.currentPage"
      :page-size="props.pageSize"
      :page-sizes="props.pageSizes"
      :total="props.total"
      :layout="props.layout"
      :disabled="props.disabled"
      :hide-on-single-page="props.hideOnSinglePage"
      popper-class="compact-select-popper"
      @current-change="handleCurrentChange"
      @size-change="handleSizeChange"
    />
  </div>
</template>

<style scoped>
.app-pagination {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 38px;
  padding-top: 12px;
}

.app-pagination__total {
  flex: 0 0 auto;
  color: #697586;
  font-size: 12px;
  line-height: 24px;
  white-space: nowrap;
}

.app-pagination__control {
  flex: 0 1 auto;
  justify-content: flex-end;
  min-width: 0;
}

.app-pagination :deep(.el-pagination__sizes .el-select) {
  width: 96px;
}

.app-pagination :deep(.el-pagination__jump) {
  color: #697586;
  font-size: 12px;
}

@media (max-width: 760px) {
  .app-pagination {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
