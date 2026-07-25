<script setup>
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { apiUrl } from './api'
import { useI18n } from 'vue-i18n'

import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip
)

const { t, locale } = useI18n({
  useScope: 'global'
})

watch(
  locale,
  (newLocale) => {
    localStorage.setItem('retention-checker-locale', newLocale)
    document.documentElement.lang = newLocale
  },
  {
    immediate: true
  }
)


const activeTab = ref('analyze')
const analysisMode = ref('manual')
const dashboardCourseInput = ref('')
const dashboardPreview = ref(null)
const dashboardLoading = ref(false)
const dashboardError = ref('')
const dashboardWiki = ref('')
const dashboardReferenceDate = ref('')
const usernamesText = ref('')
const wiki = ref('eswiki')
const referenceDate = ref('')
const newbieThresholdDays = ref(60)
const reactivationThresholdDays = ref(90)
const activeEditThreshold = ref(5)
const veryActiveEditThreshold = ref(20)
const appliedSettings = ref({
  newbieThresholdDays: 60,
  reactivationThresholdDays: 90,
  activeEditThreshold: 5,
  veryActiveEditThreshold: 20
})
const settingsAreApplied = ref(true)
const settingsError = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)

watch(dashboardCourseInput, () => {
  dashboardPreview.value = null
  dashboardError.value = ''
  dashboardWiki.value = ''
  dashboardReferenceDate.value = ''
  error.value = ''
  result.value = null
})

watch(
  [
    newbieThresholdDays,
    reactivationThresholdDays,
    activeEditThreshold,
    veryActiveEditThreshold
  ],
  () => {
    settingsAreApplied.value = false
    settingsError.value = ''
  }
)

