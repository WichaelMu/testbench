from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .cache import effective_profile
from .model import Target, payload_bytes


class AwsError (RuntimeError):
    pass

class AWS:
    def __init__(self, profile = None, region = None):
        self.profile    = profile
        self.region     = region
        self.executable = shutil.which ('aws')

        if (not self.executable):
            raise AwsError ('AWS CLI v2 is required; install it and configure your SSO profile.')

    def call (self, *args, read_timeout = 30):
        command = [ self.executable, '--output', 'json', '--color', 'off', '--no-cli-pager', '--no-cli-auto-prompt', '--cli-connect-timeout', '10', '--cli-read-timeout', str (read_timeout) ]

        if (self.profile):
            command += [ '--profile', self.profile ]

        if (self.region):
            command += [ '--region', self.region ]

        command.extend (args)
        env = dict (os.environ, AWS_PAGER='', AWS_CLI_AUTO_PROMPT='off',
                   AWS_MAX_ATTEMPTS='1', AWS_RETRY_MODE='standard')
        try:
            result = subprocess.run (command, capture_output = True, text = True, env = env, timeout = read_timeout + 30)

        except subprocess.TimeoutExpired as exc:
            raise AwsError ('AWS request timed out. Invocation outcome may be unknown; no automatic retry was made.') from exc

        if (result.returncode):
            raise AwsError (result.stderr.strip () or result.stdout.strip () or 'AWS request failed.')

        try:
            return json.loads (result.stdout)

        except json.JSONDecodeError as exc:
            raise AwsError ('AWS CLI returned an unexpected non-JSON response.') from exc

    def identity (self):
        try:
            return self.call ('sts', 'get-caller-identity')

        except AwsError as exc:
            message      = str (exc).casefold ()
            auth_markers = ('sso session', 'token has expired', 'expiredtoken', 'invalidclienttokenid', 'unable to locate credentials', 'error loading sso token', 'token does not exist', 'unauthorizedssotoken', 'expired and refresh failed', 'security token included in the request is invalid')

            if (any (marker in message for marker in auth_markers)):
                profile = effective_profile (self.profile)
                login   = 'aws sso login --profile ' + shlex.quote (profile)

                raise AwsError (f'AWS login is missing or expired. Run:\n  {login}\n{exc}') from exc

            raise AwsError (f'Could not verify AWS login: {exc}') from exc

    def account_alias (self):
        try:
            aliases = self.call ('iam', 'list-account-aliases', read_timeout=5)['AccountAliases']
            return aliases[0] if aliases else None

        except (AwsError, KeyError):
            return None  # Optional: SSO roles often cannot read IAM account aliases.

    def functions (self):
        data = self.call ('lambda', 'list-functions', '--query', 'Functions[].{FunctionName:FunctionName,FunctionArn:FunctionArn}')

        if not isinstance (data, list) or any (not isinstance (item, dict) or not isinstance (item.get ('FunctionName'), str) or not isinstance (item.get ('FunctionArn'), str) for item in data):
            raise AwsError ('AWS CLI returned an incomplete or invalid Lambda list.')

        return [ Target (item['FunctionName'], item['FunctionArn']) for item in data ]

    def invoke (self, target, text) :
        data = payload_bytes (text)

        with tempfile.TemporaryDirectory (prefix = 'genius-invokation-') as directory:
            payload = Path (directory) / 'payload.json'
            response = Path (directory) / 'response.json'

            payload.touch (mode = 0o600)
            payload.write_bytes (data)
            args = [ 'lambda', 'invoke', '--function-name', target.arn, '--invocation-type', 'RequestResponse', '--payload', 'fileb://' + str (payload) ]

            if (target.qualifier):
                args += ['--qualifier', target.qualifier]

            args.append (str (response))
            metadata = self.call (*args, read_timeout=930)

            if (not response.exists ()):
                raise AwsError ('AWS returned no response file. Invocation outcome may be unknown.')

            return metadata, response.read_bytes ().decode ('utf-8', errors='replace')
