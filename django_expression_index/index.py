from django.db import models
from django.db.backends.utils import names_digest, split_identifier
from functools import partial

class ExpressionIndex(models.Index):
    def __init__(self, *, expressions=(), name=None, db_tablespace=None, opclasses=(), condition=None):
        super().__init__(fields=[str(e) for e in expressions], 
                         name=name, db_tablespace=db_tablespace, 
                         opclasses=opclasses, condition=condition)
        self.expressions=expressions
    
    def deconstruct(self):
        path, _, kwargs = super().deconstruct()
        kwargs.pop('fields')
        kwargs['expressions'] = self.expressions
        return path, (), kwargs
    
    def set_name_with_model(self, model):
        self.fields_orders=[(model._meta.pk.name,'')]
        _, table_name = split_identifier(model._meta.db_table)
        digest=names_digest(table_name, *self.fields, length=6)
        self.name=f"{table_name[:19]}_{digest}_{self.suffix}"
        
    def create_sql(self, model, schema_editor, using='', **kwargs):
        
        class Descriptor:
            db_tablespace=''
            def __init__(self, expression):
                self.column=str(expression)
        
        col_suffixes = [''] * len(self.expressions)
        condition = self._get_condition_sql(model, schema_editor)
        statement= schema_editor._create_index_sql(
            model, [Descriptor(e) for e in self.expressions], 
            name=self.name, using=using, db_tablespace=self.db_tablespace,
            col_suffixes=col_suffixes, opclasses=self.opclasses, condition=condition,
            **kwargs,
        )
        
        compiler=model._meta.default_manager.all().query.get_compiler(connection=schema_editor.connection)
        statement.parts['columns'] = ", ".join(
            [self.compile_expression(e, compiler) for e in self.expressions])
        return statement
    
    def compile_expression(self, expression, compiler):
        def resolve_ref(original, name, allow_joins=True, reuse=None, summarize=False, simple_col=False):
            return original(name, allow_joins, reuse, summarize, True)
        
        query=compiler.query
        query.resolve_ref=partial(resolve_ref, query.resolve_ref)
        expression=expression.resolve_expression(query, allow_joins=False)
        sql, params=expression.as_sql(compiler, compiler.connection)
        return sql % params

