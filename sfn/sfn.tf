resource "aws_sfn_state_machine" "sfn_test" {
  name     = "dev-sfn-test"
  role_arn = "arn:aws:iam::159851557642:role/dev_cass_appevents_step_function_trust_role"

  definition = <<EOF
{
  "Comment": "A Step Function used for Testing.",
  "StartAt": "Task1",
  "States":
  {

    "Task1":
    {
      "Type": "Pass",
      "Next": "Task2",
      "Result":
      {
        "Task1Output": 10
      },
      "ResultPath": "$.T1"
    },

    "Task2":
    {
      "Type": "Pass",
      "Next": "Task3",
      "Result":
      {
        "Task2Output": 20
      },
      "ResultPath": "$.T2"
    },

    "Task3":
    {
      "Type": "Pass",

      "InputPath": "$",

      "Parameters":
      {
        "Task3Input":
        {
          "Task2Output.$": "$.T2",
          "Task1Output":
          {
            "Nest1":
            {
              "Nest2":
              {
                "Task1Output.$": "$.T1"
              },
              "OtherTestInformationBecauseWhyNot.$": "$.Comment"
            }
          }
        }
      },
      
      "End": true
    }

  }
}
EOF
}
