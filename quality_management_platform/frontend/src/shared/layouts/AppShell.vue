<script setup lang="ts">
import { KeepAlive, computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import type { Component } from "vue";
import { useRoute } from "vue-router";
import {
  Calendar,
  Connection,
  DataAnalysis,
  Document,
  Expand,
  Files,
  Fold,
  Grid,
  List,
  Monitor,
  Promotion,
  Reading,
  Setting,
  Timer,
  Warning,
} from "@element-plus/icons-vue";

type MenuLeaf = {
  type: "item";
  path: string;
  label: string;
  subtitle: string;
  icon: Component;
};

type MenuSubmenu = {
  type: "submenu";
  label: string;
  icon: Component;
  children: MenuLeaf[];
};

type MenuGroup = {
  title: string;
  items: Array<MenuLeaf | MenuSubmenu>;
};

type ActiveMenuItem = MenuLeaf & {
  groupTitle: string;
  parentLabel?: string;
};

const route = useRoute();
const menuCollapsed = ref(false);
const collapsedTooltip = reactive({
  visible: false,
  text: "",
  x: 0,
  y: 0,
});

const menuGroups: MenuGroup[] = [
  {
    title: "需求协同",
    items: [
      {
        type: "item",
        path: "/requirements/business",
        label: "业务管理",
        subtitle: "管理业务线与归属关系",
        icon: Grid,
      },
      {
        type: "item",
        path: "/requirements/manage",
        label: "需求管理",
        subtitle: "统一维护需求条目",
        icon: Document,
      },
      {
        type: "item",
        path: "/requirements/stories",
        label: "故事管理",
        subtitle: "沉淀用户故事与拆解任务",
        icon: Reading,
      },
    ],
  },
  {
    title: "测试中心",
    items: [
      {
        type: "submenu",
        label: "用例管理",
        icon: List,
        children: [
          {
            type: "item",
            path: "/cases/library",
            label: "用例库",
            subtitle: "维护测试用例资产",
            icon: List,
          },
          {
            type: "item",
            path: "/cases/execution",
            label: "用例执行",
            subtitle: "查看与执行测试用例",
            icon: Promotion,
          },
        ],
      },
      {
        type: "item",
        path: "/defects/manage",
        label: "缺陷管理",
        subtitle: "跟踪缺陷流转与状态",
        icon: Warning,
      },
    ],
  },
  {
    title: "工具平台",
    items: [
      {
        type: "item",
        path: "/test-data",
        label: "测试数据",
        subtitle: "证件与模拟数据",
        icon: Files,
      },
      {
        type: "item",
        path: "/api-tool",
        label: "接口工具",
        subtitle: "接口调试与配置",
        icon: Monitor,
      },
      {
        type: "item",
        path: "/tool-cards",
        label: "工具卡片",
        subtitle: "工具资产中心",
        icon: Grid,
      },
    ],
  },
  {
    title: "自动化",
    items: [
      {
        type: "submenu",
        label: "接口自动化",
        icon: Connection,
        children: [
          {
            type: "item",
            path: "/interface-auto/templates",
            label: "接口模板",
            subtitle: "统一维护接口模板",
            icon: Document,
          },
          {
            type: "item",
            path: "/interface-auto/cases",
            label: "用例管理",
            subtitle: "维护接口自动化用例",
            icon: List,
          },
          {
            type: "item",
            path: "/interface-auto/test-suites",
            label: "测试集",
            subtitle: "组装用例集合并预留调度监控",
            icon: Files,
          },
          {
            type: "item",
            path: "/interface-auto/reports",
            label: "测试报告",
            subtitle: "查看执行结果与报告",
            icon: Files,
          },
          {
            type: "item",
            path: "/interface-auto/tools",
            label: "全局工具",
            subtitle: "管理通用工具能力",
            icon: Grid,
          },
          {
            type: "item",
            path: "/interface-auto/variables",
            label: "变量管理",
            subtitle: "沉淀全局变量与环境变量",
            icon: DataAnalysis,
          },
        ],
      },
      {
        type: "item",
        path: "/automation/ui",
        label: "UI 自动化",
        subtitle: "预留 UI 自动化能力",
        icon: Monitor,
      },
    ],
  },
  {
    title: "调度任务",
    items: [
      {
        type: "item",
        path: "/scheduler/tasks",
        label: "定时任务",
        subtitle: "统一管理平台调度配置",
        icon: Timer,
      },
    ],
  },
  {
    title: "迭代计划",
    items: [
      {
        type: "item",
        path: "/iterations/plan",
        label: "迭代版本",
        subtitle: "按日期组织每周迭代计划",
        icon: Calendar,
      },
    ],
  },
  {
    title: "数据服务",
    items: [
      {
        type: "item",
        path: "/data-query",
        label: "数据查询",
        subtitle: "SQL 查询与分析",
        icon: DataAnalysis,
      },
    ],
  },
];

const flatMenuItems = computed<ActiveMenuItem[]>(() =>
  menuGroups.flatMap((group) =>
    group.items.flatMap((item) => {
      if (item.type === "item") {
        return [{ ...item, groupTitle: group.title }];
      }

      return item.children.map((child) => ({
        ...child,
        groupTitle: group.title,
        parentLabel: item.label,
      }));
    }),
  ),
);

const activeModule = computed(() => {
  return (
    flatMenuItems.value.find((item) => item.path === route.path) ??
    flatMenuItems.value.find((item) => route.path.startsWith(item.path)) ??
    flatMenuItems.value[0]
  );
});

function handleWorkspaceShortcut(event: KeyboardEvent) {
  if (!(event.ctrlKey || event.metaKey)) {
    return;
  }
  const key = event.key.toLowerCase();
  if (key === "s") {
    if (route.name === "interface-auto-cases") {
      event.preventDefault();
      window.dispatchEvent(new CustomEvent("interface-auto:save-cases"));
      return;
    }
    if (route.name === "interface-auto-templates") {
      event.preventDefault();
      window.dispatchEvent(new CustomEvent("interface-auto:save-templates"));
    }
    return;
  }
  if (key === "w" && route.name === "interface-auto-cases") {
    event.preventDefault();
    window.dispatchEvent(new CustomEvent("interface-auto:close-case-tab"));
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleWorkspaceShortcut);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleWorkspaceShortcut);
});