function safelyDecodeUrlComponent(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function normalizeDashboardCourseInput(value) {
  const trimmedValue = value.trim()

  if (!trimmedValue) {
    return ''
  }

  try {
    const url = new URL(trimmedValue)
    const coursePathMarker = '/courses/'
    const markerPosition = url.pathname.indexOf(coursePathMarker)

    if (markerPosition === -1) {
      return ''
    }

    const coursePath = url.pathname
      .slice(markerPosition + coursePathMarker.length)
      .replace(/^\/+|\/+$/g, '')

    return safelyDecodeUrlComponent(coursePath)
  } catch {
    const coursePath = trimmedValue.replace(/^\/+|\/+$/g, '')

    return safelyDecodeUrlComponent(coursePath)
  }
}

const dashboardCourseSlug = computed(() => {
  return normalizeDashboardCourseInput(dashboardCourseInput.value)
})

function selectAnalysisMode(mode) {
  analysisMode.value = mode
  error.value = ''
  result.value = null
}

async function loadDashboardPreview() {
  dashboardError.value = ''
  dashboardPreview.value = null

  if (!dashboardCourseSlug.value) {
    dashboardError.value = t('dashboard.invalidInput')
    return
  }

  dashboardLoading.value = true

  try {
    const response = await axios.post(
      apiUrl('/api/dashboard/preview'),
      {
        course_slug: dashboardCourseSlug.value
      }
    )

    dashboardPreview.value = response.data

    dashboardWiki.value =
      response.data.suggested_wiki || ''

    dashboardReferenceDate.value =
      response.data.suggested_reference_date || ''
  } catch (err) {
    console.error(err)

    dashboardError.value =
      err.response?.data?.detail
      || t('dashboard.loadFailed')
  } finally {
    dashboardLoading.value = false
  }
}

async function runDashboardAnalysis() {
  error.value = ''
  result.value = null
  if (!settingsAreApplied.value) {
    error.value = t('settings.applyBeforeAnalysis')
    return
}

  if (!dashboardPreview.value) {
    error.value = t('dashboard.previewRequired')
    return
  }

  const usernames =
    dashboardPreview.value.participant_usernames || []

  if (usernames.length === 0) {
    error.value = t('dashboard.noParticipants')
    return
  }

  if (!dashboardWiki.value.trim()) {
    error.value = t('dashboard.wikiRequired')
    return
  }

  if (!dashboardReferenceDate.value) {
    error.value = t('dashboard.referenceDateRequired')
    return
  }

  loading.value = true

  try {
    const response = await axios.post(
      apiUrl('/api/analyze/manual'),
      {
        usernames,
        wiki: dashboardWiki.value.trim(),
        reference_date: dashboardReferenceDate.value,
        retention_windows: [30, 90, 180, 360],
        newbie_threshold_days:
          appliedSettings.value.newbieThresholdDays,

        reactivation_threshold_days:
          appliedSettings.value.reactivationThresholdDays,

        active_edit_threshold:
          appliedSettings.value.activeEditThreshold,

        very_active_edit_threshold:
          appliedSettings.value.veryActiveEditThreshold
      }
    )

    result.value = response.data
  } catch (err) {
    console.error(err)

    error.value =
      err.response?.data?.detail
      || t('dashboard.analysisFailed')
  } finally {
    loading.value = false
  }
}

function applyAdvancedSettings() {
  settingsError.value = ''

  const newAccountDays = Number(newbieThresholdDays.value)
  const preEventDays = Number(reactivationThresholdDays.value)
  const activeThreshold = Number(activeEditThreshold.value)
  const veryActiveThreshold = Number(
    veryActiveEditThreshold.value
  )

  if (
    !Number.isFinite(newAccountDays)
    || newAccountDays < 0
    || !Number.isFinite(preEventDays)
    || preEventDays < 0
    || !Number.isFinite(activeThreshold)
    || activeThreshold < 1
    || !Number.isFinite(veryActiveThreshold)
    || veryActiveThreshold < 1
  ) {
    settingsError.value = t('settings.invalidValues')
    return
  }

  if (veryActiveThreshold < activeThreshold) {
    settingsError.value = t(
      'settings.veryActiveBelowActive'
    )
    return
  }

  appliedSettings.value = {
    newbieThresholdDays: newAccountDays,
    reactivationThresholdDays: preEventDays,
    activeEditThreshold: activeThreshold,
    veryActiveEditThreshold: veryActiveThreshold
  }

  settingsAreApplied.value = true

  // Existing results used the previous settings.
  result.value = null
  error.value = ''
}

async function runAnalysis() {
  error.value = ''
  result.value = null
  if (!settingsAreApplied.value) {
  error.value = t('settings.applyBeforeAnalysis')
  loading.value = false
  return
}

  const usernames = usernamesText.value
    .split('\n')
    .map((username) => username.trim())
    .filter(Boolean)

  if (usernames.length === 0) {
    error.value = t('errors.usernamesRequired')
    loading.value = false
    return
  }

  if (!wiki.value.trim()) {
    error.value = t('errors.wikiRequired')
    loading.value = false
    return
  }

  if (!referenceDate.value) {
    error.value = t('errors.referenceDateRequired')
    loading.value = false
    return
  }

  loading.value = true

  try {
    const response = await axios.post(
      apiUrl('/api/analyze/manual'), {
      usernames,
      wiki: wiki.value.trim(),
      reference_date: referenceDate.value,
      retention_windows: [30, 90, 180, 360],
      newbie_threshold_days:
        appliedSettings.value.newbieThresholdDays,
      reactivation_threshold_days:
        appliedSettings.value.reactivationThresholdDays,
      active_edit_threshold:
        appliedSettings.value.activeEditThreshold,
      very_active_edit_threshold:
        appliedSettings.value.veryActiveEditThreshold
    })

    result.value = response.data
  } catch (err) {
    console.error(err)
    error.value = t('errors.analysisFailed')
  } finally {
    loading.value = false
  }
}

function escapeCsvValue(value) {
  if (value === null || value === undefined) {
    return ''
  }

  const stringValue = String(value)

  if (
    stringValue.includes(',') ||
    stringValue.includes('"') ||
    stringValue.includes('\n')
  ) {
    return `"${stringValue.replaceAll('"', '""')}"`
  }

  return stringValue
}

function downloadCsv() {
  if (!result.value || !result.value.users) {
    return
  }

const columns = [
  'username',
  'status',
  'registration_date',
  'experience_type',
  'pre_event_edits_reactivation_window',
  'available_30d',
  'edits_30d',
  'retained_30d',
  'available_90d',
  'edits_90d',
  'retained_90d',
  'available_180d',
  'edits_180d',
  'retained_180d',
  'available_360d',
  'edits_360d',
  'retained_360d',
  'active_months',
  'first_post_activity_edit',
  'last_post_activity_edit',
  'retention_category'
]

  const header = columns.join(',')

  const rows = result.value.users.map((user) => {
    return columns
      .map((column) => escapeCsvValue(user[column]))
      .join(',')
  })

  const csvContent = [header, ...rows].join('\n')

  const blob = new Blob([csvContent], {
    type: 'text/csv;charset=utf-8;'
  })

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  const wikiName = result.value.metadata?.wiki || 'wiki'
  const referenceDate = result.value.metadata?.reference_date || 'reference-date'

  link.href = url
  link.setAttribute(
    'download',
    `retention-checker_${wikiName}_${referenceDate}.csv`
  )

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}

function formatAccountType(user) {
  if (user.status === 'user_not_found') {
    return t('accountTypes.userNotFound')
  }

  if (user.status === 'bot_excluded') {
    return t('accountTypes.botExcluded')
  }

  const translationKeys = {
    newbie: 'accountTypes.newbie',
    existing_user: 'accountTypes.existingUser',
    unknown: 'accountTypes.unknown',
    created_after_reference_date: 'accountTypes.createdAfterReferenceDate',
    reactivated_editor: 'accountTypes.existingUser'
  }

  const translationKey = translationKeys[user.experience_type]

  return translationKey
    ? t(translationKey)
    : user.experience_type || ''
}

function formatRetentionCategory(value) {
  const translationKeys = {
    not_retained: 'retentionCategories.notRetained',
    one_time_returner: 'retentionCategories.oneTimeReturner',
    active_retained_user: 'retentionCategories.activeRetainedUser',
    sustained_retained_user: 'retentionCategories.sustainedRetainedUser',
    very_active_retained_user: 'retentionCategories.veryActiveRetainedUser'
  }

  const translationKey = translationKeys[value]

  return translationKey
    ? t(translationKey)
    : value || ''
}

function formatWindowValue(value) {
  if (value === null || value === undefined) {
    return '—'
  }

  return value
}

function formatRetentionPercentage(retentionSummary) {
  if (!retentionSummary || retentionSummary.percentage === null || retentionSummary.percentage === undefined) {
    return '—'
  }

  return `${retentionSummary.percentage}%`
}

const retentionChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      callbacks: {
        label(context) {
          return `${context.parsed.y}%`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      ticks: {
        color: '#cbd5e1',
        callback(value) {
          return `${value}%`
        }
      },
      grid: {
        color: '#2a3441'
      }
    },
    x: {
      ticks: {
        color: '#cbd5e1'
      },
      grid: {
        display: false
      }
    }
  }
}

