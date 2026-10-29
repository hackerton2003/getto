# Getto Platform Database

Database engine:

PostgreSQL

Spatial extension:

PostGIS

Database schema changes are managed through Django migrations.

Database designer responsibilities:

- ERD
- Tables
- Relationships
- Constraints
- Indexes
- PostgreSQL/PostGIS design
- Database documentation

The frontend must never connect directly to PostgreSQL.

The backend communicates with PostgreSQL through Django ORM.
