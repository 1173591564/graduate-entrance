<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  createMaterial,
  deleteMaterial,
  fetchMaterials,
  reciteMaterial,
  updateMaterial,
  type EssayCategory,
  type EssayMaterial,
} from '../services/essay'

const CATEGORY_LABELS: Record<EssayCategory, string> = {
  phrase: '短语',
  sentence: '金句',
  paragraph: '段落',
  template: '模板',
  quote: '引用',
}

const materials = ref<EssayMaterial[]>([])
const dueMaterials = ref<EssayMaterial[]>([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const filterCategory = ref<EssayCategory | ''>('')
const searchInput = ref('')

const formOpen = ref(false)
const editingId = ref<string | null>(null)
const formTitle = ref('')
const formCategory = ref<EssayCategory>('sentence')
const formTopic = ref('')
const formContent = ref('')
const formTranslation = ref('')
const formSource = ref('')
const saving = ref(false)

const formValid = computed(
  () => formTitle.value.trim().length > 0 && formContent.value.trim().length > 0,
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [all, due] = await Promise.all([
      fetchMaterials({
        category: filterCategory.value || undefined,
        q: searchInput.value.trim() || undefined,
      }),
      fetchMaterials({ dueOnly: true }),
    ])
    materials.value = all.materials
    dueMaterials.value = due.materials
  } catch {
    error.value = '加载素材失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = null
  formTitle.value = ''
  formCategory.value = 'sentence'
  formTopic.value = ''
  formContent.value = ''
  formTranslation.value = ''
  formSource.value = ''
  formOpen.value = true
}

function openEdit(material: EssayMaterial): void {
  editingId.value = material.id
  formTitle.value = material.title
  formCategory.value = material.category
  formTopic.value = material.topic
  formContent.value = material.content_md
  formTranslation.value = material.translation_md
  formSource.value = material.source
  formOpen.value = true
}

async function save(): Promise<void> {
  if (!formValid.value || saving.value) {
    return
  }
  saving.value = true
  try {
    const payload = {
      title: formTitle.value.trim(),
      category: formCategory.value,
      topic: formTopic.value.trim(),
      content_md: formContent.value,
      translation_md: formTranslation.value,
      source: formSource.value.trim(),
    }
    if (editingId.value) {
      await updateMaterial(editingId.value, payload)
      notice.value = '素材已更新'
    } else {
      await createMaterial(payload)
      notice.value = '素材已添加，已排入今日背诵'
    }
    formOpen.value = false
    await load()
  } catch {
    error.value = '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

async function remove(material: EssayMaterial): Promise<void> {
  try {
    await deleteMaterial(material.id)
    notice.value = '素材已删除'
    await load()
  } catch {
    error.value = '删除失败，请稍后重试'
  }
}

async function recite(material: EssayMaterial, result: 'remembered' | 'forgot'): Promise<void> {
  try {
    const response = await reciteMaterial(material.id, result)
    notice.value =
      result === 'remembered'
        ? `已记住，下次背诵 ${response.next_due}`
        : `已标记遗忘，明天再背（${response.next_due}）`
    await load()
  } catch {
    error.value = '打卡失败，请稍后重试'
  }
}

onMounted(load)
</script>

<template>
  <section class="essay-view">
    <header class="page-header">
      <div>
        <h1>作文素材库</h1>
        <p>录入、分类、检索写作素材，按间隔计划背诵打卡。</p>
      </div>
      <button
        type="button"
        class="primary"
        @click="openCreate"
      >
        新增素材
      </button>
    </header>

    <p
      v-if="notice"
      class="notice"
    >
      {{ notice }}
    </p>
    <p
      v-if="error"
      class="error"
    >
      {{ error }}
    </p>

    <section
      v-if="dueMaterials.length > 0"
      class="due-panel"
    >
      <h2>今日待背诵（{{ dueMaterials.length }}）</h2>
      <article
        v-for="material in dueMaterials"
        :key="`due-${material.id}`"
        class="due-card"
      >
        <header>
          <strong>{{ material.title }}</strong>
          <span class="badge">{{ CATEGORY_LABELS[material.category] }}</span>
          <span
            v-if="material.topic"
            class="badge topic"
          >{{ material.topic }}</span>
        </header>
        <p class="content">
          {{ material.content_md }}
        </p>
        <p
          v-if="material.translation_md"
          class="translation"
        >
          {{ material.translation_md }}
        </p>
        <footer>
          <button
            type="button"
            class="primary"
            @click="recite(material, 'remembered')"
          >
            记住了
          </button>
          <button
            type="button"
            @click="recite(material, 'forgot')"
          >
            忘了
          </button>
        </footer>
      </article>
    </section>

    <form
      v-if="formOpen"
      class="material-form"
      @submit.prevent="save"
    >
      <h2>{{ editingId ? '编辑素材' : '新增素材' }}</h2>
      <label>
        标题
        <input
          v-model="formTitle"
          type="text"
          maxlength="240"
        >
      </label>
      <div class="form-row">
        <label>
          分类
          <select v-model="formCategory">
            <option
              v-for="(label, value) in CATEGORY_LABELS"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select>
        </label>
        <label>
          话题
          <input
            v-model="formTopic"
            type="text"
            maxlength="120"
            placeholder="如 environment / technology"
          >
        </label>
        <label>
          来源
          <input
            v-model="formSource"
            type="text"
            maxlength="240"
          >
        </label>
      </div>
      <label>
        内容
        <textarea
          v-model="formContent"
          rows="4"
        />
      </label>
      <label>
        翻译 / 注释
        <textarea
          v-model="formTranslation"
          rows="2"
        />
      </label>
      <footer>
        <button
          type="submit"
          class="primary"
          :disabled="!formValid || saving"
        >
          保存
        </button>
        <button
          type="button"
          @click="formOpen = false"
        >
          取消
        </button>
      </footer>
    </form>

    <section class="filters">
      <div class="category-pills">
        <button
          type="button"
          class="pill"
          :class="{ active: filterCategory === '' }"
          @click="filterCategory = ''; load()"
        >
          全部
        </button>
        <button
          v-for="(label, value) in CATEGORY_LABELS"
          :key="value"
          type="button"
          class="pill"
          :class="{ active: filterCategory === value }"
          @click="filterCategory = value; load()"
        >
          {{ label }}
        </button>
      </div>
      <div class="search-box">
        <input
          v-model="searchInput"
          type="search"
          placeholder="搜索标题 / 内容 / 翻译"
          @keyup.enter="load"
        >
        <button
          type="button"
          @click="load"
        >
          搜索
        </button>
      </div>
    </section>

    <p
      v-if="loading"
      class="empty-state"
    >
      加载中…
    </p>
    <div
      v-else-if="materials.length === 0"
      class="empty-state"
    >
      <span class="empty-icon">✍️</span>
      <strong>还没有素材</strong>
      <p>把背过的金句、模板、短语存进来，系统会按间隔计划提醒你背诵。</p>
      <button
        type="button"
        class="primary"
        @click="openCreate"
      >
        新增第一条素材
      </button>
    </div>
    <section
      v-else
      class="material-list"
    >
      <article
        v-for="material in materials"
        :key="material.id"
        class="material-card"
      >
        <header>
          <strong>{{ material.title }}</strong>
          <span class="badge">{{ CATEGORY_LABELS[material.category] }}</span>
          <span
            v-if="material.topic"
            class="badge topic"
          >{{ material.topic }}</span>
        </header>
        <p class="content">
          {{ material.content_md }}
        </p>
        <p
          v-if="material.translation_md"
          class="translation"
        >
          {{ material.translation_md }}
        </p>
        <footer>
          <span class="meta">
            已背 {{ material.recite_count }} 次
            <template v-if="material.due_date"> · 下次 {{ material.due_date }}</template>
            <template v-if="material.source"> · {{ material.source }}</template>
          </span>
          <span class="actions">
            <button
              type="button"
              @click="openEdit(material)"
            >
              编辑
            </button>
            <button
              type="button"
              class="danger"
              @click="remove(material)"
            >
              删除
            </button>
          </span>
        </footer>
      </article>
    </section>
  </section>
</template>

<style scoped>
.essay-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 920px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-header h1 {
  margin: 0 0 4px;
}

.page-header p {
  margin: 0;
  color: var(--color-text-muted, #667085);
}

.notice {
  background: #ecfdf3;
  border: 1px solid #abefc6;
  color: #067647;
  padding: 10px 14px;
  border-radius: 10px;
  margin: 0;
}

.error {
  background: #fef3f2;
  border: 1px solid #fecdca;
  color: #b42318;
  padding: 10px 14px;
  border-radius: 10px;
  margin: 0;
}

.due-panel {
  border: 1px solid #fedf89;
  background: #fffaeb;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.due-panel h2 {
  margin: 0;
  font-size: 1.05rem;
}

.due-card,
.material-card {
  border: 1px solid #e4e7ec;
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.due-card header,
.material-card header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  font-size: 0.78rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef4ff;
  color: #3538cd;
}

.badge.topic {
  background: #f0fdf9;
  color: #107569;
}

.content {
  margin: 0;
  white-space: pre-wrap;
}

.translation {
  margin: 0;
  color: #667085;
  white-space: pre-wrap;
}

.due-card footer,
.material-card footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta {
  color: #667085;
  font-size: 0.85rem;
}

.actions {
  display: flex;
  gap: 8px;
}

.material-form {
  border: 1px solid #e4e7ec;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fff;
}

.material-form h2 {
  margin: 0;
  font-size: 1.05rem;
}

.material-form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.9rem;
  flex: 1;
}

.form-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.material-form input,
.material-form select,
.material-form textarea,
.filters input,
.filters select {
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
}

.material-form footer {
  display: flex;
  gap: 10px;
}

.filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid #e4e7ec;
  border-radius: 14px;
  background: #fff;
}

.category-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pill {
  padding: 6px 14px;
  border: 1px solid #e4e7ec;
  border-radius: 999px;
  background: #fff;
  color: #526077;
  font-size: 0.88rem;
  font-weight: 600;
}

.pill.active {
  border-color: #2764e7;
  background: #edf4ff;
  color: #174cb7;
}

.search-box {
  display: flex;
  gap: 10px;
}

.search-box input[type='search'] {
  flex: 1;
  min-width: 200px;
  border: 1px solid #d0d5dd;
  border-radius: 10px;
  padding: 9px 12px;
  font: inherit;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 56px 24px;
  border: 1px dashed #d0d5dd;
  border-radius: 16px;
  background: #fff;
  color: #667085;
  text-align: center;
}

.empty-icon {
  font-size: 34px;
}

.empty-state strong {
  color: #16213a;
  font-size: 1.05rem;
}

.empty-state p {
  margin: 0;
  max-width: 380px;
}

.empty-state button {
  margin-top: 8px;
}

.material-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}

.material-list .material-card {
  height: 100%;
}

@media (max-width: 720px) {
  .material-list {
    grid-template-columns: 1fr;
  }
}

button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font: inherit;
}

button.primary {
  background: #444ce7;
  border-color: #444ce7;
  color: #fff;
}

button.danger {
  color: #b42318;
  border-color: #fecdca;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