const retentionChartData = computed(() => {
  if (!result.value) {
    return {
      labels: [],
      datasets: []
    }
  }


  const windows = [
    {
      label: t('chart.windowDays', { days: 30 }),
      summary: result.value.summary.retained_30d
    },
    {
      label: t('chart.windowDays', { days: 90 }),
      summary: result.value.summary.retained_90d
    },
    {
      label: t('chart.windowDays', { days: 180 }),
      summary: result.value.summary.retained_180d
    },
    {
      label: t('chart.windowDays', { days: 360 }),
      summary: result.value.summary.retained_360d
    }
  ]

  const availableWindows = windows.filter(
    (window) => window.summary?.available
  )

  return {
    labels: availableWindows.map((window) => window.label),
    datasets: [
      {
        label: t('chart.datasetLabel'),
        data: availableWindows.map(
          (window) => window.summary.percentage
        ),
        backgroundColor: '#6d8cff',
        borderColor: '#91a6ff',
        borderWidth: 1,
        borderRadius: 6
      }
    ]
  }
})
</script>

<template>
  <main class="page">
    <section class="hero">
  <p class="eyebrow">
    {{ t('app.eyebrow') }}
  </p>

  <h1>
    {{ t('app.name') }}
  </h1>

  <p class="description">
    {{ t('app.description') }}
  </p>
</section>

    <div class="navigation-row">
  <nav
    class="tabs"
    :aria-label="t('tabs.ariaLabel')"
  >
    <button
      class="tab-button"
      :class="{ active: activeTab === 'analyze' }"
      @click="activeTab = 'analyze'"
    >
      {{ t('tabs.analyze') }}
    </button>

    <button
      class="tab-button"
      :class="{ active: activeTab === 'about' }"
      @click="activeTab = 'about'"
    >
      {{ t('tabs.about') }}
    </button>
  </nav>

  <label class="language-control">
    <span>{{ t('language.label') }}</span>

    <select
      v-model="locale"
      class="language-select"
    >
      <option value="en">
        {{ t('language.english') }}
      </option>

      <option value="es">
        {{ t('language.spanish') }}
      </option>
    </select>
  </label>
