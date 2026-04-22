import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";

const AppShell = () => import("@/shared/layouts/AppShell.vue");
const LoginPage = () => import("@/modules/auth/LoginPage.vue");
const ApiToolPage = () => import("@/modules/api-tool/ApiToolWorkbenchPage.vue");
const ModulePlaceholderPage = () => import("@/modules/common/ModulePlaceholderPage.vue");
const DatabaseAssetPage = () => import("@/modules/data-assets/DatabaseAssetPage.vue");
const DataQueryPage = () => import("@/modules/data-query/DataQueryPage.vue");
const SchedulerTaskPage = () => import("@/modules/scheduler/SchedulerTaskPage.vue");
const ApiCasePage = () => import("@/modules/interface-auto/ApiCasePage.vue");
const ApiGlobalToolPage = () => import("@/modules/interface-auto/ApiGlobalToolPage.vue");
const ApiReportPage = () => import("@/modules/interface-auto/ApiReportPage.vue");
const ApiTestSuitePage = () => import("@/modules/interface-auto/ApiTestSuitePage.vue");
const ApiTemplatePage = () => import("@/modules/interface-auto/ApiTemplatePage.vue");
const ApiVariablePage = () => import("@/modules/interface-auto/ApiVariablePage.vue");
const BusinessManagementPage = () => import("@/modules/requirements/BusinessManagementPage.vue");
const TestDataPage = () => import("@/modules/test-data/TestDataPage.vue");
const ToolCardsPage = () => import("@/modules/tool-cards/ToolCardsPage.vue");

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
  },
  {
    path: "/",
    component: AppShell,
    children: [
      {
        path: "",
        redirect: "/test-data",
      },
      {
        path: "requirements/manage",
        name: "requirements-manage",
        component: ModulePlaceholderPage,
        meta: {
          title: "需求管理",
          subtitle: "统一维护需求条目、状态和基础信息。",
          note: "这里可继续接入需求列表、状态流转、负责人和迭代关联能力。",
        },
      },
      {
        path: "requirements/stories",
        name: "requirements-stories",
        component: ModulePlaceholderPage,
        meta: {
          title: "故事管理",
          subtitle: "沉淀用户故事、任务拆解和验收信息。",
          note: "这里可继续接入故事拆解、优先级、负责人和需求关联能力。",
        },
      },
      {
        path: "requirements/business",
        name: "requirements-business",
        component: BusinessManagementPage,
        meta: {
          title: "业务管理",
          subtitle: "统一维护业务线、业务域和归属关系。",
          note: "这里可继续接入业务线列表、归属映射、负责人和模块关联能力。",
        },
      },
      {
        path: "interface-auto",
        redirect: "/interface-auto/templates",
      },
      {
        path: "interface-auto/templates",
        name: "interface-auto-templates",
        component: ApiTemplatePage,
      },
      {
        path: "interface-auto/cases",
        name: "interface-auto-cases",
        component: ApiCasePage,
        meta: {
          title: "接口自动化用例管理",
          subtitle: "维护接口自动化用例、场景编排与执行配置。",
          note: "这里可继续接入接口用例目录、步骤编排、断言管理与项目关联能力。",
          useBusinessContext: true,
          contextTitle: "接口自动化项目上下文",
          contextSubtitle: "接口自动化用例管理已切换为读取全局业务组/项目主数据，后续真实页面直接复用该上下文。",
        },
      },
      {
        path: "interface-auto/test-suites",
        name: "interface-auto-test-suites",
        component: ApiTestSuitePage,
        meta: {
          title: "测试集",
          subtitle: "将用例组装为测试集合，并预留后续定时调度与自动化监控能力。",
          note: "当前页面先作为占位入口，后续可继续接入测试集编排、关联用例、定时任务调度和自动化监控能力。",
          useBusinessContext: true,
          contextTitle: "接口自动化测试集上下文",
          contextSubtitle: "测试集页面已接入全局业务组 / 项目上下文，后续测试集分组、调度和监控配置可直接复用。",
        },
      },
      {
        path: "interface-auto/reports",
        name: "interface-auto-reports",
        component: ApiReportPage,
        meta: {
          title: "接口自动化测试报告",
          subtitle: "查看自动化执行结果、趋势统计与报告详情。",
          note: "这里可继续接入报告列表、执行详情、趋势分析和失败回溯能力。",
          useBusinessContext: true,
          contextTitle: "接口自动化报告上下文",
          contextSubtitle: "报告页已预接全局业务组/项目上下文，后续可按项目维度查询与筛选报告。",
        },
      },
      {
        path: "interface-auto/tools",
        name: "interface-auto-tools",
        component: ApiGlobalToolPage,
        meta: {
          title: "接口自动化全局工具",
          subtitle: "统一维护自动化流程依赖的通用工具能力。",
          note: "这里可继续接入脚本工具、加解密工具、扩展组件和启停配置能力。",
        },
      },
      {
        path: "interface-auto/variables",
        name: "interface-auto-variables",
        component: ApiVariablePage,
        meta: {
          title: "接口自动化变量管理",
          subtitle: "沉淀全局变量、环境变量与跨项目公共配置。",
          note: "这里可继续接入变量分组、环境映射、加密存储和引用校验能力。",
        },
      },
      {
        path: "test-data",
        name: "test-data",
        component: TestDataPage,
      },
      {
        path: "cases/library",
        name: "cases-library",
        component: ModulePlaceholderPage,
        meta: {
          title: "用例库",
          subtitle: "统一维护测试用例资产和目录结构。",
          note: "这里可继续接入用例目录、用例详情、标签和版本关联能力。",
          useBusinessContext: true,
          contextTitle: "功能测试项目上下文",
          contextSubtitle: "功能测试用例库已接入全局业务组/项目主数据，后续用例目录和筛选将直接复用。",
        },
      },
      {
        path: "cases/execution",
        name: "cases-execution",
        component: ModulePlaceholderPage,
        meta: {
          title: "用例执行",
          subtitle: "查看和执行测试用例，沉淀执行结果。",
          note: "这里可继续接入执行记录、批量执行、结果回填和报告关联能力。",
          useBusinessContext: true,
          contextTitle: "测试执行项目上下文",
          contextSubtitle: "测试执行页已接入全局业务组/项目主数据，后续执行计划、批量运行和报告筛选可直接复用。",
        },
      },
      {
        path: "defects/manage",
        name: "defects-manage",
        component: ModulePlaceholderPage,
        meta: {
          title: "缺陷管理",
          subtitle: "统一跟踪缺陷状态、责任人和处理进度。",
          note: "这里可继续接入缺陷池、状态流转、严重级别和回归关联能力。",
          useBusinessContext: true,
          contextTitle: "缺陷归属项目上下文",
          contextSubtitle: "缺陷管理已接入全局业务组/项目主数据，后续缺陷归属和回归关联可直接复用。",
        },
      },
      {
        path: "automation/ui",
        name: "automation-ui",
        component: ModulePlaceholderPage,
        meta: {
          title: "UI 自动化",
          subtitle: "预留 UI 自动化编排和执行入口。",
          note: "这里可继续接入 UI 自动化脚本管理、执行任务和报告能力。",
          useBusinessContext: true,
          contextTitle: "测试平台项目上下文",
          contextSubtitle: "测试平台已接入全局业务组/项目主数据，后续 UI 自动化脚本、任务和报告都可直接复用。",
        },
      },
      {
        path: "automation/performance",
        name: "automation-performance",
        component: ModulePlaceholderPage,
        meta: {
          title: "性能压测",
          subtitle: "预留性能压测场景编排、执行和报告入口。",
          note: "这里可继续接入压测脚本管理、压测任务、资源监控和趋势报告能力。",
          useBusinessContext: true,
          contextTitle: "测试平台项目上下文",
          contextSubtitle: "性能压测已接入全局业务组/项目主数据，后续压测场景、执行记录和报告都可直接复用。",
        },
      },
      {
        path: "automation/coverage",
        name: "automation-coverage",
        component: ModulePlaceholderPage,
        meta: {
          title: "代码覆盖率",
          subtitle: "预留覆盖率数据采集、分析和趋势入口。",
          note: "这里可继续接入覆盖率任务、报告上传、变更对比和质量门禁能力。",
          useBusinessContext: true,
          contextTitle: "测试平台项目上下文",
          contextSubtitle: "代码覆盖率已接入全局业务组/项目主数据，后续覆盖率报告、质量门禁和趋势筛选都可直接复用。",
        },
      },
      {
        path: "api-tool",
        name: "api-tool",
        component: ApiToolPage,
      },
      {
        path: "tool-cards",
        name: "tool-cards",
        component: ToolCardsPage,
      },
      {
        path: "data-assets/databases",
        name: "data-assets-databases",
        component: DatabaseAssetPage,
        meta: {
          title: "数据库资产",
          subtitle: "按业务维护数据库连接信息，供查询、自动化和工具配置复用。",
        },
      },
      {
        path: "data-query",
        name: "data-query",
        component: DataQueryPage,
      },
      {
        path: "scheduler/tasks",
        name: "scheduler-tasks",
        component: SchedulerTaskPage,
        meta: {
          title: "定时任务",
          subtitle: "统一管理自动化任务和平台级调度配置。",
          note: "这里可继续接入定时任务管理、启停控制、调度日志和任务类型扩展能力。",
        },
      },
      {
        path: "iterations/plan",
        name: "iterations-plan",
        component: ModulePlaceholderPage,
        meta: {
          title: "迭代版本",
          subtitle: "按日期维护每周迭代，并关联需求、故事和测试用例。",
          note: "这里可继续接入迭代日期管理、需求关联、用例关联和周计划视图能力。",
        },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
