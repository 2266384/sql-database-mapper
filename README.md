# SQL Database Mapper

A deployable web application that contains functions to scan and document the structure of one or more database schema.

## Features

- Store multiple database configuration details
- Test database connection
- Scan database schema and generate summary dashboard page
- Produce interactive entity relationship diagram from scan


## Project Structure

```text
SQL Database Mapper/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── database/
│   │   └── ...
│   │
│   ├── models/
│   │   └── ...
│   │
│   ├── repositories/
│   │   └── ...
│   │
│   ├── routes/
│   │   └── ...
│   │
│   ├── schemas/
│   │   └── ...
│   │
│   ├── security/
│   │   └── ...
│   │
│   ├── services/
│   │   └── ...
│   │
│   ├── static/
│   │   ├── css/
│   │   ├── images/
│   │   └── js/
│   │
│   ├── tasks/
│   │   └── ...
│   │
│   ├── templates/
│   │   └── ...
│   │
│   └── utils/
│       └── ...
│
├── dbscans/
│   └── ...
│
├── migrations/
│   └── versions/
│       └── ...
│
├── .env.example
├── .gitignore
├── make_celery.py
├── requirements.txt
├── run.py
└── README.md
```

## Directory Overview

### `app/models`

Contains SQLAlchemy database models.

Each database model should normally be defined in its own module.

```text
models/
├── user.py
├── product.py
└── ...
```

Models should primarily describe database structure and relationships rather than contain application business logic.


### `migrations`

Contains the database migration files generated and managed by Flask-Migrate and Alembic.

Database migrations provide version control for changes to the application's database schema. Rather than manually modifying the database structure, changes to SQLAlchemy models can be detected and recorded as migration scripts.

The migration system allows database schema changes to be:

- Created from changes to SQLAlchemy models
- Applied to the database
- Reverted when required
- Tracked through migration history
- Applied consistently across development, testing and production environments

The `migrations` directory is created using:

```bash
flask db init
```

Once initialised, the directory contains the Alembic configuration and migration environment.

```text
migrations/
├── versions/
│   └── <migration files>
├── alembic.ini
├── env.py
├── README
└── script.py.mako
```

The important parts are:
- `versions/` — Contains the generated migration scripts.
- `alembic.ini` — Alembic configuration.
- `env.py` — Configures how Alembic interacts with the Flask application and SQLAlchemy metadata.
- `script.py.mako` — Template used when generating new migration scripts.

### Creating a Migration

After making changes to the SQLAlchemy models, create a new migration:

```bash
flask db migrate -m "Describe the database changes"
```

The migration should be reviewed before being applied, particularly when it contains changes that could result in data loss.

### Applying Migrations

Apply pending migrations to the database using:

```bash
flask db upgrade
```

This brings the database schema up to the latest migration version.

### Rolling Back a Migration

To revert the most recently applied migration:

```bash
flask db downgrade
```

Migration rollback should be used with care, particularly in environments containing production data.

### Optional: View migration history

To display the available migration history:

```bash
flask db history
```

You can also check the current database migration:

```bash
flask db current
```

### Migration Workflow

The recommended workflow when changing the database schema is:

1. Modify the SQLAlchemy model.
1. Generate a new migration.
1. Review the generated migration script.
1. Test the migration against the development database.
1. Commit the migration script to source control.
1. Deploy the application and migration to the target environment.
1. Apply the migration to the target database.

Migration files should be committed to the repository so that the database schema can be reproduced consistently across environments.


**`migrations/` should be committed to Git**, including the files under `migrations/versions/`. The database itself should not be committed.


### `app/repositories`

Contains database access and query logic.

Repositories provide an abstraction between the rest of the application and the database, helping keep database queries out of routes and business logic.

```text
repositories/
├── user_repository.py
└── ...
```

### `app/routes`

Contains the HTTP routes for the application.

Routes should primarily be responsible for:

1. Receiving the HTTP request
1. Validating or parsing request data
1. Calling the appropriate service
1. Returning a response

Business logic should generally remain in the service layer.

### `app/schemas`

Contains schemas used to define and validate data exchanged through application endpoints.

Keeping schemas separate from database models helps prevent the API representation of data from becoming tightly coupled to the database structure.

### `app/services`

Contains the application's business logic.

Services coordinate repositories and other application components and should contain the logic that determines how the application behaves.

The general flow is:

```text
Route
  │
  ▼
Service
  │
  ▼
Repository
  │
  ▼
Database
```

### `app/static`

Contains files served directly to the client.

