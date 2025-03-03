import debug_utils as dbg
from debug_utils import Verbosity, Status
from functional import seq

MAP_KEY = 0
MAP_VALUE = 1

def extract_location (ref_id, course):

    print (type (course))
    # Clarification: Multiple $.course_offering[].location.label

    course_offering = seq (course.items ())                \
        .map (lambda x: {x[MAP_KEY]: x[MAP_VALUE] })       \
        .filter (lambda x: 'course_offering' in x.keys ()) \
        .map (lambda x: x['course_offering'])              \
        .reduce (lambda x, y: x + y, [])

    dbg.trace (
        ulid = ref_id,
        tracepoint="extract_location ()",
        tracemessage=F"{type (course_offering)} course_offering.len () = {course_offering.len ()}\n\t{course_offering}",
        status = Status.CONTINUE,
        action = "DEBUG_VERIFY",
        verbosity = Verbosity.DEBUG
    )

    location_labels = seq (course_offering)                  \
        .filter (lambda x: 'location' in x.keys ())          \
        .filter (lambda x: 'label' in x['location'].keys ()) \
        .map (lambda x: x['location']['label'])              \
        .reduce (lambda x, y: x + y, [])

    return location_labels.first () if (location_labels.len () != 0) else ''

if __name__ == '__main__':

    course = { "sys_id": "9ece7252874ed61039b8ab0a0cbb357e", "abbr_name": "MProDev",
            "ai_association": [
                {
                    "applies_to_all_offerings": True,
                    "associated_academic_item": {
                        "class_name": "Course",
                        "code": "C04008",
                        "implementation_year": "2025",
                        "name": "Master of Property Development",
                        "nickname": "2025.01",
                        "publishing_parent_academic_orgs": [
                            {
                                "active": True,
                                "label": "Design, Architecture and Building",
                                "value": "A",
                                "sys_id": "70704f3f1b9c21d075df2069b04bcbd7",
                                "type": "OrgUnit"
                            }
                        ],
                        "status": {
                            "active": True,
                            "label": "Approved",
                            "value": "Active",
                            "sys_id": "4ee411252b9f5600155427b436da151e",
                            "type": "choice"
                        },
                        "subclass": {
                            "active": True,
                            "label": "Course",
                            "value": "course",
                            "sys_id": "927cc1b80fbccf009cd2534f62050e85",
                            "type": "choice"
                        },
                        "sys_id": "770ec32b877c461042d3ca260cbb357f",
                        "links": {
                            "self": "/courses/770ec32b877c461042d3ca260cbb357f"
                        }
                    },
                    "associated_ai_display": "C04008 Master of Property Development 2025.01",
                    "association_type": {
                        "active": True,
                        "label": "Articulated course",
                        "value": "articulated_course",
                        "sys_id": "29b862cadbbe4510d202d5b4f396197b",
                        "type": "choice"
                    },
                    "description": "<p>This course is part of an articulated program comprising the Graduate Certificate in Property Development (<a href=\"https://handbook.uts.edu.au/course/Current/c11271\">C11271</a>), the Graduate Diploma in Property Development (<a href=\"https://handbook.uts.edu.au/course/Current/c06006\">C06006</a>) and the Master of Property Development.</p>",
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "22ce7252874ed61039b8ab0a0cbb3584",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                }
            ],
            "applies_to_all_offerings": True,
            "apply_online": {
                "active": True,
                "label": "No",
                "value": "no",
                "sys_id": "8f678a7e0f3443009cd2534f62050e46",
                "type": "choice"
            },
            "aqf_level": {
                "active": True,
                "label": "Level 9 - Master's Degree (Coursework)",
                "value": "9_mast_deg_coursework",
                "sys_id": "958c0d9b0f04c3009cd2534f62050e08",
                "type": "choice"
            },
            "award": [
                {
                    "award_information": "Master of Property Development (MProDev)",
                    "award_type": {
                        "active": True,
                        "label": "Published Award Title",
                        "value": "PAT",
                        "sys_id": "7ef76873c31506107fe22c4bb0013118",
                        "type": "choice"
                    },
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "2ace7252874ed61039b8ab0a0cbb35d2",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19"
                },
                {
                    "abbreviation": "MProDev",
                    "award_title": "Master of Property Development",
                    "award_type": {
                        "active": True,
                        "label": "Masters",
                        "value": "MASTERS",
                        "sys_id": "3f88952b1bca651075df2069b04bcb17",
                        "type": "choice"
                    },
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "eece7252874ed61039b8ab0a0cbb35d2",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19"
                }
            ],
            "career_opportunities": "<p>The degree provides property-related professionals such as architects, engineers, construction managers, valuers, planners and business or finance professionals the opportunity to broaden their knowledge and qualifications and obtain a more holistic understanding of property development and related processes. This enables graduates to expand their careers or move outside of their original professional area to higher or broader roles within the property development industry and/or offer new services to clients.</p>\n<p>Graduates completing the UTS Master of Property Development Valuation sub-major meet the educational requirements for accreditation as a Certified Practising Valuer (CPV) by the Australian Property Institute.</p>",
            "class_name": "Course",
            "code": "C04008",
            "codes": [
                {
                    "applies_to_all_offerings": True,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "26ce7252874ed61039b8ab0a0cbb35d1",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19",
                    "type": {
                        "active": True,
                        "label": "Special course code",
                        "value": "special_course_code",
                        "sys_id": "8d4b19301b639d5002b942e7b04bcb60",
                        "type": "choice"
                    }
                },
                {
                    "applies_to_all_offerings": True,
                    "code": "019745C",
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "e2ce7252874ed61039b8ab0a0cbb3586",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19",
                    "type": {
                        "active": True,
                        "label": "CRICOS",
                        "value": "cricos",
                        "sys_id": "0fad592ddbd4b7400595c4048a9619d9",
                        "type": "choice"
                    }
                }
            ],
            "combinable": False,
            "course_learning_outcome": [
                {
                    "code": "CILO6",
                    "description": "<p>Understand Indigenous perspectives and interpret legal frameworks relating to land use and ownership.</p>",
                    "number": 6,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "62ce7252874ed61039b8ab0a0cbb3583",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                },
                {
                    "code": "CILO5",
                    "description": "<p>Work ethically and effectively in culturally diverse professional contexts.</p>",
                    "number": 5,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "66ce7252874ed61039b8ab0a0cbb3582",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                },
                {
                    "code": "CILO2",
                    "description": "<p>Demonstrate and apply relevant knowledge and technical and creative skills in property development.</p>",
                    "number": 2,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "66ce7252874ed61039b8ab0a0cbb3583",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                },
                {
                    "code": "CILO4",
                    "description": "<p>Develop alternative, appropriate creative solutions to built environment issues.</p>",
                    "number": 4,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "e2ce7252874ed61039b8ab0a0cbb3583",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                },
                {
                    "code": "CILO1",
                    "description": "<p>Communicate and collaborate effectively within professional property development contexts.</p>",
                    "number": 1,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "e6ce7252874ed61039b8ab0a0cbb3583",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                },
                {
                    "code": "CILO3",
                    "description": "<p>Evaluate and apply principles of law, sustainable development, and financial management within the built environment and property-related contexts.</p>",
                    "number": 3,
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "eece7252874ed61039b8ab0a0cbb3582",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18"
                }
            ],
            "course_offering": [
                {
                    "admission_calendar": {
                        "active": True,
                        "label": "Autumn Session",
                        "value": "AUT",
                        "sys_id": "3ed8d3921b364510212465fa274bcba1",
                        "type": "choice"
                    },
                    "attendance_type": [
                        {
                            "active": True,
                            "label": "Full Time",
                            "value": "FT",
                            "sys_id": "69bd72706f904300bd1853a11c3ee486",
                            "type": "choice"
                        },
                        {
                            "active": True,
                            "label": "Part Time",
                            "value": "PT",
                            "sys_id": "7c8d3e706f904300bd1853a11c3ee4d9",
                            "type": "choice"
                        }
                    ],
                    "display_name": "BLC-U-AUT",
                    "entry_point": False,
                    "language_of_instruction": {
                        "active": True,
                        "label": "English",
                        "value": "en",
                        "sys_id": "53a8434a6f54c300bd1853a11c3ee434",
                        "type": "choice"
                    },
                    "location": {
                        "active": True,
                        "label": "City campus",
                        "value": "U",
                        "sys_id": "0d4d703ddb720510d202d5b4f396192b",
                        "type": "Location"
                    },
                    "mode": {
                        "active": True,
                        "label": "On campus - Block",
                        "value": "BLC",
                        "sys_id": "ebd9b8b5db720510d202d5b4f396194a",
                        "type": "DeliveryMode"
                    },
                    "offered": True,
                    "offering_uid": "c704b2fe47d11610d42c8833036d43e9",
                    "publish": True,
                    "state": {
                        "active": True,
                        "label": "Checked",
                        "value": "checked",
                        "sys_id": "64da2ffbdbc073400595c4048a9619f0",
                        "type": "choice"
                    },
                    "student_types": [
                        {
                            "active": True,
                            "label": "International",
                            "value": "international",
                            "sys_id": "27925a40dba0fb400595c4048a961977",
                            "type": "choice"
                        },
                        {
                            "active": True,
                            "label": "Domestic",
                            "value": "domestic",
                            "sys_id": "e382da40dba0fb400595c4048a961998",
                            "type": "choice"
                        }
                    ],
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "26ce7252874ed61039b8ab0a0cbb3581",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18",
                    "unit_of_duration": {
                        "active": True,
                        "label": "Weeks",
                        "value": "weeks",
                        "sys_id": "d261ee99dbae84507f4f8a264a961999",
                        "type": "choice"
                    }
                },
                {
                    "admission_calendar": {
                        "active": True,
                        "label": "Spring Session",
                        "value": "SPR",
                        "sys_id": "0b69d7d21b364510212465fa274bcb6e",
                        "type": "choice"
                    },
                    "attendance_type": [
                        {
                            "active": True,
                            "label": "Full Time",
                            "value": "FT",
                            "sys_id": "69bd72706f904300bd1853a11c3ee486",
                            "type": "choice"
                        },
                        {
                            "active": True,
                            "label": "Part Time",
                            "value": "PT",
                            "sys_id": "7c8d3e706f904300bd1853a11c3ee4d9",
                            "type": "choice"
                        }
                    ],
                    "display_name": "BLC-U-SPR",
                    "entry_point": False,
                    "language_of_instruction": {
                        "active": True,
                        "label": "English",
                        "value": "en",
                        "sys_id": "53a8434a6f54c300bd1853a11c3ee434",
                        "type": "choice"
                    },
                    "location": {
                        "active": True,
                        "label": "City campus",
                        "value": "U",
                        "sys_id": "0d4d703ddb720510d202d5b4f396192b",
                        "type": "Location"
                    },
                    "mode": {
                        "active": True,
                        "label": "On campus - Block",
                        "value": "BLC",
                        "sys_id": "ebd9b8b5db720510d202d5b4f396194a",
                        "type": "DeliveryMode"
                    },
                    "offered": True,
                    "offering_uid": "8f04b2fe47d11610d42c8833036d43ea",
                    "publish": True,
                    "state": {
                        "active": True,
                        "label": "Checked",
                        "value": "checked",
                        "sys_id": "64da2ffbdbc073400595c4048a9619f0",
                        "type": "choice"
                    },
                    "student_types": [
                        {
                            "active": True,
                            "label": "International",
                            "value": "international",
                            "sys_id": "27925a40dba0fb400595c4048a961977",
                            "type": "choice"
                        },
                        {
                            "active": True,
                            "label": "Domestic",
                            "value": "domestic",
                            "sys_id": "e382da40dba0fb400595c4048a961998",
                            "type": "choice"
                        }
                    ],
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "a2ce7252874ed61039b8ab0a0cbb3581",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18",
                    "unit_of_duration": {
                        "active": True,
                        "label": "Weeks",
                        "value": "weeks",
                        "sys_id": "d261ee99dbae84507f4f8a264a961999",
                        "type": "choice"
                    }
                },
                {
                    "admission_calendar": {
                        "active": True,
                        "label": "July Session",
                        "value": "650",
                        "sys_id": "cf69d7d21b364510212465fa274bcb82",
                        "type": "choice"
                    },
                    "attendance_type": [
                        {
                            "active": True,
                            "label": "Full Time",
                            "value": "FT",
                            "sys_id": "69bd72706f904300bd1853a11c3ee486",
                            "type": "choice"
                        },
                        {
                            "active": True,
                            "label": "Part Time",
                            "value": "PT",
                            "sys_id": "7c8d3e706f904300bd1853a11c3ee4d9",
                            "type": "choice"
                        }
                    ],
                    "display_name": "BLC-U-650",
                    "entry_point": False,
                    "language_of_instruction": {
                        "active": True,
                        "label": "English",
                        "value": "en",
                        "sys_id": "53a8434a6f54c300bd1853a11c3ee434",
                        "type": "choice"
                    },
                    "location": {
                        "active": True,
                        "label": "City campus",
                        "value": "U",
                        "sys_id": "0d4d703ddb720510d202d5b4f396192b",
                        "type": "Location"
                    },
                    "mode": {
                        "active": True,
                        "label": "On campus - Block",
                        "value": "BLC",
                        "sys_id": "ebd9b8b5db720510d202d5b4f396194a",
                        "type": "DeliveryMode"
                    },
                    "offered": True,
                    "offering_uid": "cf04b2fe47d11610d42c8833036d43e7",
                    "publish": True,
                    "state": {
                        "active": True,
                        "label": "Checked",
                        "value": "checked",
                        "sys_id": "64da2ffbdbc073400595c4048a9619f0",
                        "type": "choice"
                    },
                    "student_types": [
                        {
                            "active": True,
                            "label": "International",
                            "value": "international",
                            "sys_id": "27925a40dba0fb400595c4048a961977",
                            "type": "choice"
                        },
                        {
                            "active": True,
                            "label": "Domestic",
                            "value": "domestic",
                            "sys_id": "e382da40dba0fb400595c4048a961998",
                            "type": "choice"
                        }
                    ],
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:18",
                    "sys_id": "a6ce7252874ed61039b8ab0a0cbb3581",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:18",
                    "unit_of_duration": {
                        "active": True,
                        "label": "Weeks",
                        "value": "weeks",
                        "sys_id": "d261ee99dbae84507f4f8a264a961999",
                        "type": "choice"
                    }
                }
            ],
            "credit_points": "72",
            "date_of_last_accreditation": "2029-12-31",
            "description": "<p>This course is designed for professionals aiming to excel in the property development sector, including those in valuation, construction, engineering, town planning, and architecture. Choose this course to deepen your understanding of property development and enhance your practical skills, leveraging UTS&#39;s strong industry connections and expertise.</p>\n<p>You will acquire a broad knowledge of the property development cycle and the ability to apply this in various management roles or client interactions. The course offers flexibility, allowing you to customise your learning with electives in finance, urban design, and more, preparing you for a seamless transition into the Master of Planning if desired.</p>\n<p>You&#39;ll also benefit from the diverse professional backgrounds of your peers, creating a rich environment for networking and peer-to-peer learning.</p>\n<p>The UTS Master of Property Development may also be studied as a combined degree with another associated discipline: UTS Master of Property Development and Investment UTS Master of Property Development and Planning UTS Master of Property Development and Project Management</p>",
            "duration_ft_period": {
                "active": True,
                "label": "Year(s)",
                "value": "years",
                "sys_id": "8313c8814f635b00eeb3eb4f0310c7d8",
                "type": "choice"
            },
            "duration_ft_std": "1.5",
            "duration_pt_period": {
                "active": True,
                "label": "Year(s)",
                "value": "years",
                "sys_id": "12524c014f635b00eeb3eb4f0310c793",
                "type": "choice"
            },
            "duration_pt_std": "3",
            "educational_area": {
                "active": True,
                "label": "010020 Design, Architecture and Building",
                "value": "010020",
                "sys_id": "46142b2fc3ddc2107fe22c4bb0013128",
                "type": "reference"
            },
            "effective_date": "2026-01-01",
            "ext_reporting_code": [
                {
                    "applies_to_scheme_1": False,
                    "level_1": {
                        "active": True,
                        "label": "Architecture and Urban Environment not elsewhere classified",
                        "value": "040199",
                        "sys_id": "7b8d0664dbb8a740c7c064a14a9619ee",
                        "level": "3",
                        "type": "FieldOfEducation"
                    },
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "26ce7252874ed61039b8ab0a0cbb35d4",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19",
                    "type": {
                        "active": True,
                        "label": "Primary",
                        "value": "primary",
                        "sys_id": "d8c7b4711bf28110212465fa274bcb1d",
                        "type": "reference"
                    }
                }
            ],
            "external_accreditation": [
                {
                    "description": "<p>The course is accredited by both the Australian Property Institute and the Royal Institute of Chartered Surveyors.</p>",
                    "name": "Royal Institution of Chartered Surveyors (RICS)",
                    "start_date": "2019-01-01",
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "66ce7252874ed61039b8ab0a0cbb3585",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19"
                },
                {
                    "description": "<p>The course is accredited by both the Australian Property Institute and the Royal Institute of Chartered Surveyors.</p>",
                    "end_date": "2024-12-31",
                    "name": "Australian Property Institute (API)",
                    "start_date": "2020-01-01",
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "aece7252874ed61039b8ab0a0cbb3584",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19"
                }
            ],
            "implementation_month": {
                "active": True,
                "label": "January",
                "value": "1",
                "sys_id": "52e0c9b74ff9f600949dc3818110c721",
                "type": "choice"
            },
            "implementation_year": "2026",
            "key_search_terms": [
                {
                    "active": False,
                    "label": "Property Investment Portfolios",
                    "value": ",course",
                    "sys_id": "03a62befc3ddc2107fe22c4bb0013184",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Property Assets",
                    "value": ",course",
                    "sys_id": "07a62befc3ddc2107fe22c4bb0013182",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Property Taxation",
                    "value": ",course",
                    "sys_id": "07a62befc3ddc2107fe22c4bb0013186",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Property Market",
                    "value": ",course",
                    "sys_id": "0ba62befc3ddc2107fe22c4bb0013184",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Project Management Leadership",
                    "value": ",course",
                    "sys_id": "0fa62befc3ddc2107fe22c4bb0013180",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Property Development",
                    "value": ",course",
                    "sys_id": "0fa62befc3ddc2107fe22c4bb0013182",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Greenfield Development",
                    "value": ",course",
                    "sys_id": "12a6e7efc3ddc2107fe22c4bb0013142",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Government",
                    "value": ",course",
                    "sys_id": "1aa6e7efc3ddc2107fe22c4bb0013133",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Building",
                    "value": ",course",
                    "sys_id": "1da667efc3ddc2107fe22c4bb00131b9",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Government",
                    "value": ",course",
                    "sys_id": "1ea6e7efc3ddc2107fe22c4bb0013133",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Management",
                    "value": ",course",
                    "sys_id": "22a6e7efc3ddc2107fe22c4bb00131cf",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Legal",
                    "value": ",course",
                    "sys_id": "26a6e7efc3ddc2107fe22c4bb00131c5",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Management",
                    "value": ",course",
                    "sys_id": "26a6e7efc3ddc2107fe22c4bb00131cf",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Market Analysis",
                    "value": ",course",
                    "sys_id": "26a6e7efc3ddc2107fe22c4bb00131d7",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Commercial Retail",
                    "value": ",course",
                    "sys_id": "29a667efc3ddc2107fe22c4bb00131fc",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Sustainable",
                    "value": ",course",
                    "sys_id": "2ba62befc3ddc2107fe22c4bb00131e4",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Regulation",
                    "value": ",course",
                    "sys_id": "5ba62befc3ddc2107fe22c4bb0013199",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Cost Planning",
                    "value": ",course",
                    "sys_id": "61a6a7efc3ddc2107fe22c4bb0013117",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Construction",
                    "value": ",course",
                    "sys_id": "65a6a7efc3ddc2107fe22c4bb001310b",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Transactions",
                    "value": ",course",
                    "sys_id": "67a66befc3ddc2107fe22c4bb0013103",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Built Environment",
                    "value": ",course",
                    "sys_id": "99a667efc3ddc2107fe22c4bb00131d3",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Valuation",
                    "value": ",course",
                    "sys_id": "a3a66befc3ddc2107fe22c4bb0013117",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Urban Renewal",
                    "value": ",course",
                    "sys_id": "a7a66befc3ddc2107fe22c4bb001310f",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Valuers",
                    "value": ",course",
                    "sys_id": "a7a66befc3ddc2107fe22c4bb0013118",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Urban Development",
                    "value": ",course",
                    "sys_id": "afa66befc3ddc2107fe22c4bb001310d",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Finance",
                    "value": ",course",
                    "sys_id": "c2a6e7efc3ddc2107fe22c4bb0013102",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Political",
                    "value": ",course",
                    "sys_id": "c3a62befc3ddc2107fe22c4bb0013166",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Planning",
                    "value": ",course",
                    "sys_id": "cba62befc3ddc2107fe22c4bb001315f",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Planning",
                    "value": ",course",
                    "sys_id": "cfa62befc3ddc2107fe22c4bb001315f",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Spatial Analysis",
                    "value": ",course",
                    "sys_id": "dfa62befc3ddc2107fe22c4bb00131c6",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Law",
                    "value": ",course",
                    "sys_id": "e2a6e7efc3ddc2107fe22c4bb00131be",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Investment",
                    "value": ",course",
                    "sys_id": "e6a6e7efc3ddc2107fe22c4bb00131aa",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Development Proposals",
                    "value": ",course",
                    "sys_id": "f1a6a7efc3ddc2107fe22c4bb001313d",
                    "type": "reference"
                },
                {
                    "active": False,
                    "label": "Negotiation",
                    "value": ",course",
                    "sys_id": "fea62befc3ddc2107fe22c4bb0013113",
                    "type": "reference"
                }
            ],
            "master_record_status": {
                "active": True,
                "label": "Active",
                "value": "offered",
                "sys_id": "d0bdfb1e4f953a00949dc3818110c762",
                "type": "choice"
            },
            "minor_version": 0,
            "name": "Master of Property Development",
            "nested_curriculum_structure": {
                "credit_points": "72",
                "name": "Structure",
                "sys_created_by": "141530",
                "sys_created_on": "2024-11-26 00:31:50",
                "sys_id": "fc800f1e1b4a5a10adfddc69b04bcb73",
                "sys_updated_by": "141530",
                "sys_updated_on": "2024-11-26 00:31:50",
                "curriculum_structure_container": [
                    {
                        "credit_points": "48",
                        "description": "(STM91265) Complete all of the following subjects:",
                        "order": 0,
                        "parent_connector": {
                            "active": True,
                            "label": "AND",
                            "value": "AND",
                            "sys_id": "36cb77274f148700949dc3818110c73c",
                            "type": "choice"
                        },
                        "parent_record": "fc800f1e1b4a5a10adfddc69b04bcb73",
                        "sys_created_by": "141530",
                        "sys_created_on": "2024-11-26 00:31:50",
                        "sys_id": "b8800f1e1b4a5a10adfddc69b04bcb84",
                        "sys_updated_by": "141530",
                        "sys_updated_on": "2024-11-26 00:31:50",
                        "title": "Core",
                        "vertical_grouping": {
                            "active": True,
                            "label": "Group",
                            "value": "group",
                            "sys_id": "dd383f501b235d5002b942e7b04bcbb7",
                            "type": "choice"
                        },
                        "curriculum_structure_relationship": [
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15142",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Property Development Process",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "2952ac3f87b4861042d3ca260cbb3586",
                                    "links": {
                                        "self": "/subjects/2952ac3f87b4861042d3ca260cbb3586"
                                    }
                                },
                                "order": 0,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "f4800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17700",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Planning and Environmental Law",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "de45207f87f4861042d3ca260cbb3507",
                                    "links": {
                                        "self": "/subjects/de45207f87f4861042d3ca260cbb3507"
                                    }
                                },
                                "order": 100,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "74800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12518",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Property Transactions",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "f135683f87f4861042d3ca260cbb35ba",
                                    "links": {
                                        "self": "/subjects/f135683f87f4861042d3ca260cbb35ba"
                                    }
                                },
                                "order": 200,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "38800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12535",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Property Investment and Development Feasibility",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "40d36c3787f4861042d3ca260cbb35ff",
                                    "links": {
                                        "self": "/subjects/40d36c3787f4861042d3ca260cbb35ff"
                                    }
                                },
                                "order": 300,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "b4800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17771",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Valuation Methodology",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "c872287f87b4861042d3ca260cbb3503",
                                    "links": {
                                        "self": "/subjects/c872287f87b4861042d3ca260cbb3503"
                                    }
                                },
                                "order": 400,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "78800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15143",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Group Project A: Urban Renewal",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "8fb6e4378738861042d3ca260cbb35dc",
                                    "links": {
                                        "self": "/subjects/8fb6e4378738861042d3ca260cbb35dc"
                                    }
                                },
                                "order": 500,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "f4800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17551",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Property Market and Risk Analysis",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "a70264fb87b4861042d3ca260cbb35f2",
                                    "links": {
                                        "self": "/subjects/a70264fb87b4861042d3ca260cbb35f2"
                                    }
                                },
                                "order": 600,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "f8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17704",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Property Development Finance",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "6125e03f87f4861042d3ca260cbb35c9",
                                    "links": {
                                        "self": "/subjects/6125e03f87f4861042d3ca260cbb35c9"
                                    }
                                },
                                "order": 700,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "b8800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "34800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            }
                        ]
                    },
                    {
                        "credit_points": "24",
                        "description": "(CBK90622) Select 24 credit points from the following options:",
                        "order": 100,
                        "parent_connector": {
                            "active": True,
                            "label": "AND",
                            "value": "AND",
                            "sys_id": "36cb77274f148700949dc3818110c73c",
                            "type": "choice"
                        },
                        "parent_record": "fc800f1e1b4a5a10adfddc69b04bcb73",
                        "sys_created_by": "141530",
                        "sys_created_on": "2024-11-26 00:31:50",
                        "sys_id": "f0800f1e1b4a5a10adfddc69b04bcb83",
                        "sys_updated_by": "141530",
                        "sys_updated_on": "2024-11-26 00:31:50",
                        "title": "Electives",
                        "vertical_grouping": {
                            "active": True,
                            "label": "Group",
                            "value": "group",
                            "sys_id": "dd383f501b235d5002b942e7b04bcbb7",
                            "type": "choice"
                        },
                        "curriculum_structure_relationship": [
                            {
                                "child_record": {
                                    "class_name": "Substructures",
                                    "code": "SMJ10160",
                                    "credit_points": "12",
                                    "implementation_year": "2025",
                                    "name": "Valuation",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "e64d42584f5fa600949dc3818110c7d0",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Sub-major",
                                        "value": "sub_major",
                                        "sys_id": "c448c3831be20990212465fa274bcb69",
                                        "type": "choice"
                                    },
                                    "sys_id": "7e866d3387bc861042d3ca260cbb3560",
                                    "links": {
                                        "self": "/areas_of_study/7e866d3387bc861042d3ca260cbb3560"
                                    }
                                },
                                "order": 0,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "30800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15317",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Advanced Project Risk Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "9df3e87787f4861042d3ca260cbb35f2",
                                    "links": {
                                        "self": "/subjects/9df3e87787f4861042d3ca260cbb35f2"
                                    }
                                },
                                "order": 100,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "34800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "25741",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Capital Markets",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "b6c528ff87f4861042d3ca260cbb35f9",
                                    "links": {
                                        "self": "/subjects/b6c528ff87f4861042d3ca260cbb35f9"
                                    }
                                },
                                "order": 200,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "bc800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "171200",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Conservation and Heritage",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "b545ec3f87f4861042d3ca260cbb3568",
                                    "links": {
                                        "self": "/subjects/b545ec3f87f4861042d3ca260cbb3568"
                                    }
                                },
                                "order": 300,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "3c800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12591",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Construction Cost Planning and Control",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "47b6e4378738861042d3ca260cbb35f3",
                                    "links": {
                                        "self": "/subjects/47b6e4378738861042d3ca260cbb35f3"
                                    }
                                },
                                "order": 400,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "30800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12537",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Construction Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "2195e4bf87f4861042d3ca260cbb35dc",
                                    "links": {
                                        "self": "/subjects/2195e4bf87f4861042d3ca260cbb35dc"
                                    }
                                },
                                "order": 500,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "bc800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12511",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Construction Technology and Regulation",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "8676a0f38738861042d3ca260cbb3576",
                                    "links": {
                                        "self": "/subjects/8676a0f38738861042d3ca260cbb3576"
                                    }
                                },
                                "order": 600,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "b0800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15145",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Development Negotiation and Community Engagement",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "1d95e4bf87f4861042d3ca260cbb3598",
                                    "links": {
                                        "self": "/subjects/1d95e4bf87f4861042d3ca260cbb3598"
                                    }
                                },
                                "order": 700,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "38800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "25742",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Financial Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "33b564ff87f4861042d3ca260cbb3567",
                                    "links": {
                                        "self": "/subjects/33b564ff87f4861042d3ca260cbb3567"
                                    }
                                },
                                "order": 800,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "3c800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12002",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Global Property Trends",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "93f464fb87f4861042d3ca260cbb35fe",
                                    "links": {
                                        "self": "/subjects/93f464fb87f4861042d3ca260cbb35fe"
                                    }
                                },
                                "order": 900,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "b8800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15144",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Group Project B: Greenfields Development",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "22c264ff87b4861042d3ca260cbb35c3",
                                    "links": {
                                        "self": "/subjects/22c264ff87b4861042d3ca260cbb35c3"
                                    }
                                },
                                "order": 1000,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "fc800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17556",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Investment Property Valuation",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "77a3a03787f4861042d3ca260cbb359f",
                                    "links": {
                                        "self": "/subjects/77a3a03787f4861042d3ca260cbb359f"
                                    }
                                },
                                "order": 1100,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "7c800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17775",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Land Acquisition Statutory Valuation and Litigation",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "7435e43f87f4861042d3ca260cbb3580",
                                    "links": {
                                        "self": "/subjects/7435e43f87f4861042d3ca260cbb3580"
                                    }
                                },
                                "order": 1200,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "70800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15327",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Managing Project Complexity",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "0f352c3f87f4861042d3ca260cbb351b",
                                    "links": {
                                        "self": "/subjects/0f352c3f87f4861042d3ca260cbb351b"
                                    }
                                },
                                "order": 1300,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "fc800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15362",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Managing Project Contracts",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "faa42c7b87f4861042d3ca260cbb35e6",
                                    "links": {
                                        "self": "/subjects/faa42c7b87f4861042d3ca260cbb35e6"
                                    }
                                },
                                "order": 1400,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "f0800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15325",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Negotiation and Conflict Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "be63a8b387f4861042d3ca260cbb3571",
                                    "links": {
                                        "self": "/subjects/be63a8b387f4861042d3ca260cbb3571"
                                    }
                                },
                                "order": 1500,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "78800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15346",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Organisational Project Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "c992e0bf87b4861042d3ca260cbb357e",
                                    "links": {
                                        "self": "/subjects/c992e0bf87b4861042d3ca260cbb357e"
                                    }
                                },
                                "order": 1600,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "7c800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15301",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Planning Theory and Decision Making",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "e235e83f87f4861042d3ca260cbb35c2",
                                    "links": {
                                        "self": "/subjects/e235e83f87f4861042d3ca260cbb35c2"
                                    }
                                },
                                "order": 1700,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "f8800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15348",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Project Finance and Analysis",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "c585a0bf87f4861042d3ca260cbb35ec",
                                    "links": {
                                        "self": "/subjects/c585a0bf87f4861042d3ca260cbb35ec"
                                    }
                                },
                                "order": 1800,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "b8800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15328",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Project Innovation and Entrepreneurship",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "8ab220ff87b4861042d3ca260cbb35bd",
                                    "links": {
                                        "self": "/subjects/8ab220ff87b4861042d3ca260cbb35bd"
                                    }
                                },
                                "order": 1900,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "70800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15360",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Digital Transformation in Project Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "f265a87f87f4861042d3ca260cbb354f",
                                    "links": {
                                        "self": "/subjects/f265a87f87f4861042d3ca260cbb354f"
                                    }
                                },
                                "order": 2000,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "74800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15315",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Project Management Principles",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "d604a0b787f4861042d3ca260cbb354f",
                                    "links": {
                                        "self": "/subjects/d604a0b787f4861042d3ca260cbb354f"
                                    }
                                },
                                "order": 2100,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "f0800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15314",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Project Management in Peripheral Communities",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "faa2e8bf87b4861042d3ca260cbb354e",
                                    "links": {
                                        "self": "/subjects/faa2e8bf87b4861042d3ca260cbb354e"
                                    }
                                },
                                "order": 2200,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "f4800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17703",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Property Taxation",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "44826c7f87b4861042d3ca260cbb35db",
                                    "links": {
                                        "self": "/subjects/44826c7f87b4861042d3ca260cbb35db"
                                    }
                                },
                                "order": 2300,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "74800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "17772",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Real Estate Economics",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "f1a2a8bf87b4861042d3ca260cbb3555",
                                    "links": {
                                        "self": "/subjects/f1a2a8bf87b4861042d3ca260cbb3555"
                                    }
                                },
                                "order": 2400,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "78800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15251",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Spatial Analysis in Planning and Property",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "b092e0bf87b4861042d3ca260cbb3520",
                                    "links": {
                                        "self": "/subjects/b092e0bf87b4861042d3ca260cbb3520"
                                    }
                                },
                                "order": 2500,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "b4800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "12515",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Strategic Asset Management",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "ac456c3f87f4861042d3ca260cbb35e3",
                                    "links": {
                                        "self": "/subjects/ac456c3f87f4861042d3ca260cbb35e3"
                                    }
                                },
                                "order": 2600,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "f8800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15146",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Sustainable Urban Development",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "84c4e0bb87f4861042d3ca260cbb35a6",
                                    "links": {
                                        "self": "/subjects/84c4e0bb87f4861042d3ca260cbb35a6"
                                    }
                                },
                                "order": 2700,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "b0800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15336",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Systems Thinking for Managers",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "f182ec7f87b4861042d3ca260cbb35b9",
                                    "links": {
                                        "self": "/subjects/f182ec7f87b4861042d3ca260cbb35b9"
                                    }
                                },
                                "order": 2800,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "b4800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15222",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Urban Design",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "ba25643f87f4861042d3ca260cbb3568",
                                    "links": {
                                        "self": "/subjects/ba25643f87f4861042d3ca260cbb3568"
                                    }
                                },
                                "order": 2900,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:50",
                                "sys_id": "34800f1e1b4a5a10adfddc69b04bcb84",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:50"
                            },
                            {
                                "child_record": {
                                    "class_name": "Subject",
                                    "code": "15241",
                                    "credit_points": "6",
                                    "implementation_year": "2025",
                                    "name": "Urban Economics and Infrastructure Planning",
                                    "nickname": "2025.01",
                                    "status": {
                                        "active": True,
                                        "label": "Approved",
                                        "value": "Active",
                                        "sys_id": "a593cbea6fa0cb00bd1853a11c3ee4ee",
                                        "type": "choice"
                                    },
                                    "subclass": {
                                        "active": True,
                                        "label": "Subject",
                                        "value": "subject",
                                        "sys_id": "cb3c45b80fbccf009cd2534f62050ea0",
                                        "type": "choice"
                                    },
                                    "sys_id": "93c36c3787f4861042d3ca260cbb3531",
                                    "links": {
                                        "self": "/subjects/93c36c3787f4861042d3ca260cbb3531"
                                    }
                                },
                                "order": 3000,
                                "parent_connector": {
                                    "active": True,
                                    "label": "AND",
                                    "value": "AND",
                                    "sys_id": "36cb77274f148700949dc3818110c73c",
                                    "type": "choice"
                                },
                                "parent_record": "f0800f1e1b4a5a10adfddc69b04bcb83",
                                "sys_created_by": "141530",
                                "sys_created_on": "2024-11-26 00:31:51",
                                "sys_id": "38800f1e1b4a5a10adfddc69b04bcb85",
                                "sys_updated_by": "141530",
                                "sys_updated_on": "2024-11-26 00:31:51"
                            }
                        ]
                    }
                ]
            },
            "nickname": "2026.01",
            "notes": "<p>Students who do not meet the admission requirements below may begin with a Graduate Certificate and progress to the Master of Property Development.</p>\n<p><strong><a href=\"https://www.uts.edu.au/study/find-a-course/graduate-certificate-property-development\">Graduate Certificate in Property Development</a> --&gt; Master of Property Development</strong></p>\n<p>(Note that entry to the Masters via other UTS Graduate Certificates and Graduate Diplomas is also possible.)</p>",
            "other": False,
            "parent_academic_org": {
                "active": True,
                "label": "Design, Architecture and Building",
                "value": "A",
                "sys_id": "70704f3f1b9c21d075df2069b04bcbd7",
                "type": "OrgUnit"
            },
            "parent_id": "1b00326a1baee190bca998ec2d4bcbd7",
            "professional_recognition": "<p>The course is accredited by both the Australian Property Institute and the Royal Institute of Chartered Surveyors.</p>",
            "publish_to_handbook": False,
            "publish_tuition_fees": False,
            "published_in_handbook": {
                "active": True,
                "label": "Yes",
                "value": "1",
                "sys_id": "97e749ad6fd08300bd1853a11c3ee494",
                "type": "choice"
            },
            "publishing_parent_academic_orgs": [
                {
                    "active": True,
                    "label": "Design, Architecture and Building",
                    "value": "A",
                    "sys_id": "70704f3f1b9c21d075df2069b04bcbd7",
                    "type": "OrgUnit"
                }
            ],
            "requirement": [
                {
                    "applicable_requirement": False,
                    "applies_to_all_offerings": True,
                    "requirement_multi_1": [
                        {
                            "active": True,
                            "label": "IELTS Academic: overall 6.5, writing 6.0\nTOEFL iBT: overall 79, writing 21\nUTS College AE5: Pass\nPearson PTE: overall 58, writing 50\nCambridge C1A/C2P: overall 176, writing 169",
                            "value": "ELRS1",
                            "sys_id": "332df044971b7510860ebf37f053af20",
                            "type": "reference"
                        }
                    ],
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "2ece7252874ed61039b8ab0a0cbb35d1",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19",
                    "type": {
                        "active": True,
                        "label": "English Language Requirement",
                        "value": "english_language_requirement",
                        "sys_id": "9a9923dc9710c250860ebf37f053affe",
                        "type": "choice"
                    }
                },
                {
                    "applicable_requirement": False,
                    "applies_to_all_offerings": True,
                    "description": "<p>To be eligible for admission to this course, applicants must meet the following criteria.</p><p>Applicants must have one of the following: </p> <ul> <li>Completed Australian bachelor&#39;s degree or higher qualification, or overseas equivalent, in Architecture and Building, Engineering, Management and Commerce, Law and legal studies, or Economics and Econometrics </li> </ul> <p>OR </p> <ul> <li>Completed Australian bachelor&#39;s degree or higher qualification, or overseas equivalent, in any field of study AND A minimum of 1 year full-time, or equivalent part-time, relevant professional experience </li> </ul> <p>Applicants who do not meet the criteria above should consider applying for <a href=\"https://handbook.uts.edu.au/course/Current/c11271\">C11271 Graduate Certificate in Property Development</a>. </p> <p><strong>Supporting documentation to be submitted with the application</strong></p> <p>For applicants who need to demonstrate work experience: </p> <ul> <li><strong>Curriculum Vitae</strong> AND <strong>Statement of service </strong>in one of the following formats: <ul> <li>A &#39;Statement of Service&#39; provided by the employer </li> <li>A completed &#39;<a href=\"https://www.uts.edu.au/statement-service-form\">UTS statement of service</a>&rsquo; signed by the employer </li> <li>A <a href=\"https://www.service.nsw.gov.au/transaction/nsw-statutory-declaration-forms\">statutory </a><a href=\"https://my.gov.au/en/about/help/digital-identity/digital-commonwealth-statutory-declaration\">declaration </a>confirming work experience (for Australian Residents only) </li> <li>An official letter from the applicant&rsquo;s accountant or solicitor on their company letterhead confirming the applicant&rsquo;s work experience or engagement with the business, duration of operations, and the nature of the business </li> <li>A business certificate of registration in original language and English (e.g. provision of ASIC documentation or ABN or similar documentation for Australian Businesses) </li> </ul> </li> </ul><p>Eligibility for admission does not guarantee offer of a place.</p>",
                    "domain": {
                        "active": True,
                        "label": "Admission criteria",
                        "value": "admission_criteria",
                        "sys_id": "74ccb06cc33c5610ec54d03a050131ac",
                        "type": "choice"
                    },
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "66ce7252874ed61039b8ab0a0cbb35d2",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19",
                    "type": {
                        "active": True,
                        "label": "Admission criteria",
                        "value": "admission",
                        "sys_id": "5961e0ed1bbe0110212465fa274bcbdf",
                        "type": "choice"
                    }
                },
                {
                    "applicable_requirement": False,
                    "applies_to_all_offerings": True,
                    "description": "<p>Inherent requirements are academic and non-academic requirements that are essential for successfully completing a course at UTS. You can find the inherent requirements for your course via the <a href=\"https://www.uts.edu.au/current-students/managing-your-course/your-enrolment/inherent-requirements\">inherent requirements directory</a>.</p>",
                    "sys_created_by": "141530",
                    "sys_created_on": "2024-11-26 00:24:19",
                    "sys_id": "e2ce7252874ed61039b8ab0a0cbb35d2",
                    "sys_updated_by": "141530",
                    "sys_updated_on": "2024-11-26 00:24:19",
                    "type": {
                        "active": True,
                        "label": "Inherent requirements",
                        "value": "inherent_requirements",
                        "sys_id": "0b73b3fbdbb2cd10d202d5b4f3961947",
                        "type": "choice"
                    }
                }
            ],
            "short_title": "Master of Property Development",
            "sms_version": "7",
            "start_date": "2025-01-01",
            "status": {
                "active": True,
                "label": "Approved",
                "value": "Active",
                "sys_id": "4ee411252b9f5600155427b436da151e",
                "type": "choice"
            },
            "structure": "<p>Students must complete 72 credit points made up of 48 credit points of core subjects and 24 credit points of property options.</p>",
            "study_level_ref": {
                "active": True,
                "label": "Postgraduate",
                "value": "PG",
                "sys_id": "e730b4dcdb6afc5087f743ea139619f1",
                "type": "reference"
            },
            "subclass": {
                "active": True,
                "label": "Course",
                "value": "course",
                "sys_id": "927cc1b80fbccf009cd2534f62050e85",
                "type": "choice"
            },
            "sys_created_by": "141530",
            "sys_created_on": "2024-11-26 00:24:18",
            "sys_updated_by": "141530",
            "sys_updated_on": "2024-11-26 00:31:50",
            "type": {
                "active": True,
                "label": "Master's Coursework",
                "value": "MC",
                "sys_id": "306079551b0bd51002b942e7b04bcbb4",
                "type": "choice"
            },
            "type_ref": {
                "active": True,
                "label": "Master's",
                "value": "MAST",
                "sys_id": "2b531f6d1b4b191002b942e7b04bcbf0",
                "type": "reference"
            },
            "version": 1,
            "version_approved": "2024-11-26 00:31:50"
        }

    extract_location ('ref_id', course)
