<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { get, post } from "@/shared/api/client";
import ModuleHeader from "@/shared/components/ModuleHeader.vue";

type ProductItem = {
  name: string;
  config_path: string;
  locked: boolean;
};

const products = ref<ProductItem[]>([]);
const selectedProduct = ref("");
const productConfig = ref<Record<string, unknown> | null>(null);
const executeResult = ref<Record<string, unknown> | null>(null);
const loadingProducts = ref(false);
const executing = ref(false);

const requestForm = reactive({
  url: "",
  method: "POST",
  headersText: "{\n  \"Content-Type\": \"application/json\"\n}",
  bodyText: "{\n  \"example\": true\n}",
  encrypt_url: "",
  decrypt_url: "",
});

const currentProduct = computed(() => {
  return products.value.find((item) => item.name === selectedProduct.value) ?? null;
});

async function loadProducts() {
  loadingProducts.value = true;
  try {
    const data = await get<{ products: ProductItem[]; default_product: string }>("/api/api-tool/products/");
    products.value = data.products;
    selectedProduct.value = data.default_product || data.products[0]?.name || "";
    if (selectedProduct.value) {
      await loadProduct(selectedProduct.value);
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loadingProducts.value = false;
  }
}

async function loadProduct(productName: string) {
  try {
    const data = await get<{ config: Record<string, unknown> }>(`/api/api-tool/products/${productName}/`);
    productConfig.value = data.config;
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function executeRequest() {
  executing.value = true;
  try {
    executeResult.value = await post("/api/api-tool/execute/", {
      ...requestForm,
      headers: JSON.parse(requestForm.headersText),
      body: JSON.parse(requestForm.bodyText),
    });
    ElMessage.success("请求执行完成");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    executing.value = false;
  }
}

onMounted(loadProducts);
</script>

<template>
  <div class="page-shell">
    <ModuleHeader
      title="接口工具模块"
      subtitle="把产品配置、请求编排和执行结果整合为标准后台调试页，减少工具感过强、信息分散的问题。"
    >
      <el-space wrap>
        <el-select
          v-model="selectedProduct"
          placeholder="选择产品"
          style="width: 220px"
          @change="loadProduct"
        >
          <el-option
            v-for="item in products"
            :key="item.name"
            :label="item.name"
            :value="item.name"
          />
        </el-select>
        <el-button :loading="loadingProducts" @click="loadProducts">刷新配置</el-button>
        <el-button type="primary" :loading="executing" @click="executeRequest">发送请求</el-button>
      </el-space>
    </ModuleHeader>

    <div class="grid-two">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">产品配置</p>
              <p class="section-caption">保留原有产品配置体系，但用更清晰的后台方式展示。</p>
            </div>
            <el-tag :type="currentProduct?.locked ? 'warning' : 'success'" effect="plain">
              {{ currentProduct?.locked ? "配置锁定" : "配置可编辑" }}
            </el-tag>
          </div>
        </template>

        <div v-if="currentProduct" class="product-panel">
          <div class="soft-panel">
            <span>配置文件</span>
            <strong>{{ currentProduct.config_path }}</strong>
          </div>
          <pre class="json-box">{{ JSON.stringify(productConfig, null, 2) }}</pre>
        </div>

        <div v-else class="empty-block">
          <el-empty description="暂无可用产品配置" />
        </div>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div>
            <p class="section-title">请求编排</p>
            <p class="section-caption">把 URL、方法、头部、Body 以及加解密链路集中在一个标准表单中。</p>
          </div>
        </template>

        <el-form label-position="top">
          <el-form-item label="URL">
            <el-input v-model="requestForm.url" placeholder="请输入请求地址" />
          </el-form-item>
          <el-form-item label="Method">
            <el-select v-model="requestForm.method">
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
              <el-option label="PATCH" value="PATCH" />
              <el-option label="DELETE" value="DELETE" />
            </el-select>
          </el-form-item>
          <el-form-item label="Headers JSON">
            <el-input v-model="requestForm.headersText" type="textarea" :rows="6" />
          </el-form-item>
          <el-form-item label="Body JSON">
            <el-input v-model="requestForm.bodyText" type="textarea" :rows="8" />
          </el-form-item>
          <el-form-item label="Encrypt URL">
            <el-input v-model="requestForm.encrypt_url" placeholder="可选，用于加密前置接口" />
          </el-form-item>
          <el-form-item label="Decrypt URL">
            <el-input v-model="requestForm.decrypt_url" placeholder="可选，用于解密回放接口" />
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <div>
            <p class="section-title">执行结果</p>
            <p class="section-caption">保留完整响应输出，方便核对状态、头部和业务字段。</p>
          </div>
          <span class="muted-text">{{ executeResult ? "已获取响应" : "尚未发送请求" }}</span>
        </div>
      </template>
      <pre class="json-box">{{ JSON.stringify(executeResult, null, 2) || "-- 等待执行请求 --" }}</pre>
    </el-card>
  </div>
</template>

<style scoped>
.product-panel {
  display: grid;
  gap: 16px;
}

.soft-panel span {
  display: block;
  color: var(--qm-text-secondary);
  font-size: 12px;
}

.soft-panel strong {
  display: block;
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-all;
}
</style>
