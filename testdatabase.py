import sqlalchemy as alchemy
import sqlalchemy.orm as orm
import pandas as pd
from testbench import *
from testdatabasedefinition import get_table_definition


def __decltype__(expression):
    if ('ColumnType' not in expression):
        debug ('ColumnType is not in expression!')
        # raise KeyError('ColumnType is not in the given Expression!')

    column_type = expression['ColumnType']
    if (column_type == 'STRING'):
        return alchemy.String(int(expression.get('ColumnLength', 1 << 12)))
    if (column_type == 'UINT8'):
        return alchemy.Integer

    debug (F'Failed to convert {column_type} to a valid SQL Alchemy Type.')
    # raise ValueError(F'ColumnType: {column_type} is not supported!')

def establish_connection():
    debug ('Establishing connection to MS SQL...')
    engine = alchemy.create_engine(R'mssql+pymssql://c2c_sysadmin:IV&T*^%40CEDytvftw@verge.sm.dev.mesh.uts.edu.au/80b244f9-c82b-4d7e-a378-10576ea68925-SM')
    cnx = engine.connect()
    meta = alchemy.MetaData()
    return engine, cnx, meta


def inject_ahegs(engine, meta, argv):
    debug ('Defining UTS_AHEGS Table...')
    UTS_TABLE_DEFINITION = get_table_definition()['Tables'][0]

    debug ('Connecting to AHEGS Table in MS SQL...')
    table_name = UTS_TABLE_DEFINITION.get('TableName', 'UTS_AHEGS_NAME_DEFAULT')
    UTS_AHEGS = alchemy.Table(table_name, meta)

    debug ('Defining AHEGS Fields as Columns...')
    for table_column in UTS_TABLE_DEFINITION.get('TableColumns', []):
        column_name = table_column['ColumnName']
        is_column_nullable = table_column.get('ColumnNullable', True)
        is_primary_key = table_column.get('ColumnIsPk', False)
        decltype = __decltype__(table_column)
        UTS_AHEGS.append_column(alchemy.Column(column_name, decltype,
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
        dmess ('Insert/s committed. Closing Session...')
    except:
        derr ('Insert/s failed to commit. Closing Session...')
    finally:
        session.close()

    # Print for debug only.
    if (not RUNNING_FROM_LAMBDA):
        pd_table = pd.read_sql_table(table_name, engine)
        debug ('PRINTING...')
        debug (pd_table)


if (__name__ == '__main__'):
    dmess ('                Script Execution Begins Here...\n##############################################################')
    pd.set_option('display.max_colwidth', None)
    courses = get_courses(None);
    uts_ahegs = map_uts_ahegs(courses);
    engine, cnx, meta = establish_connection();

    for ahegs in uts_ahegs:
        inject_ahegs(engine, meta, ahegs)

    dspec ('##############################################################\n            Script Execution Terminates Here...')
    cnx.close()