</div>

    <div v-if="activeTab === 'analyze'">

      <nav
        class="analysis-mode-tabs"
        :aria-label="t('analysisModes.ariaLabel')"
      >
        <button
          class="analysis-mode-button"
          :class="{ active: analysisMode === 'manual' }"
          @click="selectAnalysisMode('manual')"
        >
          {{ t('analysisModes.manual') }}
        </button>

        <button
          class="analysis-mode-button"
          :class="{ active: analysisMode === 'dashboard' }"
          @click="selectAnalysisMode('dashboard')"
        >
          {{ t('analysisModes.dashboard') }}
        </button>
      </nav>
      <details class="advanced-settings shared-settings">
        <summary>
          {{ t('analysis.advancedSettings') }}
        </summary>

        <div class="grid settings-grid">
          <label>
            {{ t('analysis.newbieThresholdLabel') }}

            <input
              v-model="newbieThresholdDays"
              type="number"
              min="0"
            />

            <small>
              {{ t('analysis.newbieThresholdHelp') }}
            </small>
          </label>

          <label>
            {{ t('analysis.preEventWindowLabel') }}

            <input
              v-model="reactivationThresholdDays"
              type="number"
              min="0"
            />

            <small>
              {{ t('analysis.preEventWindowHelp') }}
            </small>
          </label>

          <label>
            {{ t('analysis.activeThresholdLabel') }}

            <input
              v-model="activeEditThreshold"
              type="number"
              min="1"
            />

            <small>
              {{ t('analysis.activeThresholdHelp') }}
            </small>
          </label>

          <label>
            {{ t('analysis.veryActiveThresholdLabel') }}

            <input
              v-model="veryActiveEditThreshold"
              type="number"
              min="1"
            />

            <small>
              {{ t('analysis.veryActiveThresholdHelp') }}
            </small>
          </label>
        </div>
        <div class="settings-actions">
          <button
            type="button"
            class="secondary-button"
            @click="applyAdvancedSettings"
          >
            {{ t('settings.apply') }}
          </button>

          <span
            v-if="settingsAreApplied"
            class="settings-status settings-status-applied"
          >
            {{ t('settings.applied') }}
          </span>

          <span
            v-else
            class="settings-status settings-status-pending"
          >
            {{ t('settings.notApplied') }}
          </span>
        </div>

        <p
          v-if="settingsError"
          class="error"
        >
          {{ settingsError }}
        </p>
      </details>
    
    <section
      v-if="analysisMode === 'manual'"
      class="card"
    >
      <h2>{{ t('analysis.title') }}</h2>

      <label>
        {{ t('analysis.usernamesLabel') }}

        <textarea
          v-model="usernamesText"
          rows="8"
          :placeholder="t('analysis.usernamesPlaceholder')"
        ></textarea>

        <small class="processing-note">
            {{ t('analysis.processingNote') }}
          </small>
      </label>

      <div class="grid">
        <label>
          {{ t('analysis.wikiLabel') }}

          <input
            v-model="wiki"
            :placeholder="t('analysis.wikiPlaceholder')"
          />

          <small>
            {{ t('analysis.wikiHelp') }}
          </small>
        </label>

        <label>
          {{ t('analysis.referenceDateLabel') }}

          <input
            v-model="referenceDate"
            type="date"
          />
        </label>
      </div>

      <button
        @click="runAnalysis"
        :disabled="loading"
      >
        {{
          loading
            ? t('analysis.running')
            : t('analysis.run')
        }}
      </button>

      <p
        v-if="error"
        class="error"
      >
        {{ error }}
      </p>
    </section>

    <section
      v-if="analysisMode === 'dashboard'"
      class="card"
    >
      <h2>{{ t('dashboard.title') }}</h2>

      <label>
        {{ t('dashboard.courseLabel') }}

        <input
          v-model="dashboardCourseInput"
          type="text"
          :placeholder="t('dashboard.coursePlaceholder')"
        />

        <small>
          {{ t('dashboard.courseHelp') }}
        </small>
      </label>

      <p
        v-if="dashboardCourseSlug"
        class="detected-course"
      >
        {{
          t('dashboard.detectedSlug', {
            slug: dashboardCourseSlug
          })
        }}
      </p>

      <button
        @click="loadDashboardPreview"
        :disabled="
          dashboardLoading
          || !dashboardCourseSlug
        "
      >
        {{
          dashboardLoading
            ? t('dashboard.loadingCourse')
            : t('dashboard.loadCourse')
        }}
      </button>

      <p
        v-if="dashboardError"
        class="error"
      >
        {{ dashboardError }}
      </p>

      <div
        v-if="dashboardPreview"
        class="dashboard-preview"
      >
        <div class="section-header">
          <h3>{{ t('dashboard.previewTitle') }}</h3>

          <a
            :href="dashboardPreview.course_url"
            target="_blank"
            rel="noopener noreferrer"
            class="course-link"
          >
            {{ t('dashboard.openCourse') }}
          </a>
        </div>

        <div class="dashboard-preview-grid">
          <div class="preview-item">
            <span>{{ t('dashboard.courseTitle') }}</span>
            <strong>
              {{ dashboardPreview.title || '—' }}
            </strong>
          </div>

          <div class="preview-item">
            <span>{{ t('dashboard.organization') }}</span>
            <strong>
              {{ dashboardPreview.organization || '—' }}
            </strong>
          </div>

          <div class="preview-item">
            <span>{{ t('dashboard.participants') }}</span>
            <strong>
              {{ dashboardPreview.participant_count }}
            </strong>
          </div>

          <div class="preview-item">
            <span>{{ t('dashboard.staff') }}</span>
            <strong>
              {{ dashboardPreview.staff_count }}
            </strong>
          </div>

          <div class="preview-item">
            <span>{{ t('dashboard.roleConflicts') }}</span>
            <strong>
              {{ dashboardPreview.role_conflict_count }}
            </strong>
          </div>
        </div>

        <p
          v-if="dashboardPreview.role_conflict_count > 0"
          class="dashboard-note"
        >
          {{ t('dashboard.roleConflictHelp') }}
        </p>

        <p
            v-if="dashboardPreview.participant_count > 50"
            class="dashboard-note"
          >
            {{
              t('dashboard.largeCourseNote', {
                count: dashboardPreview.participant_count
              })
            }}
          </p>

        <div class="grid dashboard-settings">
          <label>
            {{ t('dashboard.wikiLabel') }}

            <input
              v-model="dashboardWiki"
              type="text"
              placeholder="enwiki"
            />
          </label>

          <label>
            {{ t('dashboard.referenceDateLabel') }}

            <input
              v-model="dashboardReferenceDate"
              type="date"
            />
          </label>
        </div>
      </div>
      <button
        @click="runDashboardAnalysis"
        :disabled="loading"
      >
        {{
          loading
            ? t('dashboard.runningAnalysis')
            : t('dashboard.runAnalysis')
        }}
      </button>

      <p
        v-if="error"
        class="error"
      >
        {{ error }}
      </p>
    </section>

    <section v-if="result" class="card">
      <h2>{{ t('summary.title') }}</h2>

      <div class="summary-grid">
        <div class="summary-card">
          <span>{{ t('summary.totalSubmitted') }}</span>
          <strong>{{ result.summary.total_users_submitted }}</strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.duplicatesRemoved') }}</span>
          <strong>
            {{ result.summary.duplicate_or_removed_usernames }}
          </strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.validUsers') }}</span>
          <strong>{{ result.summary.valid_users }}</strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.invalidUsers') }}</span>
          <strong>{{ result.summary.invalid_users }}</strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.newAccounts') }}</span>
          <strong>{{ result.summary.newbies }}</strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.existingOrUnknownAccounts') }}</span>
          <strong>
            {{
              result.summary.existing_users
              + result.summary.unknown_experience
            }}
          </strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.retention30') }}</span>
          <strong>
            {{ formatRetentionPercentage(result.summary.retained_30d) }}
          </strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.retention90') }}</span>
          <strong>
            {{ formatRetentionPercentage(result.summary.retained_90d) }}
          </strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.retention180') }}</span>
          <strong>
            {{ formatRetentionPercentage(result.summary.retained_180d) }}
          </strong>
        </div>

        <div class="summary-card">
          <span>{{ t('summary.retention360') }}</span>
          <strong>
            {{ formatRetentionPercentage(result.summary.retained_360d) }}
          </strong>
        </div>
      </div>
    </section>

      <section v-if="result" class="card">
        <div class="section-header">
          <h2>{{ t('results.title') }}</h2>

          <button
            class="secondary-button"
            @click="downloadCsv"
          >
            {{ t('results.downloadCsv') }}
          </button>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>{{ t('results.columns.username') }}</th>
                <th>{{ t('results.columns.accountType') }}</th>
                <th>{{ t('results.columns.preEventEdits') }}</th>
                <th>{{ t('results.columns.day30') }}</th>
                <th>{{ t('results.columns.day90') }}</th>
                <th>{{ t('results.columns.day180') }}</th>
                <th>{{ t('results.columns.day360') }}</th>
                <th>{{ t('results.columns.activeMonths') }}</th>
                <th>{{ t('results.columns.firstPostActivityEdit') }}</th>
                <th>{{ t('results.columns.lastPostActivityEdit') }}</th>
                <th>{{ t('results.columns.retentionCategory') }}</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="user in result.users"
                :key="user.username"
              >
                <td>{{ user.username }}</td>
                <td>{{ formatAccountType(user) }}</td>
                <td>{{ user.pre_event_edits_reactivation_window }}</td>
                <td>{{ formatWindowValue(user.edits_30d) }}</td>
                <td>{{ formatWindowValue(user.edits_90d) }}</td>
                <td>{{ formatWindowValue(user.edits_180d) }}</td>
                <td>{{ formatWindowValue(user.edits_360d) }}</td>
                <td>{{ user.active_months }}</td>
                <td>{{ user.first_post_activity_edit }}</td>
                <td>{{ user.last_post_activity_edit }}</td>
                <td>
                  {{ formatRetentionCategory(user.retention_category) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="result" class="card">
        <h2>{{ t('chart.title') }}</h2>

        <p class="chart-description">
          {{ t('chart.description') }}
        </p>

        <div
          v-if="retentionChartData.labels.length > 0"
          class="chart-container"
        >
          <Bar
            :data="retentionChartData"
            :options="retentionChartOptions"
            :aria-label="t('chart.ariaLabel')"
          />
        </div>

        <p v-else class="empty-chart-message">
          {{ t('chart.empty') }}
        </p>
      </section>
    </div>

    <section
      v-if="activeTab === 'about'"
      class="card about-card"
    >
      <h2>{{ t('about.title') }}</h2>

      <p>{{ t('about.intro') }}</p>

      <h3>{{ t('about.validUsersTitle') }}</h3>
      <p>{{ t('about.validUsersDescription') }}</p>

      <h3>{{ t('about.referenceDateTitle') }}</h3>
      <p>{{ t('about.referenceDateDescription') }}</p>

      <h3>{{ t('about.countedEditsTitle') }}</h3>
      <p>{{ t('about.countedEditsDescription') }}</p>

      <h3>{{ t('about.retentionWindowsTitle') }}</h3>
      <p>{{ t('about.retentionWindowsDescription') }}</p>
      <p>{{ t('about.unavailableWindowsDescription') }}</p>

      <h3>{{ t('about.preEventEditsTitle') }}</h3>
      <p>
        {{
          t('about.preEventEditsDescription', {
            days: appliedSettings.reactivationThresholdDays
          })
        }}
      </p>

      <h3>{{ t('about.accountTypesTitle') }}</h3>

      <table class="about-table">
        <thead>
          <tr>
            <th>{{ t('about.table.accountType') }}</th>
            <th>{{ t('about.table.meaning') }}</th>
          </tr>
        </thead>

        <tbody>
          <tr>
            <td>{{ t('accountTypes.newbie') }}</td>
            <td>
              {{
                t('about.accountTypeDescriptions.newbie', {
                  days: appliedSettings.newbieThresholdDays
                })
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('accountTypes.existingUser') }}</td>
            <td>
              {{
                t('about.accountTypeDescriptions.existingUser', {
                  days: appliedSettings.newbieThresholdDays
                })
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('accountTypes.unknown') }}</td>
            <td>
              {{ t('about.accountTypeDescriptions.unknown') }}
            </td>
          </tr>

          <tr>
            <td>{{ t('accountTypes.createdAfterReferenceDate') }}</td>
            <td>
              {{
                t(
                  'about.accountTypeDescriptions.createdAfterReferenceDate'
                )
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('accountTypes.userNotFound') }}</td>
            <td>
              {{ t('about.accountTypeDescriptions.userNotFound') }}
            </td>
          </tr>

          <tr>
            <td>{{ t('accountTypes.botExcluded') }}</td>
            <td>
              {{ t('about.accountTypeDescriptions.botExcluded') }}
            </td>
          </tr>
        </tbody>
      </table>

      <h3>{{ t('about.retentionCategoriesTitle') }}</h3>

      <table class="about-table">
        <thead>
          <tr>
            <th>{{ t('about.table.category') }}</th>
            <th>{{ t('about.table.meaning') }}</th>
          </tr>
        </thead>

        <tbody>
          <tr>
            <td>{{ t('retentionCategories.notRetained') }}</td>
            <td>
              {{
                t(
                  'about.retentionCategoryDescriptions.notRetained'
                )
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('retentionCategories.oneTimeReturner') }}</td>
            <td>
              {{
                t(
                  'about.retentionCategoryDescriptions.oneTimeReturner',
                  {
                    activeThreshold: appliedSettings.activeEditThreshold
                  }
                )
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('retentionCategories.activeRetainedUser') }}</td>
            <td>
              {{
                t(
                  'about.retentionCategoryDescriptions.activeRetainedUser',
                  {
                    activeThreshold: appliedSettings.activeEditThreshold,
                    veryActiveThreshold: appliedSettings.veryActiveEditThreshold
                  }
                )
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('retentionCategories.sustainedRetainedUser') }}</td>
            <td>
              {{
                t(
                  'about.retentionCategoryDescriptions.sustainedRetainedUser',
                  {
                    activeThreshold: appliedSettings.activeEditThreshold
                  }
                )
              }}
            </td>
          </tr>

          <tr>
            <td>{{ t('retentionCategories.veryActiveRetainedUser') }}</td>
            <td>
              {{
                t(
                  'about.retentionCategoryDescriptions.veryActiveRetainedUser',
                  {
                    activeThreshold: appliedSettings.activeEditThreshold,
                    veryActiveThreshold: appliedSettings.veryActiveEditThreshold
                  }
                )
              }}
            </td>
          </tr>
        </tbody>
      </table>

      <h3>{{ t('about.limitationsTitle') }}</h3>
      <p>{{ t('about.limitationsDescription') }}</p>
    </section>
    <footer class="site-footer">
      <p>
        {{ t('footer.madeWith') }}
        <span
          class="footer-heart"
          aria-hidden="true"
        >
          ♥
        </span>
        {{ t('footer.by') }}

        <a
          href="https://wikimedia.cl/"
          target="_blank"
          rel="noopener noreferrer"
        >
          Wikimedia Chile
        </a>
      </p>

      <a
        href="https://github.com/WikimediaChile/retention-checker"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ t('footer.sourceCode') }}
      </a>
    </footer>
  </main>
