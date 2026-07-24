# Retention Checker

[![Status](<https://img.shields.io/badge/status-in%20development-yellow>)]()
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A web application for analyzing whether Wikimedia participants continue editing after an activity.

Retention Checker supports manual username lists and imports participants from the [Programs &amp; Events Dashboard](https://outreachdashboard.wmflabs.org/). It calculates post-activity editing metrics, retention windows, account types, and retention categories using Wikimedia API data.

## About the Project

**Retention Checker** is designed to help Wikimedia organizers better understand participant activity after workshops, edit-a-thons, courses, campaigns, and other events.

The tool analyzes editing activity after a selected reference date and provides cumulative retention results for 30, 90, 180, and 360 days.

The project is currently under active development.

## Main Features

- **Manual analysis:** Enter one Wikimedia username per line and select a wiki and reference date.
- **Programs & Events Dashboard import:** Load participants directly from a Dashboard course URL or course slug.
- **Editable analysis settings:** Configure new-account, pre-event activity, active-retention, and very-active thresholds.
- **Account classification:** Identify new, existing, unknown-age, and post-reference-date accounts.
- **Retention categories:** Classify users as not retained, one-time returners, active retained, sustained retained, or very active retained.
- **Cumulative retention windows:** Calculate retention at 30, 90, 180, and 360 days when enough time has passed.
- **Visual summary:** Display retention percentages in summary cards and charts.
- **CSV export:** Download detailed user-level results.
- **Multilingual interface:** Available in English and Spanish.
- **Responsive dark interface:** Designed for desktop and smaller

## Built With

### Backend

- [Python](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [HTTPX](https://www.python-httpx.org/)
- Wikimedia Action API
- Programs & Events Dashboard API

### Frontend

- [Vue.js 3](https://vuejs.org/)
- [Vite](https://vite.dev/)
- [Vue I18n](https://vue-i18n.intlify.dev/)
- [Chart.js](https://www.chartjs.org/)
- [vue-chartjs](https://vue-chartjs.org/)
- HTML5 and CSS3


## Current Analysis Scope

The current version:

* analyzes one wiki at a time;
* uses a selected reference date as the beginning of the post-activity period;
* calculates cumulative retention windows;
* excludes missing users and detected bot accounts from retention percentages;
* imports participant accounts from Programs & Events Dashboard courses;
* excludes staff accounts and accounts with conflicting participant/staff roles from the default Dashboard participant list;
* does not store usernames or analysis results.

Support for project-specific content namespaces, richer activity visualizations, and additional Wikimedia projects is still being developed.

## Methodology

Retention Checker measures editing activity after a selected activity or reference date. The results show whether participants continued editing, but they do not prove that the activity caused that continued participation.

Some retention definitions and visualization ideas are informed by:

Gutiérrez, Silvia and Krishna Chaitanya Velaga. Editor Retention: An Approximation. Wikimedia Foundation. CC BY 4.0.

## License

Distributed under the MIT License. See LICENSE for more information.

## Contact

Carla Toro — Soylacarli⁠￼

Developed with the support of Wikimedia Chile⁠￼.
