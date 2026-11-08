# Tapick
**Never out of reach.**

Tapick is a pharmacy management system for pharmacies with multiple branches. Its main feature is a real-time cross-branch stock locator. When a medicine is out of stock locally, the system finds and notifies the nearest branch that has it. This reduces the need for phone calls between branches, which are slow and unreliable during busy hours.

Built with Django for CSIT327 (Information Management 2) at Cebu Institute of Technology – University.

---

## The Problem

Pharmacists currently phone other branches to check stock. This delays customer service during busy hours and risks losing customers to competitors. Without real-time visibility across branches, it is hard to tell quickly which nearby branch has a medicine.

## Objectives

- Keep a centralized database of medicine inventory across all branches, with stock changes reflected system-wide within 5 seconds.
- Help pharmacists search for unavailable medicines and find the nearest branch that has them in stock.
- Improve how quickly pharmacists answer customer inquiries.
- Show clear, accurate information: stock levels, branch locations, and timestamps.
- Provide real-time updates on medicine availability.
- Run a rule-based notification engine with at least 90% accuracy in triggering the correct alert.

## Limitations

- **No clinical data.** Only stock, price, and branch location are tracked. No dosage, molecular, or efficacy data.
- **No logistics tracking.** Delivery, courier, and transfer logistics are not tracked.
- **Single-company scope.** Only branches within one pharmaceutical company are managed.
- **Decision support only.** Licensed pharmacists decide whether to act on a notification.

## Tech Stack

- **Backend:** Django, Python
- **Database:** PostgreSQL (hosted on Supabase)
- **Frontend:** Django templates, HTML, CSS, JavaScript
- **Config:** python-decouple (`.env`)
- **Fonts:** Montserrat, Manrope

## Project Structure

```
Tapick/
├── manage.py
├── requirements.txt
├── config/              # Project settings and root URLs
├── apps/                # One folder per feature (vertical slices)
│   ├── landing/
│   ├── login/
│   ├── register/
│   ├── home/            # Dashboard
│   ├── profiles/
│   └── user_settings/
├── templates/           # One folder per app, plus base.html
└── static/              # css/ and js/, organized per app
```

## Getting Started

### Prerequisites

- Python 3.12 or newer
- Git
- A PostgreSQL database (for example, a Supabase project)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/sjq-158/Tapick.git
cd Tapick

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows (cmd)
# venv\Scripts\Activate.ps1    # Windows (PowerShell)
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt


### Run the App

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. If port 8000 is busy, run `python manage.py runserver 8080`.

## Routes

| Path | Page |
|---|---|
| `/` | Landing |
| `/login/` | Login |
| `/register/` | Register |
| `/dashboard/` | Dashboard |
| `/profile/` | Profile |
| `/settings/` | Settings |
| `/admin/` | Django admin |



## License

Academic project for CSIT327 at Cebu Institute of Technology – University.