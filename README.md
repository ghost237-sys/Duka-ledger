# Duka Ledger / Faida POS

An offline-first, full-stack Point of Sale (POS) system engineered specifically for local Kenyan shopkeepers (*duka* owners). This application ensures seamless cash register operations even in areas with low or unstable network connectivity, while synchronizing transactions and pricing structures back to a central cloud server whenever online.

---

## 🏗 System Architecture

The project is structured as a decoupled monorepo containing a high-performance backend API and a cross-platform mobile frontend:

*   **Backend:** FastAPI (Python 3) with SQLAlchemy ORM, Pydantic validation, and PostgreSQL (production) / SQLite (development).
*   **Frontend:** React Native via Expo (JavaScript) with local SQLite databases for local caching and transaction queueing.
*   **Deployment:** Render Blueprint configuration (`render.yaml`) orchestrating FastAPI containerization and managed cloud databases.

```mermaid
graph TD
    subgraph Mobile Device (Offline-First)
        App[React Native/Expo UI] --> DB[(Local SQLite)]
        App --> Outbox[Outbox Queue]
        Sync[Background Sync Worker] --> Outbox
    end
    subgraph Cloud Server
        Sync <--> API[FastAPI Web Service]
        API <--> CloudDB[(PostgreSQL)]
        Admin[HTML Admin Dashboard] --> API
    end
```

---

## 🚀 Key Production-Ready Features

### 1. Offline-First Sync & Caching Architecture
*   **Zero-Block UI Startup:** The mobile checkout page prioritizes speed by immediately rendering cached data from local SQLite tables rather than blocking on API fetches. Catalog refreshes execute silently in the background and patch local tables once received.
*   **Queue-Based Synchronization:** Sales made offline are cached in a local outbox database. A background sync runner manages transaction serialization and pushes batches to the backend once connectivity is re-established.

### 2. Bidirectional Pricing Conflict Resolution
*   To ensure pricing integrity across multiple shopkeeper devices, pricing models are governed by a stateful sync flag:
    *   If a shopkeeper sets a price during checkout, the item is tagged locally as `is_pending_sync = 1`. This prevents background catalog updates from overwriting the price.
    *   Once the server successfully processes the price update API request (`PATCH /skus/{id}`), the flag is cleared (`0`), allowing the new price to propagate globally to other shopkeepers.

### 3. Role-Based Access Control (RBAC)
*   **Shopkeeper View:** Restricts staff to the core Checkout register screen, preventing access to back-office metrics.
*   **Owner View:** Unlocks management screens including detailed sales history logs, inventory configurations, team member registrations, and financial analytics.

### 4. Interactive Category Management
*   An advanced category assignment UI allows owners to rename category directories and manage SKU associations at scale. 
*   Includes a real-time SKU search bar and toggles to dynamically link or unlink items within categories via localized product mapping.

### 5. Sales Logs with Advanced Query Engine
*   A client-side query filter on the Sales History screen allows owners to search logs instantly.
*   Supports filtering by:
    *   **Text/Entities:** Item names or transaction shopkeeper names.
    *   **Numeric:** Total transaction amounts.
    *   **Time Periods:** Contextual chips for *All Time*, *Today*, *Yesterday*, *Last 7 Days*, and *This Month*.

### 6. Admin Panel with Bulk Import Engine
*   Includes an administrative interface for mass catalog configuration.
*   Features a **Bulk Catalog Import** page enabling developers and administrators to copy-paste Excel or CSV grids directly to automatically resolve categories, populate products/brands, and insert SKUs.

---

## 📂 Codebase Layout

```
├── pos-backend/                # FastAPI application root
│   ├── app/
│   │   ├── routers/            # API routing modules (products, sync, admin, etc.)
│   │   ├── main.py             # FastAPI entrypoint
│   │   ├── models.py           # SQLAlchemy database schemas
│   │   └── database.py         # DB engines & session providers
│   ├── requirements.txt        # Backend dependencies
│   └── render.yaml             # Render Blueprint cloud deployment file
│
└── duka-ledger/                # React Native application root
    ├── screens/                # Mobile view screens (Checkout, Sales, Inventory)
    ├── sync.js                 # Network sync outbox runner & local APIs
    ├── database.js             # Local SQLite database configurations
    ├── App.js                  # Main navigation layout
    └── config.js               # Network API configuration
```

---

## 🛠 Local Development Setup

### Backend (FastAPI)
1. Navigate to the backend directory:
   ```bash
   cd pos-backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server (configured on port `8002` to avoid local Daphne/Django interface conflicts):
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
   ```

### Frontend (Expo Mobile App)
1. Navigate to the mobile directory:
   ```bash
   cd duka-ledger
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Expo builder:
   ```bash
   npx expo start
   ```

---

## ☁ Production Deployment

The project is pre-configured for automated cloud deployment via **Render Blueprint**:

1. Push the codebase to a GitHub repository.
2. Log into the Render dashboard and create a **New Blueprint**.
3. Select your repository. Render will automatically parse the `render.yaml` file to provision:
    *   A managed **PostgreSQL Database** instance.
    *   A **FastAPI Web Service** running the Uvicorn production container.
4. Copy your live web service URL and update [duka-ledger/config.js](file:///home/mwania/Desktop/projects/Pos/duka-ledger/config.js) to point to the production API.