function toggleMenu() {
  menuCollapsed.value = !menuCollapsed.value;
  collapsedTooltip.visible = false;
}

function showCollapsedTooltip(event: MouseEvent | FocusEvent, text: string) {
  if (!menuCollapsed.value) {
    return;
  }

  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const rect = target.getBoundingClientRect();
  collapsedTooltip.visible = true;
  collapsedTooltip.text = text;
  collapsedTooltip.x = rect.right + 14;
  collapsedTooltip.y = rect.top + rect.height / 2;
}

function hideCollapsedTooltip() {
  collapsedTooltip.visible = false;
}
</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': menuCollapsed }">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="brand">
          <div class="brand-mark">Q</div>
          <strong v-if="!menuCollapsed" class="brand-title">质量管理平台</strong>
        </div>

        <el-button class="collapse-button" text circle @click="toggleMenu">
          <el-icon><component :is="menuCollapsed ? Expand : Fold" /></el-icon>
        </el-button>
      </div>

      <div class="menu-scroll">
        <el-menu
          :default-active="activeModule.path"
          :collapse="menuCollapsed"
          class="side-menu"
          router
          unique-opened
        >
          <el-menu-item-group v-for="group in menuGroups" :key="group.title">
            <template #title>
              <span v-if="!menuCollapsed" class="menu-group-title">{{ group.title }}</span>
            </template>

            <template
              v-for="item in group.items"
              :key="item.type === 'item' ? item.path : `${group.title}-${item.label}`"
            >
              <el-menu-item
                v-if="item.type === 'item'"
                :index="item.path"
                @mouseenter="showCollapsedTooltip($event, item.label)"
                @mouseleave="hideCollapsedTooltip"
              >
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.label }}</span>
              </el-menu-item>

              <el-sub-menu
                v-else
                :index="`${group.title}-${item.label}`"
                @mouseenter="showCollapsedTooltip($event, item.label)"
                @mouseleave="hideCollapsedTooltip"
              >
                <template #title>
                  <el-icon><component :is="item.icon" /></el-icon>
                  <span>{{ item.label }}</span>
                </template>

                <el-menu-item
                  v-for="child in item.children"
                  :key="child.path"
                  :index="child.path"
                >
                  {{ child.label }}
                </el-menu-item>
              </el-sub-menu>
            </template>
          </el-menu-item-group>
        </el-menu>
      </div>

      <RouterLink
        to="/login"
        class="account-link"
        @mouseenter="showCollapsedTooltip($event, '账户')"
        @mouseleave="hideCollapsedTooltip"
      >
        <el-icon><Setting /></el-icon>
        <span v-if="!menuCollapsed">账户</span>
      </RouterLink>
    </aside>

    <section class="workspace">
      <main class="content">
        <router-view v-slot="{ Component, route: currentRoute }">
          <KeepAlive>
            <component :is="Component" :key="currentRoute.name ?? currentRoute.path" />
          </KeepAlive>
        </router-view>
      </main>
    </section>

    <transition name="collapsed-tooltip-fade">
      <div
        v-if="menuCollapsed && collapsedTooltip.visible"
        class="collapsed-tooltip"
        :style="{
          left: `${collapsedTooltip.x}px`,
          top: `${collapsedTooltip.y}px`,
        }"
      >
        {{ collapsedTooltip.text }}
      </div>
    </transition>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background: #f5f7fa;
  transition: grid-template-columns 0.2s ease;
}