</template>

<style>
:root {
  color-scheme: dark;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #101418;
  color: #f5f7fa;
}

body {
  margin: 0;
  background: #101418;
}

.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 48px 24px;
}

.hero {
  margin-bottom: 32px;
}

.eyebrow {
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.8rem;
  margin-bottom: 8px;
}

h1 {
  font-size: 3rem;
  line-height: 1;
  margin: 0 0 16px;
}

h2 {
  margin-top: 0;
}

.description {
  max-width: 720px;
  color: #cbd5e1;
  font-size: 1.1rem;
}

.card {
  width: 100%;
  background: #171d24;
  border: 1px solid #2a3441;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  overflow: hidden;
}

label {
  display: block;
  font-weight: 600;
  margin-bottom: 16px;
}

textarea,
input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #3a4656;
  background: #0f141a;
  color: #f5f7fa;
  font: inherit;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

button {
  border: 0;
  border-radius: 10px;
  padding: 12px 18px;
  background: #6d8cff;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.section-header h2 {
  margin: 0;
}

.secondary-button {
  background: #263241;
  color: #f5f7fa;
  border: 1px solid #3a4656;
}

.secondary-button:hover {
  background: #334155;
}

.error {
  color: #fca5a5;
  margin-top: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-card {
  background: #0f141a;
  border: 1px solid #2a3441;
  border-radius: 12px;
  padding: 16px;
}

.summary-card span {
  display: block;
  color: #9ca3af;
  margin-bottom: 8px;
}

.summary-card strong {
  font-size: 1.8rem;
}

.advanced-settings {
  margin: 8px 0 20px;
  border: 1px solid #2a3441;
  border-radius: 12px;
  padding: 14px 16px;
  background: #0f141a;
}

.advanced-settings summary {
  cursor: pointer;
  font-weight: 700;
  color: #f5f7fa;
}

.settings-grid {
  margin-top: 18px;
}

small {
  display: block;
  margin-top: 6px;
  color: #9ca3af;
  font-weight: 400;
  line-height: 1.4;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}

th,
td {
  text-align: left;
  padding: 12px;
  border-bottom: 1px solid #2a3441;
  white-space: nowrap;
}

th {
  color: #cbd5e1;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 0;
}

.tab-button {
  background: #0f141a;
  color: #cbd5e1;
  border: 1px solid #2a3441;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
}

.tab-button.active {
  background: #6d8cff;
  color: white;
  border-color: #6d8cff;
}

.about-card {
  max-width: 900px;
}

.about-card p {
  color: #cbd5e1;
  line-height: 1.6;
}

.about-card h3 {
  margin-top: 28px;
  margin-bottom: 8px;
}

.about-table {
  margin-top: 12px;
}

.about-table td:first-child {
  font-weight: 700;
  color: #f5f7fa;
}

.about-table th,
.about-table td {
  white-space: normal;
  vertical-align: top;
  line-height: 1.5;
}

.about-table td:first-child {
  min-width: 180px;
}

.chart-description {
  margin-top: -4px;
  margin-bottom: 24px;
  color: #cbd5e1;
  line-height: 1.5;
}

.chart-container {
  position: relative;
  width: 100%;
  height: 340px;
}

.empty-chart-message {
  color: #9ca3af;
}

.navigation-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.language-control {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0;
  color: #cbd5e1;
}

.language-select {
  padding: 9px 12px;
  border: 1px solid #3a4656;
  border-radius: 10px;
  background: #0f141a;
  color: #f5f7fa;
  font: inherit;
  cursor: pointer;
}

.analysis-mode-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.analysis-mode-button {
  background: transparent;
  color: #cbd5e1;
  border: 1px solid #3a4656;
}

.analysis-mode-button.active {
  background: #263241;
  color: #ffffff;
  border-color: #6d8cff;
}

.detected-course {
  padding: 12px 14px;
  border: 1px solid #365846;
  border-radius: 10px;
  background: #13231b;
  color: #bbf7d0;
  overflow-wrap: anywhere;
}

.dashboard-next-step {
  color: #9ca3af;
  font-size: 0.92rem;
}

.dashboard-preview {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #2a3441;
}

.dashboard-preview h3 {
  margin: 0;
}

.dashboard-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.preview-item {
  padding: 14px;
  border: 1px solid #2a3441;
  border-radius: 10px;
  background: #0f141a;
}

.preview-item span {
  display: block;
  margin-bottom: 6px;
  color: #9ca3af;
  font-size: 0.88rem;
}

.preview-item strong {
  overflow-wrap: anywhere;
}

.dashboard-settings {
  margin-top: 20px;
}

.dashboard-note {
  color: #fcd34d;
  line-height: 1.5;
}

.course-link {
  color: #91a6ff;
  font-weight: 600;
  text-decoration: none;
}

.course-link:hover {
  text-decoration: underline;
}

.shared-settings {
  margin-top: 0;
  margin-bottom: 16px;
}

.settings-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 4px;
}

.settings-status {
  font-size: 0.92rem;
  line-height: 1.4;
}

.settings-status-applied {
  color: #bbf7d0;
}

.settings-status-pending {
  color: #fcd34d;
}

.site-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 4px 0;
  margin-top: 32px;
  border-top: 1px solid #2a3441;
  color: #9ca3af;
  font-size: 0.92rem;
}

.site-footer p {
  margin: 0;
}

.site-footer a {
  color: #91a6ff;
  font-weight: 600;
  text-decoration: none;
}

.site-footer a:hover {
  text-decoration: underline;
}

.footer-heart {
  color: #f87171;
  margin: 0 3px;
}


@media (max-width: 800px) {
  .grid,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 2.2rem;
  }

  .navigation-row {
  align-items: flex-start;
  flex-direction: column;
  gap: 16px;
}

.language-control {
  width: 100%;
  justify-content: space-between;
}
.dashboard-preview-grid {
  grid-template-columns: 1fr;
}

.site-footer {
  align-items: flex-start;
  flex-direction: column;
}

}
</style>