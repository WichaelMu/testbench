

def get_table_definition():
    return {
        "TableCount": "1",
        "Tables": [
            {
                "TableName": "CMM_AHEGS",
                "TablePath": "cmmdb",
                "TableOwner": "WichaelMu",
                "TableColumnsTotal": "24",
                "TableColumns": [
                # {
                #     "ColumnName": "ts",
                #     "ColumnType": "STRING",
                #     "ColumnNullable": False,
                #     "ColumnIsPk": True,
                #     "ColumnLength": "36"
                # },
                {
                    "ColumnName": "HARVEST_YEAR",
                    "ColumnType": "STRING",
                    "ColumnLength": "4"
                },
                {
                    "ColumnName": "HARVEST_PERIOD",
                    "ColumnType": "STRING",
                    "ColumnLength": "32"
                },
                {
                    "ColumnName": "HARVEST_DATE",
                    "ColumnType": "UINT8"
                },
                {
                    "ColumnName": "CODE",
                    "ColumnType": "STRING",
                    "ColumnLength": "16"
                },
                {
                    "ColumnName": "VERSION",
                    "ColumnType": "STRING",
                    "ColumnLength": "16"
                },
                {
                    "ColumnName": "COURSENAME",
                    "ColumnType": "STRING",
                    "ColumnLength": "256"
                },
                {
                    "ColumnName": "ADMISSIONREQUIREMENTS",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "MINIMUMDURATION",
                    "ColumnType": "STRING",
                    "ColumnLength": "32"            
                },
                {
                    "ColumnName": "INDUSTRIALTRAINING",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "COURSESTRUCTURE1",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "OVERSEASSTUDY",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "ARTICULATION",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "FURTHERSTUDY",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "PROFESSIONALRECOGNITION",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "LEVELOFAWARD",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "HONOURS",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "LOADEFTSL",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "CREATE_DT",
                    "ColumnType": "UINT8"
                },
                {
                    "ColumnName": "STDACADEMICREQ",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "ACADEMICREQALL",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "ACADEMICREQLOCAL",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "ACADEMICREQINT",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "GRADUATEPRIORSTUDY",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "FULLTIMEDURATION",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "FULLTIMEDURATIONUNIT",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "PARTTIMEDURATION",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                },
                {
                    "ColumnName": "PARTTIMEDURATIONUNIT",
                    "ColumnType": "STRING",
                    "ColumnLength": "4096"
                }
            ]
        }
    ]
}