```text
static/
├── css/
├── images/
└── js/
```

CSS, JavaScript and image files should be placed in their appropriate directories.

### `app/templates`

Contains Jinja2 HTML templates.

A typical template structure might be:

```text
templates/
├── base.html
├── index.html
└── ...
```

Templates can extend a common `base.html` layout using Jinja template inheritance.

### `app/utils`
Contains reusable utility functions that do not belong specifically to a model, repository, route or service.

## Requirements
The template requires:

- Python 3
- pip
- Git

Python dependencies are listed in `requirements.txt`.

## Getting Started

### 1. Create a Repository from the Template

On GitHub, select Use this template → Create a new repository to create a new project from this template.

Alternatively, clone the repository directly:

```bash
git clone https://github.com/2266384/flask_webapp_template.git
cd flask_webapp_template
```

### 2. Create a Virtual Environment

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example environment file:

```bash
cp .env.example .env
```

Then update `.env` with the configuration required for your application.

**Do not commit `.env` to source control.**

The `.env.example` file should contain example values and variable names only.

## Running the Application
Ensure Redis is running in the docker container and execute the following command to confirm:

```bash
docker ps
```

You can confirm the connection to the Redis docker container with:
```bash
docker exec -it <container name> redis-cli ping
```

Expected response will be `PONG`


Navigate to the folder and start the application using:

```bash
source .venv/bin/active
flask run
```

You can include the optional parameter `--debug` when running the flask container if needed.

Start the Celery worker in a second terminal:

```bash
source .venv/bin/activate
celery -A make_celery:celery_app worker --pool=solo --concurrency=1 --loglevel=INFO
```

The application will then be available through the local Flask development server.

## Development Guidelines
The template follows a separation-of-concerns approach.

### Routes
Keep routes thin.

```text
HTTP Request
     │
     ▼
   Route
     │
     ▼
  Service
     │
     ▼
 Repository
     │
     ▼
 Database
 ```

Avoid putting substantial business logic or complex database queries directly into route handlers.

### Services
Services should contain application and business logic and coordinate operations between repositories and other application components.

### Repositories
Repositories should contain database access and query logic.
This keeps SQLAlchemy-specific operations isolated from the rest of the application.

### Models
Models should represent database entities and their relationships.

### Templates
Templates should primarily be responsible for presentation.
Avoid placing application business logic in Jinja templates.

## Adding a New Feature
For a typical database-backed feature, consider adding components to each relevant layer:

```text
app/
├── models/
│   └── new_feature.py
│
├── repositories/
│   └── new_feature_repository.py
│
├── routes/
│   └── new_feature.py
│
├── schemas/
│   └── new_feature.py
│
├── services/
│   └── new_feature_service.py
│
└── templates/
    └── new_feature/
        └── index.html
```

Not every feature requires every layer. Keep the structure as simple as possible while maintaining a useful separation of responsibilities.

## Environment Configuration
Environment-specific configuration should be stored outside the application source code where practical.

Use: `.env` for local configuration and `.env.example` as the documented template for required variables.

Never commit secrets, passwords, API keys or production credentials to the repository.

## Production
This repository is intended primarily as a development and application starter template.

The Flask development server should not be used as the production web server.

Before deploying a project created from this template, configure:
- A production WSGI server
- Production environment variables
- production database
- Secret management
- HTTPS
- Logging
- Error handling
- Appropriate security configuration


## Customising the Template
After creating a new application from this repository, the following are typically customised first:

1. Rename the application/package as required.
1. Update the application configuration.
1. Configure environment variables.
1. Add database models.
1. Add repositories for database operations.
1. Add services containing business logic.
1. Add routes/endpoints.
1. Add schemas where data validation is required.
1. Add templates and static assets.
1. Add automated tests.


## Architecture
The template uses a layered architecture:

```text
┌─────────────────────┐
│       Routes        │
│   HTTP / Requests   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Services       │
│   Business Logic    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Repositories     │
│   Database Access   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Models        │
│   Database Schema   │
└─────────────────────┘
```

Presentation is handled separately through:

```text
Routes
   │
   └──► Templates
          │
          └──► Static Assets
```

This separation makes individual parts of the application easier to develop, test and maintain.

## Why This Structure?
Flask does not enforce a particular application layout, allowing developers to choose an architecture appropriate for their project.

This template deliberately separates the major application responsibilities so that a project can grow without placing everything into a single app.py file.

The objective is to provide a consistent starting point for new Flask applications while keeping the architecture understandable and easy to extend.