.shell--collapsed {
  grid-template-columns: 72px minmax(0, 1fr);
}

.sidebar {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 0;
  overflow: hidden;
  padding: 12px 10px;
  border-right: 1px solid var(--qm-border);
  background: #ffffff;
}

.shell--collapsed .sidebar {
  padding-left: 0;
  padding-right: 0;
}

.sidebar-top {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 6px 10px;
}

.shell--collapsed .sidebar-top {
  flex-direction: column;
  justify-content: flex-start;
  gap: 10px;
  padding: 4px 0 12px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.shell--collapsed .brand {
  justify-content: center;
  width: 100%;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #1677ff;
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
  flex: 0 0 32px;
}

.brand-title {
  color: var(--qm-title);
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.collapse-button {
  margin: 0;
  color: #4e5969;
}

.collapse-button:hover {
  background: #f5f7fa;
}

.shell--collapsed .collapse-button {
  align-self: center;
}

.menu-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.side-menu {
  border-right: none;
}

.menu-group-title {
  color: var(--qm-text-secondary);
  font-size: 12px;
}

.account-link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  margin: 8px 6px 0;
  padding: 10px 12px;
  border-radius: 8px;
  color: #4e5969;
  text-decoration: none;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.account-link:hover {
  background: #f5f7fa;
}

.shell--collapsed .account-link {
  justify-content: center;
  margin: 8px 0 0;
  padding: 10px 0;
}

.workspace {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
  min-height: 0;
  overflow: hidden;
}

.content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 24px 24px;
}

.collapsed-tooltip {
  position: fixed;
  z-index: 40;
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.92);
  color: #ffffff;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: 1;
  white-space: nowrap;
  box-shadow:
    0 14px 28px rgba(15, 23, 42, 0.22),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
  pointer-events: none;
  transform: translateY(-50%);
}

