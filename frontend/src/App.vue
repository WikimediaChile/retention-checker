<script setup>
import { ref } from 'vue'
import axios from 'axios'

const usernamesText = ref('')
const wiki = ref('eswiki')
const referenceDate = ref('')
const newbieThresholdDays = ref(60)
const reactivationThresholdDays = ref(90)
const activeEditThreshold = ref(5)
const veryActiveEditThreshold = ref(20)
const loading = ref(false)
const error = ref('')
const result = ref(null)

async function runAnalysis() {
  error.value = ''
  result.value = null
  loading.value = true

  const usernames = usernamesText.value
    .split('\n')
    .map((username) => username.trim())
    .filter(Boolean)

  if (usernames.length === 0) {
    error.value = 'Please enter at least one username.'
    loading.value = false
    return
  }

  if (!wiki.value.trim()) {
    error.value = 'Please enter a wiki, for example eswiki.'
    loading.value = false
    return
  }

  if (!referenceDate.value) {
    error.value = 'Please choose a reference date.'
    loading.value = false
    return
  }

  try {
    const response = await axios.post('http://127.0.0.1:8000/api/analyze/manual', {
      usernames,
      wiki: wiki.value.trim(),
      reference_date: referenceDate.value,
      retention_windows: [30, 90, 180, 360],
      newbie_threshold_days: Number(newbieThresholdDays.value),
      reactivation_threshold_days: Number(reactivationThresholdDays.value),
      active_edit_threshold: Number(activeEditThreshold.value),
      very_active_edit_threshold: Number(veryActiveEditThreshold.value)
    })

    result.value = response.data
  } catch (err) {
    console.error(err)
    error.value = 'Something went wrong while running the analysis. Check that the backend is running.'
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
  'pre_event_edits_90d',
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
    return 'User not found'
  }

  if (user.status === 'bot_excluded') {
    return 'Bot excluded'
  }

  const labels = {
    newbie: 'New account',
    existing_user: 'Existing account',
    unknown: 'Unknown account age',
    created_after_reference_date: 'Created after reference date',
    reactivated_editor: 'Existing account'
  }

  return labels[user.experience_type] || user.experience_type || ''
}

function formatRetentionCategory(value) {
  const labels = {
    not_retained: 'Not retained',
    one_time_returner: 'One-time returner',
    active_retained_user: 'Active retained user',
    sustained_retained_user: 'Sustained retained user',
    very_active_retained_user: 'Very active retained user'
  }

  return labels[value] || value || ''
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
</script>

<template>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Wikimedia post-activity analysis</p>
      <h1>Retention Checker</h1>
      <p class="description">
        Analyze whether participants continued editing after an activity.
        This first version supports manual username entry for one wiki.
      </p>
    </section>

    <section class="card">
      <h2>Manual analysis</h2>

      <label>
        Usernames
        <textarea
          v-model="usernamesText"
          rows="8"
          placeholder="One username per line"
        ></textarea>
      </label>

      <div class="grid">
        <label>
          Wiki
          <input v-model="wiki" placeholder="eswiki" />
        </label>

        <label>
          Reference date
          <input v-model="referenceDate" type="date" />
        </label>
      </div>

      <details class="advanced-settings">
        <summary>Advanced settings</summary>

        <div class="grid settings-grid">
          <label>
            New account threshold, in days
            <input
              v-model="newbieThresholdDays"
              type="number"
              min="0"
            />
            <small>
              Users registered within this many days before the reference date are counted as new accounts.
            </small>
          </label>

          <label>
            Pre-event activity window, in days
            <input
              v-model="reactivationThresholdDays"
              type="number"
              min="0"
            />
            <small>
              Used for the pre-event edits column. Default: 90 days before the reference date.
            </small>
          </label>

          <label>
            Active retained threshold, edits
            <input
              v-model="activeEditThreshold"
              type="number"
              min="1"
            />
            <small>
              Minimum post-activity edits needed to count as active retained.
            </small>
          </label>

          <label>
            Very active threshold, edits
            <input
              v-model="veryActiveEditThreshold"
              type="number"
              min="1"
            />
            <small>
              Minimum post-activity edits needed to count as very active retained.
            </small>
          </label>
        </div>
      </details>

      <button @click="runAnalysis" :disabled="loading">
        {{ loading ? 'Running analysis...' : 'Run analysis' }}
      </button>

      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section v-if="result" class="card">
      <h2>Summary</h2>

      <div class="summary-grid">
        <div class="summary-card">
          <span>Total submitted</span>
          <strong>{{ result.summary.total_users_submitted }}</strong>
        </div>

        <div class="summary-card">
          <span>Duplicates removed</span>
          <strong>{{ result.summary.duplicate_or_removed_usernames }}</strong>
        </div>

        <div class="summary-card">
          <span>Valid users</span>
          <strong>{{ result.summary.valid_users }}</strong>
        </div>

        <div class="summary-card">
          <span>Invalid users</span>
          <strong>{{ result.summary.invalid_users }}</strong>
        </div>

        <div class="summary-card">
          <span>New accounts</span>
          <strong>{{ result.summary.newbies }}</strong>
        </div>

        <div class="summary-card">
          <span>Existing accounts</span>
          <strong>{{ result.summary.existing_users + result.summary.unknown_experience }}</strong>
        </div>

        <div class="summary-card">
          <span>30-day retention</span>
          <strong>{{ formatRetentionPercentage(result.summary.retained_30d) }}</strong>
        </div>

        <div class="summary-card">
          <span>90-day retention</span>
          <strong>{{ formatRetentionPercentage(result.summary.retained_90d) }}</strong>
        </div>

        <div class="summary-card">
          <span>180-day retention</span>
          <strong>{{ formatRetentionPercentage(result.summary.retained_180d) }}</strong>
        </div>

        <div class="summary-card">
          <span>360-day retention</span>
          <strong>{{ formatRetentionPercentage(result.summary.retained_360d) }}</strong>
        </div>
      </div>
    </section>

      <section v-if="result" class="card">
        <div class="section-header">
          <h2>User results</h2>

          <button class="secondary-button" @click="downloadCsv">
            Download CSV
          </button>
        </div>

        <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Account type</th>
              <th>Pre-event edits</th>
              <th>30d</th>
              <th>90d</th>
              <th>180d</th>
              <th>360d</th>
              <th>Active months</th>
              <th>First post-activity edit</th>
              <th>Last post-activity edit</th>
              <th>Retention category</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="user in result.users" :key="user.username">
            <td>{{ user.username }}</td>
            <td>{{ formatAccountType(user) }}</td>
            <td>{{ user.pre_event_edits_90d }}</td>
            <td>{{ formatWindowValue(user.edits_30d) }}</td>
            <td>{{ formatWindowValue(user.edits_90d) }}</td>
            <td>{{ formatWindowValue(user.edits_180d) }}</td>
            <td>{{ formatWindowValue(user.edits_360d) }}</td>
            <td>{{ user.active_months }}</td>
            <td>{{ user.first_post_activity_edit }}</td>
            <td>{{ user.last_post_activity_edit }}</td>
            <td>{{ formatRetentionCategory(user.retention_category) }}</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>
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
  background: #171d24;
  border: 1px solid #2a3441;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
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

@media (max-width: 800px) {
  .grid,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 2.2rem;
  }
}
</style>