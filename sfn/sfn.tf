resource "aws_sfn_state_machine" "sfn_test" {
  name     = "dev-sfn-test"
  role_arn = "arn:aws:iam::159851557642:role/dev_cass_appevents_step_function_trust_role"

  definition = <<EOF
{
  "Comment": "A Step Function used for Testing.",
  "StartAt": "Task1",
  "States":
  {
"Exit-State-Machine": {
"Type": "Pass",
	"End": true,
"ResultPath": "$.ERR"
},
    "Task1":
    {
	"Catch": [
        {
          "ErrorEquals": [
            "States.Http.StatusCode.400"
          ],
          "Next": "Exit-State-Machine"
        }
      ],
      "Parameters": {
        "ApiEndpoint": "https://data.curriculum.dev.mesh.uts.edu.au/libraries/leganto/courses",
        "Authentication": {
          "ConnectionArn.$": "$.Statics.ConnectionArn"
        },
        "Headers": {
          "Accept": "application/json"
        },
        "Method": "POST",
        "RequestBody": {
          "academic_department": {
            "value.$": "$.faculty"
          },
          "code.$": "$.course_sis_id",
          "end_date.$": "$.end_date",
          "instructor.$": "$.Reformat",
          "name.$": "$.name",
          "processing_department": {
            "value": "COURSE_UNIT"
          },
          "start_date.$": "$.start_date",
          "status": "ACTIVE",
          "year.$": "$.year"
        }
      },
      "Resource": "arn:aws:states:::http:invoke",
      "ResultPath": "$.GenerateCourse",
      "ResultSelector": {
        "CreatedCourseId.$": "$.ResponseBody.id",
        "SubjectId.$": "States.ArrayGetItem(States.StringSplit($.ResponseBody.name, '_ '), 0)"
      },
      "Type": "Task",
      "End": true
    }
  }
}
EOF
}
