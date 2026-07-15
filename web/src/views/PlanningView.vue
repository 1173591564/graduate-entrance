<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  createAvailabilityException,
  createAvailabilityPeriod,
  createMaterial,
  createPlanPhase,
  createTaskTemplate,
  deleteAvailabilityException,
  deleteAvailabilityPeriod,
  deleteMaterial,
  deletePlanPhase,
  deleteTaskTemplate,
  fetchPlanningConfig,
  type MaterialType,
  type PlanningConfig,
  type TaskType,
} from '../services/planning'

const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const materialTypes: Array<{ value: MaterialType; label: string }> = [
  { value: 'textbook', label: '教材 / 讲义' },
  { value: 'exercise_book', label: '习题册' },
  { value: 'past_paper', label: '真题卷' },
  { value: 'course', label: '课程' },
  { value: 'vocabulary', label: '词汇资料' },
  { value: 'other', label: '其他' },
]
const taskTypes: Array<{ value: TaskType; label: string }> = [
  { value: 'reading', label: '读书' },
  { value: 'practice', label: '习题' },
  { value: 'dictation', label: '默写' },
  { value: 'past_paper', label: '真题' },
  { value: 'memorization', label: '背诵' },
  { value: 'review', label: '复盘' },
]

const config = ref<PlanningConfig | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const phaseRatios = reactive<Record<string, number>>({})
const weekdayHours = reactive([8, 8, 8, 8, 8, 10, 10])

const phaseForm = reactive({
  name: '',
  start_date: '',
  end_date: '',
  description: '',
  milestones: '',
  allow_new_tasks: true,
})
const periodForm = reactive({
  name: '',
  start_date: '',
  end_date: '',
  weekly_target_hours: 50,
})
const exceptionForm = reactive({
  date: '',
  available_hours: 0,
  reason: '',
})
const materialForm = reactive({
  subject_id: '',
  name: '',
  material_type: 'textbook' as MaterialType,
  source: '',
  description: '',
})
const templateForm = reactive({
  subject_id: '',
  material_id: '',
  name: '',
  task_type: 'reading' as TaskType,
  default_est_minutes: 60,
  description: '',
  phase_ids: [] as string[],
})

const ratioTotal = computed(() =>
  Object.values(phaseRatios).reduce((total, percentage) => total + Number(percentage || 0), 0),
)
const templateMaterials = computed(
  () =>
    config.value?.materials.filter(
      (material) =>
        material.subject_id === null || material.subject_id === templateForm.subject_id,
    ) ?? [],
)

function formatHours(minutes: number): string {
  const hours = minutes / 60
  return Number.isInteger(hours) ? `${hours}h` : `${hours.toFixed(1)}h`
}

function subjectName(subjectId: string | null): string {
  if (subjectId === null) {
    return '全科'
  }
  return config.value?.subjects.find((subject) => subject.id === subjectId)?.name ?? '未知科目'
}

function phaseName(phaseId: string): string {
  return config.value?.phases.find((phase) => phase.id === phaseId)?.name ?? '未知阶段'
}

async function loadConfig(): Promise<void> {
  config.value = await fetchPlanningConfig()
  for (const subject of config.value.subjects) {
    if (!(subject.id in phaseRatios)) {
      phaseRatios[subject.id] = 0
    }
  }
  templateForm.subject_id ||= config.value.subjects[0]?.id ?? ''
}

async function runMutation(action: () => Promise<unknown>, successMessage: string): Promise<void> {
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await action()
    await loadConfig()
    notice.value = successMessage
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '保存失败'
  } finally {
    busy.value = false
  }
}

async function submitPhase(): Promise<void> {
  if (phaseForm.allow_new_tasks && ratioTotal.value !== 100) {
    error.value = '允许新任务时，四科配比之和必须为 100%'
    return
  }
  const subjectRatios = phaseForm.allow_new_tasks
    ? (config.value?.subjects.map((subject) => ({
        subject_id: subject.id,
        percentage: Number(phaseRatios[subject.id] ?? 0),
      })) ?? [])
    : []
  await runMutation(
    () =>
      createPlanPhase({
        name: phaseForm.name,
        start_date: phaseForm.start_date,
        end_date: phaseForm.end_date,
        description: phaseForm.description,
        milestones: phaseForm.milestones
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean),
        allow_new_tasks: phaseForm.allow_new_tasks,
        order: config.value?.phases.length ?? 0,
        subject_ratios: subjectRatios,
      }),
    '阶段已保存',
  )
  phaseForm.name = ''
  phaseForm.start_date = ''
  phaseForm.end_date = ''
  phaseForm.description = ''
  phaseForm.milestones = ''
}

