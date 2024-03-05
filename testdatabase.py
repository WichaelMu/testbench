import os
import sqlalchemy as alchemy
import sqlalchemy.orm as orm
from api_common import get_secret
from testbench import *
from testdatabasedefinition import get_table_definition

decltype_map = {
    'UINT8': alchemy.Integer,
    'DATETIME': alchemy.DateTime
}


class PyMSSQLEngineSecrets:
    def __init__(self, dbname, engine, host, password, port, username):
        self.dbname   = dbname
        self.engine   = engine
        self.host     = host
        self.password = password
        self.port     = port
        self.username = username
    
    def sanitise(self, field):
        field = field.replace(':', '%3A')
        field = field.replace('@', '%40')
        field = field.replace('/', '%2F')
        return field

    def sanitise_fields(self):
        self.dbname   = self.sanitise(self.dbname)
        self.engine   = self.sanitise(self.engine)
        self.host     = self.sanitise(self.host)
        self.password = self.sanitise(self.password)
        self.port     = self.sanitise(self.port)
        self.username = self.sanitise(self.username)


def get_database_secrets() -> PyMSSQLEngineSecrets:
    """Returns MS SQL Database Authentication secrets."""
    # secret = get_secret (secret_name = os.environ['SECRET_NAME'], secret_stage = 'AWSCURRENT')
    sqlserver_secrets = get_secret(secret_name=os.environ['MSSQL_SECRETS'], secret_stage='AWSCURRENT')
    dbname   = sqlserver_secrets['dbname']
    engine   = sqlserver_secrets['engine']
    host     = sqlserver_secrets['host']
    password = sqlserver_secrets['password']
    port     = sqlserver_secrets['port']
    username = sqlserver_secrets['username']

    return PyMSSQLEngineSecrets(dbname, engine, host, password, port, username)


def decltype(expression):
    """Get the Declaring Type of a column."""
    if ('ColumnType' not in expression):
        debug ('ColumnType is not in expression!')
        # raise KeyError('ColumnType is not in the given Expression!')

    column_type = expression['ColumnType']
    if (column_type == 'STRING'): # STRING requires expression, so it can't be mapped easily...
        return alchemy.String(int(expression.get('ColumnLength', 1 << 12)))

    if (column_type in decltype_map):
        return decltype_map[column_type]

    debug (F'Failed to convert {column_type} to a valid SQL Alchemy Type.')
    # raise ValueError(F'ColumnType: {column_type} is not supported!')

def establish_connection(ref_id, course_metadata) -> tuple[alchemy.Engine | None, alchemy.Connection | None, alchemy.MetaData | None]:
    """Connects and returns the necessary connection database objects."""
    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "DATABASE.ESTABLISH_CONNECTION",
        tracemessage = "Establishing connection to database.",
        status       = Status.START,
        action       = "DISPATCH.ESTABLISH_CONNECTION",
        metadata     = course_metadata,
    )
    try:
        secrets: PyMSSQLEngineSecrets = get_database_secrets()
    except Exception as ex:
        derr (F'Failed to retrieve connection secrets.\nReason:\t{ex}')
        dbg.trace (
                ulid         = ref_id,
                tracepoint   = "DATABASE.ESTABLISH_CONNECTION",
                tracemessage = "Failed to retrieve connection secrets to database.",
                status       = Status.FAILURE,
                action       = "DISPATCH.ESTABLISH_CONNECTION",
                metadata     = course_metadata,
                verbosity    = Verbosity.ERROR
            )
        return None, None, None
    secrets.sanitise_fields()

    try:
        engine = alchemy.create_engine(F'mssql+pymssql://{secrets.username}:{secrets.password}@{secrets.host}:{secrets.port}/{secrets.dbname}')
        cnx = engine.connect()
        meta = alchemy.MetaData()

        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "DATABASE.ESTABLISH_CONNECTION",
            tracemessage = "Connection to database established.",
            status       = Status.SUCCESS,
            action       = "DISPATCH.ESTABLISH_CONNECTION",
            metadata     = course_metadata,
        )
        return engine, cnx, meta
    except Exception as ex:
        derr (F'Failed to establish a connection to database.\n\t{ex}')
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "DATABASE.ESTABLISH_CONNECTION",
            tracemessage = "Failed to establish a connection to database.",
            status       = Status.FAILURE,
            action       = "DISPATCH.ESTABLISH_CONNECTION",
            metadata     = course_metadata,
            verbosity    = Verbosity.ERROR
        )
        return None, None, None


def inject_ahegs(engine, meta, argv, ref_id, course_metadata):
    """
    Inserts `argv` into database `engine` with `meta`data.
    
    Assumes `argv` is mapped and keyed with UTS_AHEGS specifications.
    """
    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "DATABASE.INJECTION",
        tracemessage = "Injecting AHEGS data into MS SQL database.",
        status       = Status.START,
        action       = "DISPATCH.INJECT",
        metadata     = course_metadata,
    )
    UTS_TABLE_DEFINITION = get_table_definition()['Tables'][0]

    table_name = UTS_TABLE_DEFINITION.get('TableName', 'CMM_AHEGS')
    UTS_AHEGS = alchemy.Table(table_name, meta)

    for table_column in UTS_TABLE_DEFINITION.get('TableColumns', []):
        column_name = table_column['ColumnName']
        is_column_nullable = table_column.get('ColumnNullable', True)
        is_primary_key = table_column.get('ColumnIsPk', False)
        declaring_type = decltype(table_column)
        UTS_AHEGS.append_column(alchemy.Column(column_name, declaring_type,
                                       primary_key = is_primary_key,
                                       nullable = is_column_nullable),
                                replace_existing = True)

    meta.create_all(engine)

    # Insert UTS_AHEGS fields into database.
    #
    debug ('Inserting AHEGS fields...')
    session = orm.Session(engine)
    try:
        session.execute(alchemy.insert(UTS_AHEGS), [ argv ])
        session.commit()
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "DATABASE.INJECTION",
            tracemessage = "Insert/s injected and committed into database.",
            status       = Status.SUCCESS,
            action       = "DISPATCH.INJECT",
            metadata     = course_metadata,
        )
    except Exception as exception:
        derr (F'Insert/s failed to commit.\nException:\n\t{exception}')
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "DATABASE.INJECTION",
            tracemessage = "Insert/s failed to inject and commit into database.",
            status       = Status.FAILURE,
            action       = "DISPATCH.INJECT",
            metadata     = course_metadata,
            verbosity    = Verbosity.ERROR
        )
    finally:
        dmess ('Closing Session...')
        session.close()
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "DATABASE",
            tracemessage = "Closing Database Session.",
            status       = Status.END,
            action       = "DISPATCH.INJECT",
            metadata     = course_metadata,
        )