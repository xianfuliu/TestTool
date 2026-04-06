import { computed, ref } from "vue";

import {
  fetchBusinessGroups,
  fetchProjects,
  type BusinessGroupRecord,
  type ProjectRecord,
} from "@/shared/api/businessManagement";

const GROUP_STORAGE_KEY = "qm_active_business_group_id";
const PROJECT_STORAGE_KEY = "qm_active_project_id";

const groups = ref<BusinessGroupRecord[]>([]);
const projects = ref<ProjectRecord[]>([]);
const loading = ref(false);
const selectedGroupId = ref<number | null>(readStoredNumber(GROUP_STORAGE_KEY));
const selectedProjectId = ref<number | null>(readStoredNumber(PROJECT_STORAGE_KEY));

let initialized = false;
let pendingPromise: Promise<void> | null = null;

function readStoredNumber(key: string) {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function writeStoredNumber(key: string, value: number | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (value === null) {
    window.localStorage.removeItem(key);
    return;
  }
  window.localStorage.setItem(key, String(value));
}

function syncSelection() {
  if (selectedProjectId.value !== null) {
    const currentProject = projects.value.find((item) => item.id === selectedProjectId.value) ?? null;
    if (currentProject) {
      selectedGroupId.value = currentProject.business_group_id;
      writeStoredNumber(GROUP_STORAGE_KEY, selectedGroupId.value);
      writeStoredNumber(PROJECT_STORAGE_KEY, selectedProjectId.value);
      return;
    }
    selectedProjectId.value = null;
    writeStoredNumber(PROJECT_STORAGE_KEY, null);
  }

  if (selectedGroupId.value !== null) {
    const currentGroup = groups.value.find((item) => item.id === selectedGroupId.value) ?? null;
    if (currentGroup) {
      writeStoredNumber(GROUP_STORAGE_KEY, selectedGroupId.value);
      return;
    }
    selectedGroupId.value = null;
    writeStoredNumber(GROUP_STORAGE_KEY, null);
  }

  if (groups.value.length) {
    selectedGroupId.value = groups.value[0].id;
    writeStoredNumber(GROUP_STORAGE_KEY, selectedGroupId.value);
  }
}

async function load(force = false) {
  if (!force && initialized) {
    return;
  }
  if (pendingPromise) {
    return pendingPromise;
  }

  pendingPromise = (async () => {
    loading.value = true;
    try {
      const [groupRows, projectRows] = await Promise.all([fetchBusinessGroups(), fetchProjects()]);
      groups.value = groupRows;
      projects.value = projectRows;
      initialized = true;
      syncSelection();
    } finally {
      loading.value = false;
      pendingPromise = null;
    }
  })();

  return pendingPromise;
}

function setGroup(groupId: number | null) {
  selectedGroupId.value = groupId;
  writeStoredNumber(GROUP_STORAGE_KEY, groupId);

  if (selectedProjectId.value !== null) {
    const currentProject = projects.value.find((item) => item.id === selectedProjectId.value) ?? null;
    if (!currentProject || currentProject.business_group_id !== groupId) {
      selectedProjectId.value = null;
      writeStoredNumber(PROJECT_STORAGE_KEY, null);
    }
  }
}

function setProject(projectId: number | null) {
  if (projectId === null) {
    selectedProjectId.value = null;
    writeStoredNumber(PROJECT_STORAGE_KEY, null);
    return;
  }

  const currentProject = projects.value.find((item) => item.id === projectId) ?? null;
  if (!currentProject) {
    selectedProjectId.value = null;
    writeStoredNumber(PROJECT_STORAGE_KEY, null);
    return;
  }

  selectedProjectId.value = currentProject.id;
  selectedGroupId.value = currentProject.business_group_id;
  writeStoredNumber(PROJECT_STORAGE_KEY, currentProject.id);
  writeStoredNumber(GROUP_STORAGE_KEY, currentProject.business_group_id);
}

export function useBusinessProjectContext() {
  const selectedGroup = computed(() => groups.value.find((item) => item.id === selectedGroupId.value) ?? null);
  const selectedProject = computed(() => projects.value.find((item) => item.id === selectedProjectId.value) ?? null);
  const projectsOfSelectedGroup = computed(() => {
    if (selectedGroupId.value === null) {
      return projects.value;
    }
    return projects.value.filter((item) => item.business_group_id === selectedGroupId.value);
  });

  return {
    groups,
    projects,
    loading,
    selectedGroupId,
    selectedProjectId,
    selectedGroup,
    selectedProject,
    projectsOfSelectedGroup,
    ensureLoaded: () => load(false),
    refresh: () => load(true),
    setGroup,
    setProject,
  };
}