async function submitAvailabilityPeriod(): Promise<void> {
  await runMutation(
    () =>
      createAvailabilityPeriod({
        name: periodForm.name,
        start_date: periodForm.start_date,
        end_date: periodForm.end_date,
        weekly_target_minutes: Math.round(periodForm.weekly_target_hours * 60),
        order: config.value?.availability_periods.length ?? 0,
        rules: weekdayHours.map((hours, weekday) => ({
          weekday,
          available_minutes: Math.round(Number(hours) * 60),
        })),
      }),
    '可用时段已保存',
  )
  periodForm.name = ''
  periodForm.start_date = ''
  periodForm.end_date = ''
}

async function submitAvailabilityException(): Promise<void> {
  await runMutation(
    () =>
      createAvailabilityException({
        date: exceptionForm.date,
        available_minutes: Math.round(exceptionForm.available_hours * 60),
        reason: exceptionForm.reason,
      }),
    '例外日期已保存',
  )
  exceptionForm.date = ''
  exceptionForm.available_hours = 0
  exceptionForm.reason = ''
}

async function submitMaterial(): Promise<void> {
  await runMutation(
    () =>
      createMaterial({
        subject_id: materialForm.subject_id || null,
        name: materialForm.name,
        material_type: materialForm.material_type,
        source: materialForm.source,
        description: materialForm.description,
        active: true,
        order: config.value?.materials.length ?? 0,
      }),
    '资料已保存',
  )
  materialForm.name = ''
  materialForm.source = ''
  materialForm.description = ''
}

async function submitTemplate(): Promise<void> {
  if (templateForm.phase_ids.length === 0) {
    error.value = '任务模板至少选择一个适用阶段'
    return
  }
  await runMutation(
    () =>
      createTaskTemplate({
        subject_id: templateForm.subject_id,
        material_id: templateForm.material_id || null,
        name: templateForm.name,
        task_type: templateForm.task_type,
        default_est_minutes: templateForm.default_est_minutes,
        description: templateForm.description,
        active: true,
        order: config.value?.task_templates.length ?? 0,
        phase_ids: templateForm.phase_ids,
      }),
    '任务模板已保存',
  )
  templateForm.name = ''
  templateForm.material_id = ''
  templateForm.description = ''
  templateForm.phase_ids = []
}

