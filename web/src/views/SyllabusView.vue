<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchSyllabusTree, type SubjectSyllabus } from '../services/syllabus'

const subjects = ref<SubjectSyllabus[]>([])
const selectedSubjectId = ref<string>('')
const sourceFileCount = ref(0)
const loading = ref(true)
const error = ref('')

const selectedSubject = computed(
  () => subjects.value.find((subject) => subject.id === selectedSubjectId.value) ?? subjects.value[0],
)

const totalSourceRows = computed(() =>
  subjects.value.reduce((total, subject) => total + subject.source_row_count, 0),
)

const totalKnowledgePoints = computed(() =>
  subjects.value.reduce((total, subject) => total + subject.knowledge_point_count, 0),
)

onMounted(async () => {
  try {
    const tree = await fetchSyllabusTree()
    subjects.value = tree.subjects
    sourceFileCount.value = tree.versions.length
    selectedSubjectId.value = tree.subjects[0]?.id ?? ''
  } catch {
    error.value = '考纲树加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="page syllabus-page">
    <div class="syllabus-hero">
      <p class="eyebrow">
        P0-A · 考纲事实层
      </p>
      <h1>考纲知识点树</h1>
      <p class="summary">
        先把四科原始考纲导入为稳定、可重复生成的事实层，再用于后续阶段配比、任务池和确定性排程。
      </p>
    </div>

    <p
      v-if="loading"
      class="state-card"
    >
      正在加载考纲树…
    </p>
    <p
      v-else-if="error"
      class="state-card error"
    >
      {{ error }}
    </p>

    <template v-else-if="selectedSubject">
      <div class="summary-grid">
        <article>
          <span>版本记录</span>
          <strong>{{ sourceFileCount }}</strong>
        </article>
        <article>
          <span>原始条目</span>
          <strong>{{ totalSourceRows }}</strong>
        </article>
        <article>
          <span>知识点</span>
          <strong>{{ totalKnowledgePoints }}</strong>
        </article>
        <article>
          <span>当前科目</span>
          <strong>{{ selectedSubject.knowledge_point_count }}</strong>
        </article>
      </div>

      <div
        class="subject-tabs"
        aria-label="选择科目"
      >
        <button
          v-for="subject in subjects"
          :key="subject.id"
          :class="{ active: subject.id === selectedSubject.id }"
          type="button"
          @click="selectedSubjectId = subject.id"
        >
          <span>{{ subject.name }}</span>
          <small>{{ subject.source_row_count }} 条</small>
        </button>
      </div>

      <div class="tree-layout">
        <aside class="subject-panel">
          <h2>{{ selectedSubject.name }}</h2>
          <dl>
            <div>
              <dt>模块</dt>
              <dd>{{ selectedSubject.modules.length }}</dd>
            </div>
            <div>
              <dt>知识点</dt>
              <dd>{{ selectedSubject.knowledge_point_count }}</dd>
            </div>
            <div>
              <dt>考试结构</dt>
              <dd>{{ selectedSubject.exam_blueprints.length }}</dd>
            </div>
          </dl>
          <section
            v-for="blueprint in selectedSubject.exam_blueprints"
            :key="blueprint.id"
            class="exam-blueprint"
          >
            <h3>{{ blueprint.name }}</h3>
            <p>
              {{ blueprint.sections[0]?.name }}
            </p>
          </section>
        </aside>

        <div class="tree-card">
          <section
            v-for="module in selectedSubject.modules"
            :key="module.id"
            class="module-section"
          >
            <h2>{{ module.name }}</h2>
            <details
              v-for="chapter in module.chapters"
              :key="chapter.id"
            >
              <summary>{{ chapter.name }}</summary>
              <div class="chapter-body">
                <section
                  v-for="section in chapter.sections"
                  :key="section.id"
                  class="section-block"
                >
                  <h3>{{ section.name }}</h3>
                  <ul>
                    <li
                      v-for="point in section.knowledge_points"
                      :key="point.id"
                    >
                      <span>{{ point.name }}</span>
                      <small>{{ point.requirement_raw }}</small>
                    </li>
                  </ul>
                </section>
                <ul
                  v-if="chapter.knowledge_points.length"
                  class="chapter-points"
                >
                  <li
                    v-for="point in chapter.knowledge_points"
                    :key="point.id"
                  >
                    <span>{{ point.name }}</span>
                    <small>{{ point.requirement_raw }}</small>
                  </li>
                </ul>
              </div>
            </details>
          </section>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.syllabus-page {
  padding-top: 48px;
}

.syllabus-hero {
  max-width: 780px;
}

.syllabus-hero h1 {
  margin: 0;
  font-size: clamp(24px, 2.5vw, 30px);
  letter-spacing: -0.04em;
}

.state-card,
.summary-grid article,
.subject-panel,
.tree-card {
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
  box-shadow: var(--shadow-card);
}

.state-card {
  padding: 24px;
  color: var(--ink-soft);
}

.state-card.error {
  color: var(--danger);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 32px 0 20px;
}

.summary-grid article {
  padding: 20px;
}

.summary-grid span,
.subject-panel dt {
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 700;
}

.summary-grid strong {
  display: block;
  margin-top: 8px;
  font-size: 30px;
}

.subject-tabs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.subject-tabs button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  color: var(--ink-soft);
  background: white;
  cursor: pointer;
}

.subject-tabs button.active {
  border-color: var(--deep);
  color: var(--deep);
  background: var(--paper-warm);
}

.subject-tabs small {
  color: var(--ink-muted);
}

.tree-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.subject-panel,
.tree-card {
  padding: 24px;
}

.subject-panel {
  position: sticky;
  top: 96px;
}

.subject-panel h2 {
  margin: 0 0 18px;
}

.subject-panel dl {
  display: grid;
  gap: 12px;
  margin: 0;
}

.subject-panel dl div {
  display: flex;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--rule-soft);
}

.subject-panel dd {
  margin: 0;
  font-weight: 700;
}

.exam-blueprint {
  margin-top: 18px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--paper-warm);
}

.exam-blueprint h3,
.exam-blueprint p {
  margin: 0;
}

.exam-blueprint p {
  margin-top: 8px;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.6;
}

.module-section + .module-section {
  margin-top: 28px;
}

.module-section > h2 {
  margin: 0 0 12px;
  color: var(--deep);
}

details {
  border-top: 1px solid var(--rule-soft);
}

summary {
  padding: 16px 0;
  cursor: pointer;
  font-weight: 700;
}

.chapter-body {
  display: grid;
  gap: 14px;
  padding-bottom: 18px;
}

.section-block {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--paper-warm);
}

.section-block h3 {
  margin: 0 0 10px;
  font-size: 15px;
}

ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: white;
  color: var(--ink);
}

li small {
  flex: 0 0 auto;
  color: var(--deep);
  font-weight: 700;
}

.chapter-points {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--paper-warm);
}

@media (max-width: 920px) {
  .summary-grid,
  .subject-tabs,
  .tree-layout {
    grid-template-columns: 1fr;
  }

  .subject-panel {
    position: static;
  }
}
</style>