.collapsed-tooltip::before {
  content: "";
  position: absolute;
  top: 50%;
  left: -5px;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: rgba(15, 23, 42, 0.92);
  transform: translateY(-50%) rotate(45deg);
}

.collapsed-tooltip-fade-enter-active,
.collapsed-tooltip-fade-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}

.collapsed-tooltip-fade-enter-from,
.collapsed-tooltip-fade-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(-4px);
}

:deep(.side-menu.el-menu) {
  border-right: none;
}

:deep(.side-menu.el-menu--collapse) {
  width: 100%;
}

:deep(.side-menu .el-menu-item-group__title) {
  padding-left: 12px;
}

:deep(.side-menu .el-menu-item .el-icon),
:deep(.side-menu .el-sub-menu__title .el-icon),
.account-link :deep(.el-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
}

:deep(.side-menu .el-menu-item),
:deep(.side-menu .el-sub-menu__title) {
  height: 40px;
  margin: 4px 6px;
  border-radius: 8px;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

:deep(.side-menu .el-menu-item:hover),
:deep(.side-menu .el-sub-menu__title:hover) {
  background: #f5f7fa;
}

:deep(.side-menu .el-menu-item.is-active) {
  background: #e6f4ff;
  color: var(--qm-primary);
}

:deep(.side-menu .el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--qm-primary);
}

:deep(.side-menu.el-menu--collapse .el-menu-item span),
:deep(.side-menu.el-menu--collapse .el-sub-menu__title span),
:deep(.side-menu.el-menu--collapse .el-sub-menu__icon-arrow) {
  display: none;
}

:deep(.side-menu.el-menu--collapse .el-menu-item),
:deep(.side-menu.el-menu--collapse .el-sub-menu__title) {
  width: 44px;
  height: 44px;
  justify-content: center;
  margin-left: auto;
  margin-right: auto;
  padding: 0;
  border-radius: 14px;
}

:deep(.side-menu.el-menu--collapse .el-menu-item-group__title) {
  display: none;
  height: 0;
  padding: 0;
  margin: 0;
}

:deep(.side-menu.el-menu--collapse .el-menu-item-group__wrap) {
  margin: 0;
}

:deep(.side-menu.el-menu--collapse .el-menu-item .el-icon),
:deep(.side-menu.el-menu--collapse .el-sub-menu__title .el-icon) {
  margin: 0;
}

.shell--collapsed :deep(.side-menu .el-menu-item:hover),
.shell--collapsed :deep(.side-menu .el-sub-menu__title:hover),
.shell--collapsed .account-link:hover {
  background: linear-gradient(180deg, #f9fbff 0%, #edf4ff 100%);
  box-shadow:
    inset 0 0 0 1px rgba(22, 119, 255, 0.08),
    0 8px 16px rgba(22, 119, 255, 0.08);
  transform: translateY(-1px);
}

.shell--collapsed :deep(.side-menu .el-menu-item.is-active),
.shell--collapsed :deep(.side-menu .el-sub-menu.is-active > .el-sub-menu__title) {
  background: linear-gradient(180deg, #edf5ff 0%, #dcecff 100%);
  color: var(--qm-primary);
  box-shadow:
    inset 0 0 0 1px rgba(22, 119, 255, 0.12),
    0 10px 18px rgba(22, 119, 255, 0.12);
}

.shell--collapsed :deep(.side-menu .el-menu-item.is-active:hover),
.shell--collapsed :deep(.side-menu .el-sub-menu.is-active > .el-sub-menu__title:hover) {
  background: linear-gradient(180deg, #e9f3ff 0%, #d6e8ff 100%);
}

@media (max-width: 960px) {
  .shell,
  .shell--collapsed {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 100vh;
  }

  .sidebar,
  .workspace {
    height: auto;
  }

  .menu-scroll,
  .content {
    overflow: visible;
  }

  .content {
    padding: 0 16px 16px;
  }

}
</style>
