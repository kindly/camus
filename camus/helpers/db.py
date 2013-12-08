import sqlalchemy
import uuid

_engines = {}
_pg_types = {}

def create_db_tables(engine):
    context = {}
    connection = engine.connect()
    context['db.connection'] = connection

    trans = connection.begin()
    try:
        execute_sql(context, 
            '''
            create table if not exists "user"(
            user_id text not null unique,
            email text not null unique,
            name text not null,
            properties json
            );

            create table if not exists "contact"(
            contact_id text not null unique,
            email text not null unique,
            email_history json,
            code text,
            name text,
            adressee text,
            address_line_1 text,
            address_line_2 text,
            town text,
            county text,
            postcode text,
            address_history json,
            contact_date timestamp,
            lists text[],
            properties json
            );

            create table if not exists "contact_list"(
            contact_list_id text not null unique,
            name text not null unique,
            properties json
            );

            create table if not exists "donation"(
            donation_id text not null unique,
            contact_id text not null unique,
            codes text, 
            amount money,
            type text,
            frequency text,
            date text,
            external_reference text,
            properties json
            );

            create table if not exists "transaction"(
            donation_id text not null unique,
            contact_id text not null unique,
            code text,
            amount money,
            properties json
            );

            create table if not exists "code"(
            code_id text not null unique,
            code text not null unique,
            code_type text not null,
            properties json
            );

            '''
        )
        trans.commit()
    finally:
        connection.close()

def drop_db_tables(engine):
    context = {}
    connection = engine.connect()
    context['db.connection'] = connection
    trans = connection.begin()
    try:
        execute_sql(context, 'drop table "user"')
        execute_sql(context, 'drop table "contact"')
        trans.commit()
    finally:
        connection.close()

def setup(context, config):
    engine = get_engine(context, config)
    create_db_tables(engine)

def teardown(context, config):
    engine = get_engine(context, config)
    drop_db_tables(engine)

def setup_request(context, config):
    engine = get_engine(context, config)
    context['db.connection'] = engine.connect()
    context['db.transaction'] = context['db.connection'].begin()

def after_request(context, config):
    if not context.get('db.rollback'):
        context['db.transaction'].commit()

def teardown_request(context, config):
    context['db.connection'].close()

def get_engine(context, data_dict):
    db_name = data_dict.get('DB_NAME', 'main')
    engine = _engines.get(db_name)
    if not engine:
        engine = sqlalchemy.create_engine(data_dict['DB_URL'],
                                          echo=data_dict.get('DB_ECHO', False))
        _engines[db_name] = engine
    return engine

def get_type(context, oid):
    if not _pg_types:
        connection = context['db.connection']
        results = connection.execute(
            'select oid, typname from pg_type;'
        )
        for result in results:
            _pg_types[result[0]] = result[1]

    return _pg_types[oid]

def _convert_jsonable(value):
    if any([isinstance(value, basestring),
           isinstance(value, int),
           isinstance(value, float),
           isinstance(value, bool)]):
        return value
    if value is None:
        return None
    return str(value)

def dictize_results(context, results):
    jsonable = context.get('db.make_jsonable', False)
    result = {}
    data = []
    fields = []
    result['fields'] = fields
    result['data'] = data

    for field in results.cursor.description:
        fields.append(
            {'name': field[0],
             'type': get_type(context, field[1])}
        )

    for row in results:
        row_data = {}
        for num, value in enumerate(row):
            if jsonable:
                value = _convert_jsonable(value)
            row_data[fields[num]['name']] = value
        result['data'].append(row_data)

    result['count'] = results.rowcount

    return result

def execute_sql(context, sql, *args):
    connection = context['db.connection']

    results = connection.execute(sql, *args)

    #not a select statement
    if not results.cursor:
        if results.rowcount > 0:
            return {'count': results.rowcount}
        else:
            #if create/drop table
            return {}

    return dictize_results(context, results)

def insert_dict(context, data_dict):

    table_name = data_dict.pop('__table')
    primary_key = "%s_id" % table_name

    primary_key_value = data_dict.get(primary_key)

    if not data_dict.get(primary_key):
        primary_key_value = str(uuid.uuid4())
        data_dict[primary_key] = primary_key_value

    sql_columns = ", ".join(['"%s"' % key for key in data_dict.keys()])
    sql_values = ", ".join(['%s' for key in data_dict.keys()])

    result = execute_sql(
        context,
        'insert into "%s" (%s) values (%s)' % (table_name, sql_columns, sql_values),
         *data_dict.values()
    )

    return result

def update_dict(context, data_dict, table=None):

    table_name = data_dict.pop('__table', table)
    if not table_name:
        raise AttributeError, 'Table needs to be supplied to update'

    primary_key = "%s_id" % table_name
    primary_key_value = data_dict[primary_key]

    update_clauses = []
    params = []

    for key, value in data_dict.iteritems():
        update_clauses.append(""""%s" = %%s""" % key)
        params.append(value)
    update_columns = ', '.join(update_clauses)

    where_clause = """"%s" = %%s""" % (primary_key)
    params.append(primary_key_value)

    result = execute_sql(
        context,
        'update "%s" set %s where %s' % (table_name, update_columns, where_clause),
         params
    )

    return result
