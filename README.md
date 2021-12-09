# django-dbcleanup

Easily monitor database usage - and clean it up (based on your django models)

This pluggable app provides:
* visibility over database disk space usage for your models
* command to remove unused tables and recover disk space

## Usage

`dbcleanup.Table` is an unmanaged model mapped to information tables in MySQL and PostgreSQL and added to django admin
