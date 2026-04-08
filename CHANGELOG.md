# Changelog

All notable changes to the StockPilot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added

- **Authentication System**
  - JWT-based authentication with access and refresh tokens
  - User registration with email validation and secure password hashing (bcrypt)
  - Login and logout endpoints with token rotation
  - Role-based access control (admin and standard user roles)
  - Protected route middleware for authenticated endpoints

- **Inventory CRUD with Ownership**
  - Full create, read, update, and delete operations for inventory items
  - Ownership enforcement ensuring users can only manage their own inventory
  - Pagination and filtering support for inventory listing
  - Search functionality across item names and descriptions
  - Bulk operations for inventory updates

- **Category Management**
  - Create, read, update, and delete categories for organizing inventory
  - Hierarchical category support
  - Category-based filtering for inventory items
  - Default categories seeded on initial setup

- **User Management**
  - User profile viewing and editing
  - Password change functionality with current password verification
  - Admin ability to list, activate, and deactivate user accounts
  - User activity tracking and last login timestamps

- **Admin Dashboard**
  - Overview statistics including total users, items, and categories
  - System-wide inventory summary with aggregated metrics
  - User management interface for administrative operations
  - Activity logs for auditing administrative actions

- **Low-Stock Alerts**
  - Configurable low-stock thresholds per inventory item
  - Automatic detection of items falling below threshold levels
  - Low-stock alert endpoint returning items requiring attention
  - Summary counts of items in low-stock status on the dashboard

- **Responsive UI**
  - Mobile-first responsive design using Tailwind CSS
  - Dark mode support with system preference detection
  - Accessible components following WCAG guidelines
  - Interactive data tables with sorting and filtering
  - Toast notifications for user feedback on actions

- **Vercel Deployment Support**
  - Vercel configuration for seamless deployment
  - Environment variable management for production settings
  - CORS configuration for cross-origin frontend requests
  - Health check endpoint for deployment monitoring
  - Static asset serving and API route configuration

### Technical Details

- **Backend**: Python 3.12 with FastAPI framework
- **Database**: SQLAlchemy 2.0 with async session support
- **Validation**: Pydantic v2 models for request/response schemas
- **Security**: Passlib bcrypt for password hashing, python-jose for JWT tokens
- **Testing**: pytest with httpx AsyncClient for API integration tests
- **Configuration**: Pydantic Settings with `.env` file support