# django-expression-index

[![PyPI](https://img.shields.io/pypi/v/django-expression-index.svg)](https://pypi.org/project/django-expression-index/)

django-expression-index provides implementation of subclass of `django.db.models.Index`, which enables indexing tables using expressions.

In Django 3.2 this solution is obsoleted by built-in support of expression index.

## What problem does this solve?

Currently `django.db.models.Index` only accepts field names in `fields` parameter. There is no way to add expression index other than using raw SQL.

This project implements `ExpressionIndex` class, which accepts list  of any `django.db.models.expressions.Expression` in its `expressions` parameter.

## How to use it?

Here is an example of adding index based on lowercased `models.CharField` value.

```python
from django.db import models
from django.db.models.functions import Lower
from django_expression_index import ExpressionIndex

class Profile(models.Model):
    name = models.CharField(max_length=255)
    
    class Meta:
        indexes = [
            ExpressionIndex(expressions=[Lower('name')])
        ]
```

After adding `ExpressionIndex` to your `indexes`, run `makemigrations` and `migrate` commands. The following SQL code will be generated and executed on your database:
```sql
CREATE TABLE "myapp_profile" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL);
CREATE INDEX "myapp_profile_9a3539_idx" ON "myapp_profile" (LOWER("name"));
```

`ExpressionIndex` constructor replaces `fields` parameter with `expressions` parameter. All remaining parameters are relayed to `django.db.models.Index` constructor.

## How does it work?
`ExpressionIndex` overrides `create_sql` method and uses django's default query compiler to render the expression.

There is a monkey-patch implemented on `django.db.models.sql.query.Query` instance, which replaces `resolve_ref`. The patch forces using `SimpleCol` instead of `Col` class to render bare field names referred by the expression, without prefixing them with table name.

```python
    def compile_expression(self, expression, compiler):
        def resolve_ref(original, name, allow_joins=True, reuse=None, summarize=False, simple_col=False):
            return original(name, allow_joins, reuse, summarize, True)
        
        query=compiler.query
        query.resolve_ref=partial(resolve_ref, query.resolve_ref)
        expression=expression.resolve_expression(query, allow_joins=False)
        sql, params=expression.as_sql(compiler, compiler.connection)
        return sql % params
```

If you know a better solution, please let me know!

## Compatibility

It was tested with Django 2.2.13 and 3.x.
In release 0.2.0 code was updated to make it compatible with Django 3.2