onMounted(async () => {
  try {
    await loadConfig()
  } catch {
    error.value = '规划配置加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="page planning-page">
    <header class="planning-hero">
      <div>
        <p class="eyebrow">
          P0-B · 排程输入层
        </p>
        <h1>阶段与任务配置</h1>
        <p>
          先定义阶段配比、每日可用学时、资料和任务模板；下一纵切片将据此生成确定性日历。
        </p>
      </div>
      <RouterLink
        class="secondary-link"
        to="/syllabus"
      >
        返回考纲树
      </RouterLink>
    </header>

    <p
      v-if="loading"
      class="state-card"
    >
      正在加载规划配置…
    </p>
    <p
      v-else-if="!config"
      class="state-card error"
    >
      {{ error }}
    </p>

    <template v-else>
      <p
        v-if="error"
        class="feedback error"
      >
        {{ error }}
      </p>
      <p
        v-if="notice"
        class="feedback success"
      >
        {{ notice }}
      </p>

      <nav
        class="section-nav"
        aria-label="规划配置分区"
      >
        <a href="#phases">阶段配比</a>
        <a href="#availability">可用时段</a>
        <a href="#materials">资料库</a>
        <a href="#templates">任务模板</a>
      </nav>

      <section
        id="phases"
        class="config-section"
      >
        <div class="section-heading">
          <div>
            <span>01</span>
            <h2>阶段与四科配比</h2>
          </div>
          <strong>{{ config.phases.length }} 个阶段</strong>
        </div>
        <div class="split-layout">
          <form
            class="config-form"
            @submit.prevent="submitPhase"
          >
            <label>
              阶段名称
              <input
                v-model.trim="phaseForm.name"
                data-testid="phase-name"
                placeholder="基础期"
                required
              >
            </label>
            <div class="two-columns">
              <label>
                开始日期
                <input
                  v-model="phaseForm.start_date"
                  data-testid="phase-start"
                  type="date"
                  required
                >
              </label>
              <label>
                结束日期
                <input
                  v-model="phaseForm.end_date"
                  data-testid="phase-end"
                  type="date"
                  required
                >
              </label>
            </div>
            <label class="toggle-row">
              <input
                v-model="phaseForm.allow_new_tasks"
                type="checkbox"
              >
              该阶段允许排入新任务
            </label>
            <fieldset :disabled="!phaseForm.allow_new_tasks">
              <legend>四科时间配比 · 当前 {{ ratioTotal }}%</legend>
              <div class="ratio-grid">
                <label
                  v-for="subject in config.subjects"
                  :key="subject.id"
                >
                  {{ subject.name }}
                  <span>
                    <input
                      v-model.number="phaseRatios[subject.id]"
                      :data-testid="`ratio-${subject.code}`"
                      type="number"
                      min="0"
                      max="100"
                    >
                    %
                  </span>
                </label>
              </div>
            </fieldset>
            <label>
              阶段主线
              <textarea
                v-model.trim="phaseForm.description"
                rows="3"
                placeholder="本阶段学习重点"
              />
            </label>
            <label>
              里程碑（每行一条）
              <textarea
                v-model="phaseForm.milestones"
                rows="3"
                placeholder="1000 题完成 ≥80%"
              />
            </label>
            <button
              data-testid="submit-phase"
              type="submit"
              :disabled="busy"
            >
              保存阶段
            </button>
          </form>
          <div class="record-list">
            <article
              v-for="phase in config.phases"
              :key="phase.id"
            >
              <div class="record-title">
                <div>
                  <small>{{ phase.start_date }} — {{ phase.end_date }}</small>
                  <h3>{{ phase.name }}</h3>
                </div>
                <button
                  type="button"
                  :disabled="busy"
                  @click="runMutation(() => deletePlanPhase(phase.id), '阶段已删除')"
                >
                  删除
                </button>
              </div>
              <p>{{ phase.description || '未填写阶段主线' }}</p>
              <div
                v-if="phase.subject_ratios.length"
                class="tag-row"
              >
                <span
                  v-for="ratio in phase.subject_ratios"
                  :key="ratio.subject_id"
                >
                  {{ subjectName(ratio.subject_id) }} {{ ratio.percentage }}%
                </span>
              </div>
              <span
                v-else
                class="muted"
              >
                维稳阶段：不排新任务
              </span>
            </article>
            <p
              v-if="config.phases.length === 0"
              class="empty-state"
            >
              尚未配置阶段。
            </p>
          </div>
        </div>
      </section>

      <section
        id="availability"
        class="config-section"
      >
        <div class="section-heading">
          <div>
            <span>02</span>
            <h2>Availability</h2>
          </div>
          <strong>{{ config.availability_periods.length }} 套周模板</strong>
        </div>
        <div class="split-layout">
          <div class="form-stack">
            <form
              class="config-form"
              @submit.prevent="submitAvailabilityPeriod"
            >
              <label>
                周模板名称
                <input
                  v-model.trim="periodForm.name"
                  placeholder="暑假"
                  required
                >
              </label>
              <div class="two-columns">
                <label>
                  开始日期
                  <input
                    v-model="periodForm.start_date"
                    type="date"
                    required
                  >
                </label>
                <label>
                  结束日期
                  <input
                    v-model="periodForm.end_date"
                    type="date"
                    required
                  >
                </label>
              </div>
              <label>
                每周目标小时
                <input
                  v-model.number="periodForm.weekly_target_hours"
                  type="number"
                  min="0"
                  max="168"
                  step="0.5"
                  required
                >
              </label>
              <fieldset>
                <legend>每天可用小时</legend>
                <div class="weekday-grid">
                  <label
                    v-for="(weekday, index) in weekdays"
                    :key="weekday"
                  >
                    {{ weekday }}
                    <input
                      v-model.number="weekdayHours[index]"
                      type="number"
                      min="0"
                      max="24"
                      step="0.5"
                    >
                  </label>
                </div>
              </fieldset>
              <button
                type="submit"
                :disabled="busy"
              >
                保存周模板
              </button>
            </form>

            <form
              class="config-form compact"
              @submit.prevent="submitAvailabilityException"
            >
              <h3>例外日期 / 请假</h3>
              <div class="two-columns">
                <label>
                  日期
                  <input
                    v-model="exceptionForm.date"
                    type="date"
                    required
                  >
                </label>
                <label>
                  可用小时
                  <input
                    v-model.number="exceptionForm.available_hours"
                    type="number"
                    min="0"
                    max="24"
                    step="0.5"
                    required
                  >
                </label>
              </div>
              <label>
                原因
                <input
                  v-model.trim="exceptionForm.reason"
                  placeholder="请假 / 模考 / 返校"
                >
              </label>
              <button
                type="submit"
                :disabled="busy"
              >
                保存例外
              </button>
            </form>
          </div>

          <div class="record-list">
            <article
              v-for="period in config.availability_periods"
              :key="period.id"
            >
              <div class="record-title">
                <div>
                  <small>{{ period.start_date }} — {{ period.end_date }}</small>
                  <h3>{{ period.name }}</h3>
                </div>
                <button
                  type="button"
                  :disabled="busy"
                  @click="
                    runMutation(
                      () => deleteAvailabilityPeriod(period.id),
                      '可用时段已删除',
                    )
                  "
                >
                  删除
                </button>
              </div>
              <p>周目标 {{ formatHours(period.weekly_target_minutes) }}</p>
              <div class="week-summary">
                <span
                  v-for="rule in period.rules"
                  :key="rule.weekday"
                >
                  {{ weekdays[rule.weekday] }} {{ formatHours(rule.available_minutes) }}
                </span>
              </div>
            </article>
            <article
              v-for="exception in config.availability_exceptions"
              :key="exception.id"
              class="exception-card"
            >
              <div class="record-title">
                <div>
                  <small>例外日期</small>
                  <h3>{{ exception.date }}</h3>
                </div>
                <button
                  type="button"
                  :disabled="busy"
                  @click="
                    runMutation(
                      () => deleteAvailabilityException(exception.id),
                      '例外日期已删除',
                    )
                  "
                >
                  删除
                </button>
              </div>
              <p>{{ formatHours(exception.available_minutes) }} · {{ exception.reason || '无说明' }}</p>
            </article>
            <p
              v-if="
                config.availability_periods.length === 0 &&
                  config.availability_exceptions.length === 0
              "
              class="empty-state"
            >
              尚未配置可用时段。
            </p>
          </div>
        </div>
      </section>

      <section
        id="materials"
        class="config-section"
      >
        <div class="section-heading">
          <div>
            <span>03</span>
            <h2>资料库</h2>
          </div>
          <strong>{{ config.materials.length }} 份资料</strong>
        </div>
        <div class="split-layout">
          <form
            class="config-form"
            @submit.prevent="submitMaterial"
          >
            <label>
              适用科目
              <select v-model="materialForm.subject_id">
                <option value="">
                  全科通用
                </option>
                <option
                  v-for="subject in config.subjects"
                  :key="subject.id"
                  :value="subject.id"
                >
                  {{ subject.name }}
                </option>
              </select>
            </label>
            <label>
              资料名称
              <input
                v-model.trim="materialForm.name"
                placeholder="王道数据结构"
                required
              >
            </label>
            <label>
              类型
              <select v-model="materialForm.material_type">
                <option
                  v-for="type in materialTypes"
                  :key="type.value"
                  :value="type.value"
                >
                  {{ type.label }}
                </option>
              </select>
            </label>
            <label>
              来源
              <input
                v-model.trim="materialForm.source"
                placeholder="出版社 / 课程平台"
              >
            </label>
            <label>
              说明
              <textarea
                v-model.trim="materialForm.description"
                rows="3"
              />
            </label>
            <button
              type="submit"
              :disabled="busy"
            >
              添加资料
            </button>
          </form>
          <div class="record-list material-grid">
            <article
              v-for="material in config.materials"
              :key="material.id"
            >
              <div class="record-title">
                <div>
                  <small>{{ subjectName(material.subject_id) }}</small>
                  <h3>{{ material.name }}</h3>
                </div>
                <button
                  type="button"
                  :disabled="busy"
                  @click="runMutation(() => deleteMaterial(material.id), '资料已删除')"
                >
                  删除
                </button>
              </div>
              <p>{{ material.source || material.description || '未填写来源' }}</p>
            </article>
            <p
              v-if="config.materials.length === 0"
              class="empty-state"
            >
              尚未添加资料。
            </p>
          </div>
        </div>
      </section>

      <section
        id="templates"
        class="config-section"
      >
        <div class="section-heading">
          <div>
            <span>04</span>
            <h2>任务模板</h2>
          </div>
          <strong>{{ config.task_templates.length }} 个模板</strong>
        </div>
        <div class="split-layout">
          <form
            class="config-form"
            @submit.prevent="submitTemplate"
          >
            <label>
              科目
              <select
                v-model="templateForm.subject_id"
                required
              >
                <option
                  v-for="subject in config.subjects"
                  :key="subject.id"
                  :value="subject.id"
                >
                  {{ subject.name }}
                </option>
              </select>
            </label>
            <label>
              关联资料
              <select v-model="templateForm.material_id">
                <option value="">
                  不关联资料
                </option>
                <option
                  v-for="material in templateMaterials"
                  :key="material.id"
                  :value="material.id"
                >
                  {{ material.name }}
                </option>
              </select>
            </label>
            <label>
              模板名称
              <input
                v-model.trim="templateForm.name"
                placeholder="王道章节学习"
                required
              >
            </label>
            <div class="two-columns">
              <label>
                任务类型
                <select v-model="templateForm.task_type">
                  <option
                    v-for="type in taskTypes"
                    :key="type.value"
                    :value="type.value"
                  >
                    {{ type.label }}
                  </option>
                </select>
              </label>
              <label>
                默认分钟
                <input
                  v-model.number="templateForm.default_est_minutes"
                  type="number"
                  min="1"
                  max="1440"
                  required
                >
              </label>
            </div>
            <fieldset>
              <legend>适用阶段</legend>
              <div class="checkbox-grid">
                <label
                  v-for="phase in config.phases"
                  :key="phase.id"
                >
                  <input
                    v-model="templateForm.phase_ids"
                    type="checkbox"
                    :value="phase.id"
                  >
                  {{ phase.name }}
                </label>
              </div>
            </fieldset>
            <label>
              执行说明
              <textarea
                v-model.trim="templateForm.description"
                rows="3"
              />
            </label>
            <button
              type="submit"
              :disabled="busy || config.phases.length === 0"
            >
              添加任务模板
            </button>
          </form>
          <div class="record-list">
            <article
              v-for="template in config.task_templates"
              :key="template.id"
            >
              <div class="record-title">
                <div>
                  <small>{{ subjectName(template.subject_id) }} · {{ template.default_est_minutes }} 分钟</small>
                  <h3>{{ template.name }}</h3>
                </div>
                <button
                  type="button"
                  :disabled="busy"
                  @click="
                    runMutation(() => deleteTaskTemplate(template.id), '任务模板已删除')
                  "
                >
                  删除
                </button>
              </div>
              <p>{{ template.description || '未填写执行说明' }}</p>
              <div class="tag-row">
                <span
                  v-for="phaseId in template.phase_ids"
                  :key="phaseId"
                >
                  {{ phaseName(phaseId) }}
                </span>
              </div>
            </article>
            <p
              v-if="config.task_templates.length === 0"
              class="empty-state"
            >
              尚未添加任务模板。
            </p>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.planning-page {
  padding-top: 48px;
}

.planning-hero,
.section-heading,
.record-title,
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.planning-hero {
  gap: 32px;
  margin-bottom: 28px;
}

.planning-hero > div {
  max-width: 760px;
}

.eyebrow {
  margin: 0 0 10px;
  color: #2764e7;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 56px);
  letter-spacing: -0.04em;
}

.planning-hero p:last-child {
  margin: 16px 0 0;
  color: #647087;
  line-height: 1.8;
}

.secondary-link,
.section-nav a,
.tag-row span {
  border-radius: 999px;
  font-weight: 750;
}

.secondary-link {
  flex: 0 0 auto;
  padding: 10px 16px;
  color: #174cb7;
  background: #edf4ff;
}

.state-card,
.feedback,
.section-nav,
.config-section,
.config-form,
.record-list article {
  border: 1px solid #e1e7f0;
  background: white;
  box-shadow: 0 18px 45px rgb(40 55 90 / 8%);
}

.state-card,
.feedback {
  padding: 18px 20px;
  border-radius: 16px;
}

.feedback.success {
  color: #166534;
  background: #f0fdf4;
}

.feedback.error,
.state-card.error {
  color: #a12626;
  background: #fff7f7;
}

.section-nav {
  position: sticky;
  z-index: 3;
  top: 12px;
  display: flex;
  gap: 8px;
  margin: 24px 0;
  padding: 10px;
  border-radius: 18px;
}

.section-nav a {
  padding: 9px 14px;
  color: #526077;
}

.section-nav a:hover {
  color: #174cb7;
  background: #edf4ff;
}

.config-section {
  scroll-margin-top: 90px;
  margin-top: 24px;
  padding: 28px;
  border-radius: 24px;
}

.section-heading {
  gap: 20px;
  margin-bottom: 24px;
}

.section-heading > div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-heading span {
  color: #2764e7;
  font-size: 13px;
  font-weight: 850;
}

.section-heading h2 {
  margin: 0;
}

.section-heading strong {
  color: #647087;
  font-size: 14px;
}

.split-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.85fr) minmax(0, 1.15fr);
  gap: 22px;
  align-items: start;
}

.form-stack,
.record-list,
.config-form {
  display: grid;
  gap: 14px;
}

.config-form,
.record-list article {
  padding: 20px;
  border-radius: 18px;
  box-shadow: none;
}

.config-form {
  background: #f8faff;
}

.config-form.compact {
  margin-top: 16px;
}

.config-form h3 {
  margin: 0;
}

.config-form label {
  display: grid;
  gap: 7px;
  color: #526077;
  font-size: 13px;
  font-weight: 750;
}

input,
select,
textarea {
  width: 100%;
  padding: 10px 11px;
  border: 1px solid #d8e0ec;
  border-radius: 10px;
  color: #172033;
  background: white;
}

textarea {
  resize: vertical;
}

.config-form button {
  padding: 11px 16px;
  border: 0;
  border-radius: 12px;
  color: white;
  background: #2764e7;
  cursor: pointer;
  font-weight: 800;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.two-columns {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.toggle-row {
  grid-template-columns: auto 1fr;
  justify-content: start;
}

.toggle-row input,
.checkbox-grid input {
  width: auto;
}

fieldset {
  margin: 0;
  padding: 14px;
  border: 1px solid #dce4f0;
  border-radius: 14px;
}

legend {
  padding: 0 6px;
  color: #526077;
  font-size: 13px;
  font-weight: 800;
}

.ratio-grid,
.weekday-grid {
  display: grid;
  gap: 8px;
}

.ratio-grid {
  grid-template-columns: repeat(2, 1fr);
}

.ratio-grid label {
  padding: 10px;
  border-radius: 10px;
  background: white;
}

.ratio-grid label span {
  display: flex;
  align-items: center;
  gap: 5px;
}

.weekday-grid {
  grid-template-columns: repeat(4, 1fr);
}

.checkbox-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
}

.checkbox-grid label {
  display: flex;
  grid-template-columns: auto 1fr;
  align-items: center;
}

.record-title {
  gap: 12px;
  align-items: flex-start;
}

.record-title small,
.muted {
  color: #7a879b;
}

.record-title h3 {
  margin: 4px 0 0;
}

.record-title button {
  padding: 6px 10px;
  border: 0;
  border-radius: 8px;
  color: #a12626;
  background: #fff1f1;
  cursor: pointer;
}

.record-list article > p {
  margin: 12px 0;
  color: #647087;
  line-height: 1.65;
}

.tag-row,
.week-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.tag-row span,
.week-summary span {
  padding: 5px 9px;
  color: #174cb7;
  background: #edf4ff;
  font-size: 12px;
}

.week-summary span {
  border-radius: 8px;
  color: #526077;
  background: #f0f3f8;
}

.exception-card {
  border-color: #f0dcae !important;
  background: #fffbeb !important;
}

.empty-state {
  margin: 0;
  padding: 20px;
  border: 1px dashed #ccd6e5;
  border-radius: 14px;
  color: #7a879b;
  text-align: center;
}

@media (max-width: 900px) {
  .split-layout {
    grid-template-columns: 1fr;
  }

  .section-nav {
    position: static;
    overflow-x: auto;
  }
}

@media (max-width: 600px) {
  .planning-hero,
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .two-columns,
  .ratio-grid,
  .weekday-grid {
    grid-template-columns: 1fr;
  }

  .config-section {
    padding: 20px;
  }
}
</style>
